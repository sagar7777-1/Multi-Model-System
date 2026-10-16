
import json
import sys
from pathlib import Path

# Make router_cli.py importable from this script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from router_cli import inspect_answer


DATASET_PATH = PROJECT_ROOT / "data" / "evaluation_cases.json"
REPORT_PATH = PROJECT_ROOT / "logs" / "evaluation_report.json"


def load_cases():
    """Load evaluation cases from the JSON dataset."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError("The evaluation dataset must be a JSON list.")

    return cases


def evaluate_case(case):
    """Evaluate one candidate answer without making API calls."""
    case_id = case.get("id", "UNKNOWN")
    domain = case.get("domain", "").strip().lower()
    question = case.get("question", "").strip()
    answer = case.get("candidate_answer", "").strip()
    required_facts = case.get("required_facts", [])

    if domain not in {"finance", "legal", "tax"}:
        raise ValueError(
            f"{case_id}: domain must be finance, legal, or tax."
        )

    if not question or not answer:
        raise ValueError(
            f"{case_id}: question and candidate_answer are required."
        )

    if not isinstance(required_facts, list):
        raise ValueError(
            f"{case_id}: required_facts must be a list."
        )

    # Simple case-insensitive phrase matching.
    # This checks wording, not semantic equivalence.
    answer_lower = answer.casefold()

    matched_facts = [
        fact for fact in required_facts
        if isinstance(fact, str)
        and fact.strip()
        and fact.casefold() in answer_lower
    ]

    missing_facts = [
        fact for fact in required_facts
        if not isinstance(fact, str)
        or not fact.strip()
        or fact.casefold() not in answer_lower
    ]

    total_facts = len(required_facts)

    coverage = (
        len(matched_facts) / total_facts * 100
        if total_facts
        else 100.0
    )

    # Reuse the safety checks already present in router_cli.py.
    warnings = inspect_answer(domain, answer)

    if missing_facts:
        status = "FAIL"
    elif warnings:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "id": case_id,
        "domain": domain,
        "status": status,
        "required_fact_coverage_percent": round(coverage, 2),
        "matched_facts": matched_facts,
        "missing_facts": missing_facts,
        "safety_warnings": warnings,
        "question": question
    }


def main():
    cases = load_cases()

    if not cases:
        print("The evaluation dataset contains no cases.")
        return

    results = [evaluate_case(case) for case in cases]

    print("\nNU​​GEN AI ANSWER EVALUATION")
    print("=" * 65)

    for result in results:
        print(
            f"\n[{result['status']}] {result['id']} "
            f"| {result['domain'].upper()}"
        )
        print(
            "Required-fact coverage: "
            f"{result['required_fact_coverage_percent']:.2f}%"
        )

        if result["missing_facts"]:
            print("Missing facts:", ", ".join(result["missing_facts"]))

        if result["safety_warnings"]:
            print("Safety warnings:")
            for warning in result["safety_warnings"]:
                print(f"  - {warning}")

    total = len(results)
    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)
    review = sum(r["status"] == "REVIEW" for r in results)

    average_coverage = sum(
        r["required_fact_coverage_percent"] for r in results
    ) / total

    summary = {
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "needs_review": review,
        "pass_rate_percent": round(passed / total * 100, 2),
        "average_required_fact_coverage_percent": round(
            average_coverage, 2
        ),
        "results": results
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print("SUMMARY")
    print(f"Total cases:       {total}")
    print(f"Passed:            {passed}")
    print(f"Failed:            {failed}")
    print(f"Needs review:      {review}")
    print(f"Pass rate:         {summary['pass_rate_percent']}%")
    print(
        "Average required-fact coverage: "
        f"{summary['average_required_fact_coverage_percent']}%"
    )
    print(f"\nDetailed report saved to:\n{REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Evaluation error: {error}")
        raise SystemExit(1)
