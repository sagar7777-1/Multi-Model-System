
import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv


# Load the API key from the project's .env file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
API_URL = "https://api.nugen.in/api/v3/inference/completions"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "aligned_model_tests.jsonl"


# Test each aligned model with a question from its intended domain.
TESTS = [
    {
        "name": "Finance",
        "model_id": "model_01m50emq7xy1cn4y",
        "prompt": """
You are a banking fraud and risk detection expert working in India.

A bank observes the following transaction pattern:
A customer normally makes 2-3 small transactions per day.
Within 10 minutes, the account suddenly makes 8 high-value transfers
to previously unseen beneficiaries.

Explain:
1. Why this pattern may be suspicious.
2. Which transaction features and historical patterns to investigate.
3. How rules and machine-learning anomaly detection could work together.
4. How to control false positives and involve human investigators.

Focus strictly on financial fraud and transaction risk.
Do not suggest sentiment analysis unless relevant transaction text exists.
Do not claim that the pattern proves fraud.
""",
    },
    {
        "name": "Legal",
        "model_id": "model_01m50enpxws0mn6a",
        "prompt": """
You are a legal information assistant focused on Indian law.

An Indian software company wants to use customer personal data
to build an AI-powered customer support system.

Explain:
1. The main privacy and data-protection issues to assess.
2. What consent, notice, purpose limitation, and security measures
   may need consideration under applicable Indian law.
3. What the company should verify before launching.
4. When it should consult a qualified Indian lawyer.

Use India as the jurisdiction. Do not apply US or UK law as if it
were Indian law. Distinguish general information from legal advice,
and do not invent statutory provisions or claim certainty where
the facts or applicable law need verification.
""",
    },
    {
        "name": "Tax",
        "model_id": "model_01m50enq2069gfqm",
        "prompt": """
You are an Indian income-tax information assistant.

An individual living and working in India wants to compare the
old and new income-tax regimes for a financial year.

Explain:
1. What information is needed before comparing the regimes.
2. How eligible deductions and exemptions may affect the comparison.
3. Why the financial year and applicable rules must be confirmed.
4. How to make a fair, side-by-side calculation.

Focus on Indian income tax only. Do not introduce US filing statuses,
US tax credits, or foreign tax rules. Do not invent tax rates,
deduction limits, or exemption amounts. If exact figures are needed,
ask for the relevant financial year and income details.
""",
    },
]


def run_inference(session, test):
    """Send one inference request and return its result."""
    payload = {
        "model": test["model_id"],
        "prompt": test["prompt"].strip(),
        "max_tokens": 250,
        "temperature": 0.2,
        "stream": False,
    }

    started = time.perf_counter()

    try:
        response = session.post(
            API_URL,
            json=payload,
            timeout=120,
        )
        latency_seconds = round(time.perf_counter() - started, 2)

        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_response": response.text[:3000]}

        answer = ""
        if response.ok:
            choices = response_data.get("choices", [])
            if choices:
                answer = choices[0].get("text", "")

                # Support APIs that return chat-style message content.
                if not answer and isinstance(
                    choices[0].get("message"), dict
                ):
                    answer = choices[0]["message"].get("content", "")

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expert": test["name"],
            "model_id": test["model_id"],
            "http_status": response.status_code,
            "latency_seconds": latency_seconds,
            "answer": answer,
            "error": (
                None if response.ok
                else response_data
            ),
        }

        return result

    except requests.RequestException as exc:
        latency_seconds = round(time.perf_counter() - started, 2)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expert": test["name"],
            "model_id": test["model_id"],
            "http_status": None,
            "latency_seconds": latency_seconds,
            "answer": "",
            "error": str(exc),
        }


def main():
    if not API_KEY:
        print("ERROR: NUGEN_API_KEY was not found in the project .env file.")
        print("Check that .env is in the project root.")
        return

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })

    print("=" * 65)
    print("NU​GEN ALIGNED-MODEL INFERENCE TEST")
    print("=" * 65)

    with LOG_FILE.open("a", encoding="utf-8") as log_file:
        for test in TESTS:
            print(f"\n{'=' * 65}")
            print(f"Expert: {test['name']}")
            print(f"Model ID: {test['model_id']}")
            print("=" * 65)
            print("Sending inference request...")

            result = run_inference(session, test)

            print(f"HTTP Status: {result['http_status']}")
            print(f"Latency: {result['latency_seconds']} seconds")

            if result["answer"]:
                print("\nMODEL ANSWER:\n")
                print(result["answer"])
            else:
                print("\nNo answer returned.")
                if result["error"] is not None:
                    print("Error details:")
                    print(json.dumps(result["error"], indent=2))

            # Store each result as one JSON object per line.
            log_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            log_file.flush()

    session.close()

    print(f"\n{'=' * 65}")
    print("TESTING FINISHED")
    print(f"Results saved to: {LOG_FILE}")
    print("=" * 65)


if __name__ == "__main__":
    main()
