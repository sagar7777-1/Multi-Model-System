# Nugen Multi-Domain AI Router

A Python prototype that routes user questions to specialized Nugen aligned models for finance, legal, and tax topics.

## Features

- Keyword-based domain routing for Finance, Legal, and Tax.
- Ambiguity handling for questions spanning multiple domains.
- Tax questions require an explicit financial year or assessment year.
- Specialized model calls through the Nugen inference API.
- Answer-safety checks and a cautious fallback for flagged tax responses.
- Optional answer synthesis and JSONL inference logging.
- Automated unit tests for routing and safety behavior.

## Project Structure

```text
.
├── data/       # Domain-specific sample datasets
├── src/        # Router and supporting scripts
├── tests/      # Automated unit tests
├── logs/       # Generated logs; excluded from Git
├── .env        # Local API key; must not be committed
├── .gitignore
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.10 or newer
- A Nugen API key and access to the required models
- Internet access for API inference

## Setup

1. Open a terminal in the project directory.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Create a local `.env` file containing your Nugen API key:

   ```text
   NUGEN_API_KEY=your_api_key_here
   ```

   Replace the placeholder locally. Never commit or share your real API key.

## Run the Router

From the project root, run:

```powershell
python src/router_cli.py
```

If your local workflow uses a different entry point, see `run_demo.py` and the scripts under `src/`.

## Run Tests

```powershell
python -m unittest discover -s tests -v
```

The current automated suite contains 24 tests covering domain routing, tax-year validation, answer-safety checks, and fallback behavior.

## Limitations

- This is a prototype, not a production financial, legal, or tax advisory system.
- Model output can be incorrect, incomplete, or outdated. Verify consequential information against authoritative sources.
- Automated safety checks are heuristic and cannot guarantee factual correctness or prevent every unsafe answer.
- Live inference requires valid credentials, API availability, and access to the configured models.
- The current test suite does not establish production readiness or guarantee model accuracy.

## Security

- Keep `.env` private.
- Do not commit `.venv/`, API credentials, or generated logs.
- Review all files and sample datasets for sensitive information before publishing.
