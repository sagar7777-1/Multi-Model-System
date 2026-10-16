
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_DIR / "logs"
ALIGNMENT_FILE = LOG_DIR / "alignments.json"

load_dotenv(PROJECT_DIR / ".env")
API_KEY = os.getenv("NUGEN_API_KEY")

if not API_KEY:
    raise SystemExit("NUGEN_API_KEY is missing from .env")

BASE_URL = "https://api.nugen.in/api/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

MAX_WAIT_SECONDS = 300
POLL_INTERVAL_SECONDS = 15
SUCCESS = {"READY", "COMPLETED", "COMPLETE", "SUCCEEDED"}
FAILURE = {"FAILED", "ERROR", "CANCELLED", "CANCELED"}


def save(data):
    ALIGNMENT_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def main():
    alignments = json.loads(
        ALIGNMENT_FILE.read_text(encoding="utf-8")
    )

    deadline = time.monotonic() + MAX_WAIT_SECONDS

    while time.monotonic() < deadline:
        pending = []

        for domain, item in alignments.items():
            if item.get("status", "").upper() in SUCCESS:
                continue
            if item.get("status", "").upper() in FAILURE:
                continue
            pending.append(domain)

        if not pending:
            break

        for domain in pending:
            alignment_id = alignments[domain]["alignment_id"]
            url = f"{BASE_URL}/alignment-projects/{alignment_id}/status"

            try:
                response = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=30,
                )
            except requests.RequestException as error:
                print(f"{domain}: request error: {error}")
                continue

            print(f"\n{domain}: HTTP {response.status_code}")

            try:
                body = response.json()
            except ValueError:
                body = {"raw_response": response.text}

            print(json.dumps(body, indent=2))

            if not response.ok:
                print("Status check failed; preserving saved records.")
                continue

            # Save the complete response so we can inspect the exact
            # fields Nugen returns, including evaluation/model IDs.
            alignments[domain]["status_response"] = body

            status = body.get("status")
            if not status and isinstance(body.get("data"), dict):
                status = body["data"].get("status")
            if status:
                alignments[domain]["status"] = str(status).upper()

            for key in ("evaluation_id", "model_id", "error", "progress"):
                if key in body:
                    alignments[domain][key] = body[key]
                elif isinstance(body.get("data"), dict) and key in body["data"]:
                    alignments[domain][key] = body["data"][key]

            save(alignments)

        print("\nCurrent summary:")
        for domain, item in alignments.items():
            print(
                f"{domain}: {item.get('status', 'UNKNOWN')} "
                f"| alignment_id={item['alignment_id']} "
                f"| model_id={item.get('model_id', 'not returned yet')} "
                f"| evaluation_id={item.get('evaluation_id', 'not returned yet')}"
            )

        if all(
            item.get("status", "").upper() in SUCCESS | FAILURE
            for item in alignments.values()
        ):
            break

        time.sleep(POLL_INTERVAL_SECONDS)

    print("\nFinal saved summary:")
    for domain, item in alignments.items():
        print(domain, item.get("status", "UNKNOWN"))

    print(f"Full responses saved to: {ALIGNMENT_FILE}")


if __name__ == "__main__":
    main()
