
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Project root is the parent of this script's directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
OUTPUT_FILE = LOGS_DIR / "aligned_models.json"

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
BASE_URL = "https://api.nugen.in/api/v3"

EXPECTED_ALIGNMENTS = {
    "finance": "alignment_01m50ejep0r4265z",
    "legal": "alignment_01m50ejf6wpxt2w4",
    "tax": "alignment_01m50ejfrrj4htk2",
}


def main():
    if not API_KEY:
        print("ERROR: NUGEN_API_KEY was not found in the project's .env file.")
        return

    url = f"{BASE_URL}/models/aligned"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"limit": 100, "offset": 0}

    print("Checking Nugen aligned models...")
    print(f"Endpoint: GET {url}")

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"Network error: {exc}")
        return

    print(f"HTTP Status: {response.status_code}")

    try:
        payload = response.json()
    except ValueError:
        print("The API returned a non-JSON response.")
        print(response.text[:1000])
        return

    if not response.ok:
        print("API request failed:")
        print(json.dumps(payload, indent=2))

        if response.status_code == 404:
            print(
                "\nNugen returned 404: no aligned models were found "
                "for this account, according to the endpoint response."
            )
        elif response.status_code == 401:
            print("Check whether the API key is valid.")
        elif response.status_code == 403:
            print("The API key may not have permission to access this resource.")

        return

    models = payload.get("domain_aligned_models", [])

    print(f"\nAligned models returned: {len(models)}")

    results = {
        "endpoint": url,
        "http_status": response.status_code,
        "expected_alignments": EXPECTED_ALIGNMENTS,
        "domain_aligned_models": models,
        "alignment_matches": {},
    }

    for domain, alignment_id in EXPECTED_ALIGNMENTS.items():
        matches = [
            model
            for model in models
            if model.get("alignment_id") == alignment_id
        ]

        results["alignment_matches"][domain] = matches

        print(f"\n--- {domain.upper()} ---")
        if not matches:
            print(f"No model found for {alignment_id}")
            continue

        for model in matches:
            print(f"Model name: {model.get('model_name')}")
            print(f"Model ID: {model.get('model_id')}")
            print(f"Alignment ID: {model.get('alignment_id')}")
            print(f"Deployment status: {model.get('deployment_status')}")

            if model.get("deployment_status") == "DEPLOYED":
                print("Result: Ready for inference.")
            else:
                print("Result: Not currently available for inference.")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print(f"\nFull results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
