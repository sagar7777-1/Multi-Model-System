
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")
URL = "https://api.nugen.in/api/v3/inference/completions"

MODEL_ID = "model_01m50emq7xy1cn4y"

PROMPT = """
You are a banking fraud-risk expert.

Question:
How can a bank detect suspicious transactions and reduce fraud risk?

Give a practical, structured answer covering:
1. Transaction signals and anomaly detection.
2. Rules and machine-learning approaches.
3. False positives and customer impact.
4. Human investigation and escalation.
5. Evaluation metrics used to measure fraud detection.

Avoid unrelated techniques. Do not invent performance statistics.
Clearly state any assumptions.
"""


def main():
    if not API_KEY:
        print("ERROR: NUGEN_API_KEY is missing from the project's .env file.")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_ID,
        "prompt": PROMPT,
        "max_tokens": 350,
        "temperature": 0.2,
        "stream": False,
    }

    print("Testing aligned Finance model")
    print(f"Model ID: {MODEL_ID}")
    print(f"Endpoint: {URL}")

    start = time.perf_counter()

    try:
        response = requests.post(
            URL,
            headers=headers,
            json=payload,
            timeout=120,
        )
    except requests.RequestException as exc:
        print(f"\nRequest failed: {exc}")
        return

    elapsed = round(time.perf_counter() - start, 2)

    print(f"\nHTTP Status: {response.status_code}")
    print(f"Latency: {elapsed} seconds")

    try:
        result = response.json()
    except ValueError:
        print("Response was not JSON:")
        print(response.text[:3000])
        return

    if not response.ok:
        print("Inference failed:")
        print(json.dumps(result, indent=2))
        print(
            "\nDo not switch to a base model automatically. "
            "Check the error and deployment status first."
        )
        return

    choices = result.get("choices", [])
    answer = choices[0].get("text", "") if choices else ""

    print("\n" + "=" * 60)
    print("ALIGNED FINANCE MODEL RESPONSE")
    print("=" * 60)
    print(answer if answer else json.dumps(result, indent=2))

    output_dir = ROOT / "logs"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "aligned_finance_test.json"

    saved_result = {
        "model_id": MODEL_ID,
        "http_status": response.status_code,
        "latency_seconds": elapsed,
        "response": result,
    }

    output_file.write_text(
        json.dumps(saved_result, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved test result to: {output_file}")


if __name__ == "__main__":
    main()
