
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

load_dotenv(PROJECT_DIR / ".env")
API_KEY = os.getenv("NUGEN_API_KEY")

if not API_KEY:
    raise SystemExit(
        "NUGEN_API_KEY is missing from .env. Check your file without printing the key."
    )

URL = "https://api.nugen.in/api/v3/inference/completions"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

payload = {
    "model": MODEL,
    "prompt": (
        "You are a financial education assistant. "
        "Explain three basic principles of responsible personal budgeting. "
        "Use a short numbered list and do not give personalized investment advice."
    ),
    "max_tokens": 180,
    "temperature": 0.2,
    "stream": False,
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

print("Testing Nugen inference...")
print("Endpoint:", URL)
print("Model:", MODEL)

try:
    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=90,
    )
except requests.RequestException as error:
    raise SystemExit(f"Request failed: {error}")

print("\nHTTP status:", response.status_code)

try:
    result = response.json()
except ValueError:
    result = {"raw_response": response.text[:4000]}

if not response.ok:
    print("API error:")
    print(json.dumps(result, indent=2))
else:
    print("Response:")
    print(json.dumps(result, indent=2))

record = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "endpoint": URL,
    "model": MODEL,
    "http_status": response.status_code,
    "success": response.ok,
    "response": result,
}

with (LOG_DIR / "inference_test.jsonl").open(
    "a",
    encoding="utf-8",
) as file:
    file.write(json.dumps(record, ensure_ascii=False) + "\n")

print("\nTest record saved to logs/inference_test.jsonl")

if response.ok:
    print(
        "\nSUCCESS: Base-model inference works. "
        "This does not yet prove aligned-model inference works."
    )
else:
    print(
        "\nInference failed. Share the HTTP status and error body "
        "so we can correct the request."
    )
