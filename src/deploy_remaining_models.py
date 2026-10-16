
import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
BASE_URL = "https://api.nugen.in/api/v3"

MODELS = {
    "LEGAL": "model_01m50enpxws0mn6a",
    "TAX": "model_01m50enq2069gfqm",
}


def get_status(session, model_id):
    url = f"{BASE_URL}/models/{model_id}/deployment/status"
    response = session.get(url, timeout=30)

    print(f"Status check HTTP: {response.status_code}")
    try:
        data = response.json()
    except ValueError:
        data = {"raw_response": response.text[:2000]}

    print(json.dumps(data, indent=2))

    if not response.ok:
        raise RuntimeError("Could not verify model deployment status.")

    return data.get("status", "").upper()


def main():
    if not API_KEY:
        print("ERROR: NUGEN_API_KEY is missing from .env")
        return

    print("This script can start deployment for Legal and Tax models.")
    print("It will skip models already deployed or currently transitioning.")
    confirm = input("Type DEPLOY to continue: ").strip()

    if confirm != "DEPLOY":
        print("Cancelled. No deployment requests were sent.")
        return

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    })

    for domain, model_id in MODELS.items():
        print(f"\n{'=' * 55}")
        print(f"{domain}: {model_id}")
        print("=" * 55)

        try:
            status = get_status(session, model_id)

            if status == "DEPLOYED":
                print(f"{domain} is already deployed. Skipping.")
                continue

            if status in ("DEPLOYING", "UNDEPLOYING"):
                print(f"{domain} is transitioning ({status}). Skipping.")
                continue

            if status != "UNDEPLOYED":
                print(f"Unexpected status '{status}'. Skipping safely.")
                continue

            deploy_url = f"{BASE_URL}/models/{model_id}/deployment"
            response = session.post(deploy_url, timeout=60)

            print(f"Deployment request HTTP: {response.status_code}")
            try:
                result = response.json()
                print(json.dumps(result, indent=2))
            except ValueError:
                print(response.text[:2000])

            if not response.ok:
                print(f"{domain} deployment request failed.")
            else:
                print(f"{domain} deployment request accepted.")

        except (requests.RequestException, RuntimeError) as exc:
            print(f"Error processing {domain}: {exc}")

    print("\nDeployment requests finished.")
    print("Check each model's deployment status before testing inference.")


if __name__ == "__main__":
    main()
