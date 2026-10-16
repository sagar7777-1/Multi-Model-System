
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_DIR / "logs"
ALIGNMENT_FILE = LOG_DIR / "alignments.json"
OUTPUT_FILE = LOG_DIR / "aligned_models.json"

load_dotenv(PROJECT_DIR / ".env")
API_KEY = os.getenv("NUGEN_API_KEY")

if not API_KEY:
    raise SystemExit(
        "NUGEN_API_KEY is missing from .env. Check the file; do not print the key."
    )

BASE_URL = "https://api.nugen.in/api/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Documented route first; plural route is a fallback to test the API version.
LIST_ENDPOINTS = [
    "/alignment-project",
    "/alignment-projects",
]


def read_json(path):
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def request_json(method, url):
    try:
        response = requests.request(
            method,
            url,
            headers=HEADERS,
            timeout=30,
        )
    except requests.RequestException as error:
        return None, f"Network/request error: {error}"

    print(f"\n{method} {url}")
    print(f"HTTP {response.status_code}")

    try:
        body = response.json()
    except ValueError:
        body = {"raw_response": response.text[:2000]}

    if not response.ok:
        print(json.dumps(body, indent=2))
        return None, f"HTTP {response.status_code}"

    return body, None


def extract_projects(body):
    if isinstance(body, list):
        return body

    if not isinstance(body, dict):
        return []

    for key in ("alignment_projects", "projects", "data", "results"):
        value = body.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            for nested_key in ("alignment_projects", "projects", "results"):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return nested

    return []


def main():
    alignments = read_json(ALIGNMENT_FILE)
    projects = None
    successful_endpoint = None

    print("Looking up existing alignment projects.")
    print("This script does not create or modify alignments.")

    for endpoint in LIST_ENDPOINTS:
        body, error = request_json(
            "GET",
            f"{BASE_URL}{endpoint}",
        )

        if body is not None:
            projects = extract_projects(body)
            successful_endpoint = endpoint
            print(f"Listing endpoint responded successfully: {endpoint}")
            print(f"Projects returned: {len(projects)}")
            break

        print(f"Endpoint unavailable: {endpoint} ({error})")

    results = {}

    if projects is not None:
        for domain, item in alignments.items():
            alignment_id = item["alignment_id"]

            match = next(
                (
                    project
                    for project in projects
                    if isinstance(project, dict)
                    and (
                        project.get("id") == alignment_id
                        or project.get("alignment_id") == alignment_id
                    )
                ),
                None,
            )

            if match:
                model_id = match.get("model_id")
                results[domain] = {
                    "alignment_id": alignment_id,
                    "status": match.get("status"),
                    "model_id": model_id,
                    "evaluation_id": match.get("evaluation_id"),
                    "project_response": match,
                }

                print(f"\n{domain.upper()}")
                print("Alignment ID:", alignment_id)
                print("Status:", match.get("status"))
                print("Model ID:", model_id or "Not supplied by API")
                print(
                    "Evaluation ID:",
                    match.get("evaluation_id") or "Not supplied",
                )
            else:
                print(
                    f"\n{domain}: alignment not found in the "
                    "listing response."
                )
    else:
        print(
            "\nNeither listing route worked. The API route may differ "
            "from the published documentation."
        )
        print(
            "The status endpoint already confirmed your alignments are READY. "
            "Their IDs have been preserved."
        )

    # Always preserve the original IDs and status responses.
    # Do not guess a model ID from an alignment ID.
    for domain, item in alignments.items():
        if domain not in results:
            results[domain] = {
                "alignment_id": item["alignment_id"],
                "status": item.get("status", "UNKNOWN"),
                "model_id": None,
                "evaluation_id": item.get("evaluation_id"),
                "note": (
                    "No deployed model_id was confirmed by the listing API. "
                    "Do not use the alignment ID as a model ID unless Nugen "
                    "explicitly documents that behavior."
                ),
                "saved_status_response": item.get("status_response", {}),
            }

    save_json(OUTPUT_FILE, results)

    print("\nSummary")
    for domain, item in results.items():
        print(
            f"{domain}: status={item.get('status')}, "
            f"model_id={item.get('model_id') or 'NOT CONFIRMED'}"
        )

    print(f"\nListing endpoint used: {successful_endpoint or 'none'}")
    print(f"Saved results to: {OUTPUT_FILE}")

    if not successful_endpoint or any(
        not item.get("model_id") for item in results.values()
    ):
        print(
            "\nNEXT STEP: Share this complete terminal output. "
            "We need to verify Nugen's live API route/model-ID format "
            "before testing inference."
        )


if __name__ == "__main__":
    main()
