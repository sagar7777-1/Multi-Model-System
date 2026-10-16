
import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
BASE_URL = "https://api.nugen.in/api/v3"
MODEL_ID = "model_01m50emq7xy1cn4y"


def main():
    if not API_KEY:
        print("ERROR: NUGEN_API_KEY is missing from .env")
        return

    print("Finance model deployment")
    print(f"Model ID: {MODEL_ID}")
    print("This request starts an asynchronous deployment.")
    confirm = input("Type DEPLOY to continue: ").strip()

    if confirm != "DEPLOY":
        print("Cancelled. No deployment request was sent.")
        return

    headers = {"Authorization": f"Bearer {API_KEY}"}

    # Check the current deployment status first.
    status_url = f"{BASE_URL}/models/{MODEL_ID}/deployment/status"

    try:
        status_response = requests.get(
            status_url,
            headers=headers,
            timeout=30,
        )
        print(f"\nStatus check HTTP: {status_response.status_code}")
        print(status_response.text)

        if not status_response.ok:
            print("Could not verify current status. Deployment not attempted.")
            return

        current = status_response.json()
        status = current.get("status", "").upper()

        if status == "DEPLOYED":
            print("Model is already deployed. Nothing to do.")
            return

        if status in ("DEPLOYING", "UNDEPLOYING"):
            print(f"Deployment transition already in progress: {status}")
            print("Wait for it to finish, then check status again.")
            return

        if status != "UNDEPLOYED":
            print(f"Unexpected status: {status}")
            print("Do not deploy until the status is understood.")
            return

        # Start deployment only after the explicit confirmation above.
        deploy_url = f"{BASE_URL}/models/{MODEL_ID}/deployment"
        response = requests.post(
            deploy_url,
            headers=headers,
            timeout=60,
        )

        print(f"\nDeployment request HTTP: {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except ValueError:
            print(response.text)

        if response.ok:
            print("\nDeployment request accepted.")
            print("Check status again after a few minutes using:")
            print(f"python src/check_model_deployment.py")
        else:
            print("\nDeployment request failed. Save the error response.")

    except requests.RequestException as exc:
        print(f"Request error: {exc}")


if __name__ == "__main__":
    main()
