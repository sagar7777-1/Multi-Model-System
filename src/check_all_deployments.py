
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
BASE_URL = "https://api.nugen.in/api/v3"

MODELS = {
    "Finance": "model_01m50emq7xy1cn4y",
    "Legal": "model_01m50enpxws0mn6a",
    "Tax": "model_01m50enq2069gfqm",
}


def main():
    if not API_KEY:
        print("ERROR: NUGEN_API_KEY is missing from .env")
        return

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {API_KEY}"})
    results = {}

    for domain, model_id in MODELS.items():
        print(f"\n{'=' * 50}")
        print(f"{domain}: {model_id}")
        print("=" * 50)

        url = f"{BASE_URL}/models/{model_id}/deployment/status"

        try:
            response = session.get(url, timeout=30)
            print(f"HTTP Status: {response.status_code}")

            try:
                data = response.json()
            except ValueError:
                data = {"raw_response": response.text[:2000]}

            print(json.dumps(data, indent=2))

            results[domain] = {
                "model_id": model_id,
                "http_status": response.status_code,
                "response": data,
            }

            if response.ok:
                status = data.get("status", "").upper()
                if status == "DEPLOYED":
                    print("RESULT: Ready for inference.")
                elif status == "DEPLOYING":
                    print("RESULT: Still deploying; check again later.")
                elif status == "UNDEPLOYED":
                    print("RESULT: Not deployed yet.")
                else:
                    print(f"RESULT: Current status is {status or 'unknown'}.")

        except requests.RequestException as exc:
            results[domain] = {"model_id": model_id, "error": str(exc)}
            print(f"Request error: {exc}")

    output_dir = ROOT / "logs"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "deployment_statuses.json"
    output_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\nSaved results to: {output_file}")


if __name__ == "__main__":
    main()
