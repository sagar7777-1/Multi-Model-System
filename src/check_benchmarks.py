
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
    raise SystemExit("NUGEN_API_KEY is missing from .env")

BASE_URL = "https://api.nugen.in/api/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
BENCHMARK_FILE = PROJECT_DIR / "logs" / "benchmarks.json"

# Check for up to 5 minutes.
MAX_WAIT_SECONDS = 300
POLL_INTERVAL_SECONDS = 10

def main():
    benchmarks = json.loads(
        BENCHMARK_FILE.read_text(encoding="utf-8")
    )

    deadline = time.monotonic() + MAX_WAIT_SECONDS
    pending = set(benchmarks.keys())

    while pending and time.monotonic() < deadline:
        for domain in list(pending):
            benchmark_id = benchmarks[domain]["benchmark_id"]
            url = f"{BASE_URL}/benchmarks/{benchmark_id}/status"

            response = requests.get(
                url, headers=HEADERS, timeout=30
            )

            if not response.ok:
                print(f"{domain}: HTTP {response.status_code}")
                print(response.text[:1500])
                response.raise_for_status()

            result = response.json()
            status = str(result.get("status", "UNKNOWN")).upper()
            print(f"{domain}: {status}")

            benchmarks[domain]["status"] = status
            benchmarks[domain]["status_response"] = result

            if status in {"READY", "COMPLETED", "COMPLETE", "SUCCEEDED"}:
                pending.remove(domain)
            elif status in {"FAILED", "ERROR"}:
                raise SystemExit(
                    f"{domain} benchmark failed. Details: {result}"
                )

        (PROJECT_DIR / "logs" / "benchmarks.json").write_text(
            json.dumps(benchmarks, indent=2),
            encoding="utf-8",
        )

        if pending:
            time.sleep(POLL_INTERVAL_SECONDS)

    print("\nLatest benchmark results:")
    for domain, details in benchmarks.items():
        print(domain, details["benchmark_id"], details["status"])

    if pending:
        print("\nSome benchmarks are still processing.")
        print("Run this script again later; do not create duplicates.")
    else:
        print("\nAll benchmarks are ready for the next step.")

if __name__ == "__main__":
    main()
