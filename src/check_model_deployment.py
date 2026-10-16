
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

    url = f"{BASE_URL}/models/{MODEL_ID}/deployment/status"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"HTTP Status: {response.status_code}")

        try:
            data = response.json()
        except ValueError:
            print(response.text)
            return

        print(json.dumps(data, indent=2))

        if response.ok:
            status = data.get("status", "").upper()
            if status == "DEPLOYED":
                print("\nSUCCESS: Finance model is ready for inference.")
            elif status == "DEPLOYING":
                print("\nDeployment is still in progress. Check again later.")
            elif status == "UNDEPLOYED" and data.get("error"):
                print("\nDeployment failed. Review the error field.")
            else:
                print(f"\nCurrent deployment status: {status}")

    except requests.RequestException as exc:
        print(f"Request error: {exc}")


if __name__ == "__main__":
    main()
