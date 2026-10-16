
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
if not API_KEY:
    raise SystemExit("NUGEN_API_KEY is missing from your .env file.")

BASE_URL = "https://api.nugen.in/api/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

LOG_DIR = PROJECT_DIR / "logs"
OUTPUT_FILE = LOG_DIR / "benchmarks.json"

DOMAINS = {
    "finance": {
        "document_id": "document_01m50dew64vcay3b",
        "benchmark_name": "Finance Expert Benchmark",
    },
    "legal": {
        "document_id": "document_01m50df20ecms4j0",
        "benchmark_name": "Legal Expert Benchmark",
    },
    "tax": {
        "document_id": "document_01m50df7p8wkftrh",
        "benchmark_name": "Tax Expert Benchmark",
    },
}


def create_benchmark(domain, details):
    response = requests.post(
        f"{BASE_URL}/benchmarks/create",
        headers=HEADERS,
        json={
            "document_ids": [details["document_id"]],
            "benchmark_name": details["benchmark_name"],
            "n_samples": 5,
        },
        timeout=60,
    )

    if not response.ok:
        print(f"Benchmark creation failed for {domain}.")
        print("HTTP status:", response.status_code)
        print("Nugen response:", response.text[:2000])
        response.raise_for_status()

    result = response.json()
    benchmark_id = result.get("benchmark_id")
    if not benchmark_id:
        raise RuntimeError(f"No benchmark_id returned: {result}")

    print(f"{domain}: {benchmark_id} ({result.get('status', 'UNKNOWN')})")
    return {
        "benchmark_id": benchmark_id,
        "benchmark_name": details["benchmark_name"],
        "status": result.get("status", "PROCESSING"),
        "document_id": details["document_id"],
    }


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Avoid accidentally creating duplicate benchmarks on reruns.
    if OUTPUT_FILE.exists():
        print(f"{OUTPUT_FILE} already exists.")
        print("Read the saved IDs before running this script again.")
        print(OUTPUT_FILE.read_text(encoding="utf-8"))
        return

    benchmarks = {}
    for domain, details in DOMAINS.items():
        benchmarks[domain] = create_benchmark(domain, details)

        # Save immediately so IDs aren't lost if a later request fails.
        OUTPUT_FILE.write_text(
            json.dumps(benchmarks, indent=2),
            encoding="utf-8",
        )

        time.sleep(1)

    print("\nBenchmark creation requests completed.")
    print("IDs saved to:", OUTPUT_FILE)
    print("Next: check benchmark status before creating alignments.")


if __name__ == "__main__":
    main()
