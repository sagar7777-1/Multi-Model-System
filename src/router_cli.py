
import os
import json
import time
import re
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
API_URL = "https://api.nugen.in/api/v3/inference/completions"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "inference.jsonl"

EXPERTS = {

    "finance": {
        "model_id": "model_01m50emq7xy1cn4y",
        "name": "Finance Expert",
        "keywords": [
            # Existing banking and fraud topics
            "fraud", "transaction", "bank", "banking", "aml",
            "money laundering", "risk detection", "credit risk",
            "suspicious transfer", "beneficiary", "loan",
            "investment", "mutual fund", "insurance",
            "financial", "payment", "customer risk",

            # Interest and borrowing
            "simple interest", "compound interest",
            "interest rate", "interest", "principal",
            "emi", "equated monthly installment",
            "loan repayment", "repayment", "mortgage",
            "savings account", "fixed deposit",
            "recurring deposit", "deposit", "credit card",
            "debit card", "borrowing", "lending", "debt",
            "credit score",

            # Investments and personal finance
            "finance", "money", "budget", "budgeting",
            "personal finance", "financial planning",
            "cash flow", "portfolio", "stocks", "stock",
            "shares", "share market", "equity", "bond",
            "bonds", "dividend", "returns",
            "return on investment", "mutual funds",
            "asset allocation", "risk management",
            "wealth", "wealth management", "retirement planning",
            "emergency fund",

            # Economics and financial reporting
            "inflation", "purchasing power",
            "interest calculation", "time value of money",
            "profit", "loss", "revenue", "expenses",
            "financial statement", "financial statements",
            "working capital", "cash flow statement",
            "balance sheet",

            # Financial risk and payments
            "financial risk", "suspicious transaction",
            "payment gateway", "digital payment",
            "payment fraud", "transaction monitoring",
            "anomaly detection",
        ],
    },


    "legal": {
        "model_id": "model_01m50enpxws0mn6a",
        "name": "Legal Expert",
        "keywords": [
            "legal", "law", "lawsuit", "contract", "court",
            "compliance", "privacy", "privacy law",
            "data protection", "data-protection",
            "personal data", "customer data", "personal information",
            "data privacy", "chatbot", "ai support",
            "consent", "liability", "regulation", "statute",
            "litigation", "agreement", "rights", "legal notice",
        ],
    },

    "tax": {
        "model_id": "model_01m50enq2069gfqm",
        "name": "Tax Expert",
        "keywords": [
            "income tax", "income-tax", "income-tax regime",
            "income tax regime", "income-tax regimes",
            "tax regime", "tax regimes",
            "old and new tax regime",
            "old and new income-tax regimes",
            "salaried employee", "tax return", "taxation", "taxable",
            "deduction", "deductions", "exemption", "exemptions",
            "financial year", "assessment year", "old tax regime",
            "new tax regime", "itr", "gst", "capital gains tax",
            "tax liability", "tax slab",
        ],
    },
}

# General-purpose model used for synthesis.
MOTHER_MODEL = "meta-llama/Llama-3.2-3B-Instruct"


# --------------------------------------------------
# Prompt guardrails
# --------------------------------------------------

EXPERT_INSTRUCTIONS = {
    "finance": """
You are a banking finance, fraud detection, and financial risk expert.

Rules:
- Distinguish suspicious activity from confirmed fraud.
- Explain which evidence supports each conclusion.
- Do not assume money laundering, tax evasion, or criminal intent
  without supporting evidence.
- Focus on transaction features, historical behavior, anomaly
  detection, precision, recall, false positives, and human review.
- Do not recommend irrelevant techniques such as sentiment analysis
  when no relevant text data exists.
- State assumptions and uncertainties clearly.
- An alert alone does not prove fraud.
""",

    "legal": """
You are an Indian legal information assistant.

Rules:
- Focus on Indian law when the question concerns India.
- Never invent legislation, statutory titles, sections, judgments,
  or legal citations.
- Do not claim that India has a "Data Protection Act, 2011" or
  a "Data Privacy Act, 2011".
- Relevant central legislation includes the Digital Personal Data
  Protection Act, 2023 (DPDP Act).
- Do not assume every provision of the DPDP Act is in force.
  The commencement of relevant provisions and applicable rules
  must be verified before describing current legal obligations.
- If a legal claim cannot be verified, explicitly flag it.
- Distinguish general legal information from legal advice.
- Identify missing facts and jurisdictional uncertainty.
- Do not present foreign laws as Indian law.
- Recommend a qualified Indian lawyer for consequential decisions.
""",

    "tax": """
You are an Indian tax information assistant.

Rules:
- Focus on Indian tax rules when the question concerns India.
- Never invent rates, thresholds, exemptions, or deduction limits.
- Identify the relevant financial year (FY) or assessment year (AY).
- If the year is missing and the answer depends on year-specific
  rules, ask for the year before providing numerical figures.
- For a general comparison, explain what factors to compare without
  inventing figures.
- Never describe the new regime as having replaced the old regime.
  Explain that applicable rules depend on the year and circumstances.
- Do not introduce foreign tax rules unless requested.
- Never ask for PAN, Aadhaar, passwords, or unnecessary identifiers.
- Request only the financial details needed to answer.
- Recommend verification against current official tax guidance.
""",
}


# --------------------------------------------------
# Tax-year safety check
# --------------------------------------------------

def tax_year_is_specified(question):
    """Check whether the question contains an explicit FY or AY."""
    patterns = [
        r"\bFY\s*20\d{2}\s*[-/]\s*\d{2,4}\b",
        r"\bAY\s*20\d{2}\s*[-/]\s*\d{2,4}\b",
        r"\bfinancial year\s+20\d{2}\s*[-/]\s*\d{2,4}\b",
        r"\bassessment year\s+20\d{2}\s*[-/]\s*\d{2,4}\b",
        r"\b(?:FY|AY)\s*20\d{2}\b",
    ]

    return any(
        re.search(pattern, question, re.IGNORECASE)
        for pattern in patterns
    )


# --------------------------------------------------
# Answer safety inspection
# --------------------------------------------------


def inspect_answer(domain, answer):
    """
    Flag known risky legal claims and potentially unsafe tax answers.

    This is a warning system, not a complete fact-check.
    """
    warnings = []

    if domain == "legal":
        risky_patterns = [
            r"\bData\s+Privacy\s+Act,?\s+2011\b",
            r"\bData\s+Protection\s+Act,?\s+2011\b",
            r"\bDPA\s*2011\b",
        ]

        if any(
            re.search(pattern, answer, re.IGNORECASE)
            for pattern in risky_patterns
        ):
            warnings.append(
                "Potentially fabricated Indian legislation detected."
            )

    if domain == "tax":
        risky_patterns = [
            # Indian rupee amounts.
            r"(?:₹|Rs\.?\s*|INR\s*)\s*\d[\d,]*(?:\.\d+)?",

            # Percentages.
            r"\b\d+(?:\.\d+)?\s*%",
            r"\b\d+(?:\.\d+)?\s*(?:percent|per\s+cent)\b",

            # Potentially misleading regime statements.
            r"\breplaced the existing regime\b",
            r"\breplaced the old regime\b",
            r"\breplaced the old tax regime\b",
        ]

        if any(
            re.search(pattern, answer, re.IGNORECASE)
            for pattern in risky_patterns
        ):
            warnings.append(
                "Tax answer contains numerical claims or a known "
                "risky statement. Verify against official tax "
                "guidance for the specified FY/AY before relying on it."
            )

        # Flag requests for personal details that are not generally
        # necessary for a basic individual income-tax estimate.
        personal_data_patterns = [
            r"\b(?:provide|specify|please share|tell me|enter|supply)"
            r"\b.{0,80}\bdependents?\b",

            r"\b(?:provide|specify|please share|tell me|enter|supply)"
            r"\b.{0,80}\bmarital status\b",
        ]

        if any(
            re.search(pattern, answer, re.IGNORECASE | re.DOTALL)
            for pattern in personal_data_patterns
        ):
            warnings.append(
                "Tax answer may request unnecessary personal information. "
                "Review the requested details before proceeding."
            )

        # Never request sensitive identity or account credentials.
        sensitive_data_patterns = [
            r"\bPAN\b",
            r"\bAadhaar\b",
            r"\bpassword\b",
            r"\bOTP\b",
        ]

        if any(
            re.search(pattern, answer, re.IGNORECASE)
            for pattern in sensitive_data_patterns
        ):
            warnings.append(
                "Tax answer mentions sensitive identity or authentication "
                "information. Ensure the user is not asked to disclose it."
            )

    return warnings


# --------------------------------------------------
# API helpers
# --------------------------------------------------

def extract_answer(response_data):
    """Extract text from common completion/chat response formats."""
    choices = response_data.get("choices", [])

    if not choices:
        return ""

    choice = choices[0]
    answer = choice.get("text", "")

    if not answer and isinstance(choice.get("message"), dict):
        answer = choice["message"].get("content", "")

    return answer.strip() if isinstance(answer, str) else ""


def call_model(model_id, prompt, max_tokens=450):
    """Call the Nugen inference API and return answer plus metadata."""
    payload = {
        "model": model_id,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "stream": False,
    }

    started = time.perf_counter()

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=120,
        )

        latency = round(time.perf_counter() - started, 2)

        try:
            data = response.json()
        except ValueError:
            data = {"raw_response": response.text[:2000]}

        if not response.ok:
            return {
                "ok": False,
                "answer": "",
                "status_code": response.status_code,
                "latency_seconds": latency,
                "error": data,
            }

        answer = extract_answer(data)

        if not answer:
            return {
                "ok": False,
                "answer": "",
                "status_code": response.status_code,
                "latency_seconds": latency,
                "error": "HTTP succeeded, but no answer text was returned.",
            }

        return {
            "ok": True,
            "answer": answer,
            "status_code": response.status_code,
            "latency_seconds": latency,
            "error": None,
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "answer": "",
            "status_code": None,
            "latency_seconds": round(time.perf_counter() - started, 2),
            "error": str(exc),
        }


# --------------------------------------------------
# Domain routing
# --------------------------------------------------


def detect_domain(question):
    """
    Select the strongest domain using weighted keyword matching.

    Returns:
        (domain, scores, routing_issue)

    Preserves the existing return format used by main().
    """
    text = question.lower()
    scores = {}

    for domain, config in EXPERTS.items():
        score = 0

        for keyword in config["keywords"]:
            # Match complete words/phrases instead of arbitrary
            # substrings inside unrelated words.
            pattern = (
                r"(?<!\w)"
                + re.escape(keyword.lower())
                + r"(?!\w)"
            )

            if re.search(pattern, text):
                # Longer phrases carry more weight because they
                # are usually more specific to a domain.
                score += 2 if " " in keyword else 1

        scores[domain] = score

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    best_domain, best_score = ranked[0]
    second_score = ranked[1][1]

    if best_score == 0:
        return (
            None,
            scores,
            "No domain-specific keywords found.",
        )

    if best_score == second_score:
        return (
            None,
            scores,
            "The question matches multiple domains.",
        )

    return best_domain, scores, None



# --------------------------------------------------
# Expert response
# --------------------------------------------------

def ask_expert(domain, question):
    """Get an answer from the selected aligned expert."""
    instructions = EXPERT_INSTRUCTIONS[domain]

    extra_rules = ""

    if domain == "tax":
        extra_rules = """
Additional tax safety rules:
- Identify whether the user supplied an FY or AY.
- If the year is missing and numerical rules are needed, ask for it.
- Do not provide rates, income thresholds, deduction limits, rebates,
  or other numerical tax claims without year-specific verification.
- For general questions, explain the comparison method without
  inventing figures.
"""

    prompt = f"""
{instructions}

{extra_rules}

Answer directly and clearly. Use headings or numbered steps when
helpful. Do not invent facts to fill gaps. If current information
cannot be verified, say so explicitly.

USER QUESTION:
{question}

EXPERT ANSWER:
"""

    return call_model(
        EXPERTS[domain]["model_id"],
        prompt,
        max_tokens=450,
    )


# --------------------------------------------------
# Mother-model synthesis
# --------------------------------------------------

def synthesize_answer(question, expert_answer):
    """Improve clarity without intentionally adding factual claims."""
    prompt = f"""
You are the synthesis component of a multi-agent AI system.

Edit the expert's answer for clarity and relevance, not to create
new factual claims.

Strict rules:
- Preserve the expert's assumptions, caveats, and key points.
- Do not add laws, legal citations, tax figures, statistics, or
  technical claims absent from the expert answer.
- Do not turn uncertain claims into certain claims.
- Do not remove verification warnings.
- If the answer appears unsupported or incomplete, say verification
  is needed instead of inventing missing details.
- Do not request unnecessary sensitive identifiers.
- Keep the response concise and relevant.

USER QUESTION:
{question}

EXPERT ANSWER:
{expert_answer}

Provide the carefully edited answer:
"""

    return call_model(
        MOTHER_MODEL,
        prompt,
        max_tokens=450,
    )


# --------------------------------------------------
# Logging
# --------------------------------------------------

def write_log(record):
    """Append one JSON record to the inference log."""
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


# --------------------------------------------------
# Main CLI
# --------------------------------------------------

def main():
    if not API_KEY:
        print("ERROR: NUGEN_API_KEY was not found in .env.")
        print("Check that .env exists in the project root.")
        return

    print("=" * 60)
    print("NUGEN MULTI-DOMAIN EXPERT ROUTER")
    print("=" * 60)
    print("Domains: Finance | Legal | Tax")
    print("Type 'exit' or 'quit' to stop.")
    print("Note: Responses may require independent verification.")

    while True:
        try:
            question = input("\nYour question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting router.")
            break

        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if not question:
            print("Please enter a question.")
            continue

        domain, scores, routing_issue = detect_domain(question)

        if routing_issue:
            print(f"\nRouter needs clarification: {routing_issue}")
            print("Domain scores:", scores)
            print(
                "Please include context such as banking fraud, "
                "Indian law, or Indian income tax."
            )
            continue

        # SAFETY CHECK 1:
        # Require an explicit FY or AY before calling the tax model.
        if domain == "tax" and not tax_year_is_specified(question):
            print(
                "\nPlease specify the relevant Indian financial year "
                "or assessment year before requesting year-specific "
                "tax figures."
            )
            print("Example: FY 2025-26 or AY 2026-27.")
            print("No model call was made.")
            continue

        expert_config = EXPERTS[domain]

        print(f"\nSelected expert: {expert_config['name']}")
        print("Routing scores:", scores)
        print("Calling aligned expert model...")

        expert_result = ask_expert(domain, question)

        if not expert_result["ok"]:
            print("\nExpert inference failed.")
            print("HTTP status:", expert_result["status_code"])
            print("Error:", expert_result["error"])

            write_log({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question": question,
                "domain": domain,
                "routing_scores": scores,
                "expert_model_id": expert_config["model_id"],
                "expert_result": expert_result,
                "synthesis_result": None,
                "final_answer": None,
            })
            continue

        print(
            "Expert response received in "
            f"{expert_result['latency_seconds']} seconds."
        )

        # SAFETY CHECK 2:
        # Inspect the aligned expert's answer before synthesis.
        expert_warnings = print_answer_warnings(
            domain,
            expert_result["answer"],
            "Expert answer",
        )

        # Conservative fallback for unverified tax claims.
        safe_tax_fallback = (
            "I cannot provide a reliable tax-regime recommendation "
            "from the model's current response because it contains "
            "numerical claims that have not been verified.\n\n"
            "For a proper comparison, calculate your tax liability "
            "under both regimes using the official Income Tax "
            "Department calculator for the specified financial year. "
            "Use the same income, eligible deductions, exemptions, "
            "and other relevant details for both calculations. "
            "Then compare the resulting tax liabilities and check "
            "which regime's rules apply to your circumstances.\n\n"
            "No tax figures or personalized recommendation are "
            "being provided by this router until the relevant "
            "claims can be verified."
        )

        synthesis_result = None
        synthesis_used = False
        final_answer = None
        final_warnings = []

        # If the expert's tax answer contains unverified numbers,
        # do not pass those claims to the mother model for rewriting.
        if should_use_tax_fallback(domain, expert_warnings):
            print(
                "\nSafety policy: Skipping synthesis because the "
                "expert answer contains unverified tax claims."
            )
            final_answer = safe_tax_fallback
            final_warnings = list(expert_warnings)

        else:
            print("Calling mother model for cautious synthesis...")

            synthesis_result = synthesize_answer(
                question,
                expert_result["answer"],
            )

            if synthesis_result["ok"]:
                candidate_answer = synthesis_result["answer"]
                synthesis_used = True
            else:
                candidate_answer = expert_result["answer"]
                print(
                    "Synthesis unavailable; checking the expert answer."
                )

            # SAFETY CHECK 3:
            # Inspect the answer that would otherwise be displayed.
            candidate_warnings = print_answer_warnings(
                domain,
                candidate_answer,
                "Final answer",
            )

            if domain == "tax" and candidate_warnings:
                print(
                    "\nSafety policy: Replacing the unverified tax "
                    "answer with a cautious fallback."
                )
                final_answer = safe_tax_fallback
                final_warnings = list(candidate_warnings)
                synthesis_used = False
            else:
                final_answer = candidate_answer
                final_warnings = candidate_warnings

        print("\n" + "=" * 60)
        print("FINAL ANSWER")
        print("=" * 60)
        print(final_answer)

        print("\n" + "-" * 60)
        print("Execution details")
        print("Expert:", expert_config["name"])
        print(
            "Expert latency:",
            expert_result["latency_seconds"],
            "seconds",
        )

        synthesis_latency = (
            synthesis_result["latency_seconds"]
            if synthesis_result is not None
            else 0.0
        )

        print("Synthesis latency:", synthesis_latency, "seconds")
        print("Synthesis used:", synthesis_used)
        print("Expert safety warnings:", len(expert_warnings))
        print("Unverified-answer warnings:", len(final_warnings))
        print("-" * 60)

        write_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "domain": domain,
            "routing_scores": scores,
            "expert_model_id": expert_config["model_id"],
            "expert_result": expert_result,
            "expert_safety_warnings": expert_warnings,
            "synthesis_model_id": MOTHER_MODEL,
            "synthesis_result": synthesis_result,
            "synthesis_used": synthesis_used,
            "final_safety_warnings": final_warnings,
            "final_answer": final_answer,
        })


def print_answer_warnings(domain, answer, stage):
    """Inspect an answer, print its warnings, and return the warning list."""
    warnings = inspect_answer(domain, answer)

    if warnings:
        print(f"\\nWARNING: {stage} failed a safety check.")
        for warning in warnings:
            print("-", warning)
        print("Verify the answer before relying on it.")

    return warnings


def should_use_tax_fallback(domain, expert_warnings):
    """Use the cautious fallback when a Tax answer has safety warnings."""
    return domain == "tax" and bool(expert_warnings)


if __name__ == "__main__":
    main()
