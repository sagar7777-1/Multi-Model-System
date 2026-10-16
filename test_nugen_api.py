
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file.
load_dotenv()

# Read the API key without displaying it.
api_key = os.getenv("NUGEN_API_KEY")

if not api_key:
    raise SystemExit(
        "NUGEN_API_KEY is missing. Check your .env file."
    )

# Official Nugen endpoint for listing base models.
url = "https://api.nugen.in/api/v3/models/base"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
}

try:
    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    print("HTTP status:", response.status_code)

    if not response.ok:
        print("API error:", response.text[:2000])
        raise SystemExit("Connection check failed.")

    # Parse and display the response without exposing the API key.
    try:
        data = response.json()
        output = json.dumps(data, indent=2)
        print(output[:6000])
    except ValueError:
        print(response.text[:2000])

except requests.RequestException as error:
    print("Network request failed:", error)
