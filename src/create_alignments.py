
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

load_dotenv(PROJECT_DIR / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
if not API_KEY:
    raise SystemExit("NUGEN_API_KEY is missing from .env")

BASE_URL = "https://api.nugen.in/api/v3"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Each expert uses its own domain dataset and benchmark.
CONFIG = {
    "finance": {
        "alignment_name": "Finance Domain Expert",
        "base_model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "document_id": "document_01m50dew64vcay3b",
        "benchmark_id": "benchmark_01m50e6f3rfcvsfj",
        "description": "Finance Q&A and financial reasoning domain alignment.",
    },
    "legal": {
        "alignment_name": "Legal Domain Expert",
        "base_model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "document_id": "document_01m50df20ecms4j0",
        "benchmark_id": "benchmark_01m50e6gc68v8nsa",
        "description": "Legal information and legal reasoning domain alignment.",
    },
    "tax": {
        "alignment_name": "Tax Domain Expert",
        "base_model_id": "meta-llama/Llama-3.2-3B-Instruct",
        "document_id": "document_01m50df7p8wkftrh",
        "benchmark_id": "benchmark_01m50e6hnkst7d5w",
        "description": "Tax concepts and tax Q&A domain alignment.",
    },
}

OUTPUT_FILE = LOG_DIR / "alignments.json"


def save_results(results):
    OUTPUT_FILE.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )


def main():
    if OUTPUT_FILE.exists():
        results = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    else:
        results = {}

    for domain, config in CONFIG.items():
        # Avoid creating a duplicate if this script is run again.
        if results.get(domain, {}).get("alignment_id"):
            print(
                f"{domain}: already recorded as "
                f"{results[domain]['alignment_id']} "
                f"(status: {results[domain].get('status', 'UNKNOWN')})"
            )
            continue

        payload = {
            "alignment_name": config["alignment_name"],
            "base_model_id": config["base_model_id"],
            "document_ids": [config["document_id"]],
            "benchmark_id": config["benchmark_id"],
            "description": config["description"],
        }

        print(f"\nCreating {domain} alignment...")

        try:
            response = requests.post(
                f"{BASE_URL}/alignment-projects/create",
                headers=HEADERS,
                json=payload,
                timeout=60,
            )
        except requests.RequestException as error:
            print(f"{domain}: request failed: {error}")
            print("Rerun later; saved alignment IDs will be skipped.")
            break

        try:
            body = response.json()
        except ValueError:
            body = {"raw_response": response.text}

        print(f"HTTP {response.status_code}")
        print(json.dumps(body, indent=2))

        # Nugen may report an existing matching alignment with HTTP 422.
        # If it returns an alignment ID, record it rather than duplicating it.
        alignment_id = body.get("alignment_id")

        if not response.ok and not alignment_id:
            print(f"{domain}: creation failed. Fix the error above before retrying.")
            break

        if not alignment_id:
            print(f"{domain}: response did not contain alignment_id.")
            break

        results[domain] = {
            "alignment_id": alignment_id,
            "status": body.get("status", "PROCESSING"),
            "base_model_id": config["base_model_id"],
            "document_id": config["document_id"],
            "benchmark_id": config["benchmark_id"],
            "create_response": body,
        }

        # Save immediately after each successful creation.
        save_results(results)

    print("\nSaved alignment records:")
    for domain, details in results.items():
        print(
            f"{domain}: {details['alignment_id']} "
            f"| {details.get('status', 'UNKNOWN')}"
        )

    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
