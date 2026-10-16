
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load the API key from the project's .env file.
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

API_KEY = os.getenv("NUGEN_API_KEY")

if not API_KEY:
    raise SystemExit(
        "ERROR: NUGEN_API_KEY is missing. Check your .env file."
    )

BASE_URL = "https://api.nugen.in"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

DATA_DIR = PROJECT_DIR / "data"
LOG_DIR = PROJECT_DIR / "logs"
OUTPUT_FILE = LOG_DIR / "documents.json"


def validate_jsonl(file_path):
    """Check that each non-empty line is valid JSON."""
    count = 0

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{file_path.name}, line {line_number}: {error}"
                ) from error

            if not isinstance(record, dict):
                raise ValueError(
                    f"{file_path.name}, line {line_number}: "
                    "each line must contain a JSON object."
                )

            if "question" not in record or "answer" not in record:
                raise ValueError(
                    f"{file_path.name}, line {line_number}: "
                    "each record must contain question and answer."
                )

            count += 1

    if count == 0:
        raise ValueError(f"{file_path.name} contains no records.")

    print(f"Validated {file_path.name}: {count} records")


def upload_dataset(file_path):
    """Upload one JSONL dataset using the documented API."""
    url = f"{BASE_URL}/api/v3/documents/create"

    # Do not send a guessed category. It is optional in the API docs.
    with file_path.open("rb") as file:
        files = {
            "files": (file_path.name, file)
        }

        try:
            response = requests.post(
                url,
                headers=HEADERS,
                files=files,
                timeout=60,
            )
        except requests.RequestException as error:
            raise RuntimeError(
                f"Network error uploading {file_path.name}: {error}"
            ) from error

    if not response.ok:
        print(f"\nUpload failed: {file_path.name}")
        print("HTTP status:", response.status_code)
        print("Nugen response:", response.text[:3000])
        raise SystemExit(
            "Stopped. Do not repeatedly retry until this error is understood."
        )

    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError(
            f"Nugen returned a non-JSON response: {response.text[:1000]}"
        ) from error

    document_ids = result.get("document_ids", [])

    if not document_ids:
        raise RuntimeError(
            "Upload response contained no document_ids. "
            f"Response: {result}"
        )

    document_id = document_ids[0]
    print(f"Uploaded {file_path.name}. Document ID: {document_id}")

    return document_id


def wait_until_ready(document_id, max_wait_seconds=120):
    """Poll Nugen until document processing completes."""
    url = f"{BASE_URL}/api/v3/documents/{document_id}/status"
    deadline = time.monotonic() + max_wait_seconds

    while time.monotonic() < deadline:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        if not response.ok:
            print("Status check failed:", response.status_code)
            print("Nugen response:", response.text[:2000])
            response.raise_for_status()

        result = response.json()
        status = str(result.get("status", "UNKNOWN")).upper()

        print(f"Document {document_id}: {status}")

        if status == "READY":
            return result

        if status in {"FAILED", "ERROR"}:
            raise RuntimeError(
                f"Document processing failed: {result}"
            )

        time.sleep(5)

    raise TimeoutError(
        f"Document {document_id} did not become READY within "
        f"{max_wait_seconds} seconds. Check its status before retrying."
    )


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    dataset_names = [
        "finance.jsonl",
        "legal.jsonl",
        "tax.jsonl",
    ]

    # Validate every file before making any upload requests.
    for name in dataset_names:
        file_path = DATA_DIR / name

        if not file_path.is_file():
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        validate_jsonl(file_path)

    documents = {}

    for name in dataset_names:
        file_path = DATA_DIR / name

        document_id = upload_dataset(file_path)
        status_result = wait_until_ready(document_id)

        documents[name] = {
            "document_id": document_id,
            "status": status_result.get("status"),
        }

        # Save progress after each successful upload, so IDs are preserved.
        OUTPUT_FILE.write_text(
            json.dumps(documents, indent=2),
            encoding="utf-8",
        )

    print("\nAll three documents are READY.")
    print(f"Document IDs saved in: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
