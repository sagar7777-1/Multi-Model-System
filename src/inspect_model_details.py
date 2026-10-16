
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
    "finance": "model_01m50emq7xy1cn4y",
    "legal": "model_01m50enpxws0mn6a",
    "tax": "model_01m50enq2069gfqm",
}


def main():
    if not API_KEY:
        print("ERROR: NUGEN_API_KEY missing from .env")
        return

    headers = {"Authorization": f"Bearer {API_KEY}"}
    results = {}

    for domain, model_id in MODELS.items():
        print(f"\n{'=' * 55}")
        print(f"{domain.upper()} MODEL: {model_id}")
        print("=" * 55)

        try:
            response = requests.get(
                f"{BASE_URL}/models/{model_id}",
                headers=headers,
                timeout=30,
            )
            print(f"HTTP Status: {response.status_code}")

            try:
                data = response.json()
            except ValueError:
                data = {"raw_response": response.text[:2000]}

            results[domain] = {
                "http_status": response.status_code,
                "response": data,
            }

            print(json.dumps(data, indent=2))

        except requests.RequestException as exc:
            results[domain] = {"error": str(exc)}
            print(f"Request failed: {exc}")

    output_dir = ROOT / "logs"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "model_details.json"
    output_file.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved full results to: {output_file}")


if __name__ == "__main__":
    main()
