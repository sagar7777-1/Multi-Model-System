
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NUGEN_API_KEY", "").strip()
API_URL = "https://api.nugen.in/api/v3/inference/completions"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

if not API_KEY:
    raise ValueError("NUGEN_API_KEY is missing from .env")


def call_nugen(prompt, max_tokens=250):
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "stream": False,
        },
        timeout=60,
    )

    response.raise_for_status()
    data = response.json()

    # This endpoint returns generated text in choices[0].text.
    return data["choices"][0]["text"].strip()


def legal_expert(question):
    prompt = f"""
You are the legal analysis expert in a business advisory system.
Identify relevant legal considerations, registrations, and risks.
Do not invent laws. Ask for jurisdiction when it is missing.
Question: {question}
"""
    return call_nugen(prompt)


def finance_expert(question):
    prompt = f"""
You are the finance expert in a business advisory system.
Identify startup costs, cash flow, budgeting factors, and financial risks.
State assumptions and do not invent numerical estimates.
Question: {question}
"""
    return call_nugen(prompt)


def tax_expert(question):
    prompt = f"""
You are the tax expert in a business advisory system.
Identify relevant tax and GST considerations and compliance questions.
Ask for jurisdiction when it is missing. Do not invent tax rules.
Question: {question}
"""
    return call_nugen(prompt)


def legal_expert(question: str) -> str:
    """Temporary mock for the legal expert."""
    return (
        "[MOCK LEGAL EXPERT] "
        f"Review the legal requirements related to: {question}"
    )


def finance_expert(question: str) -> str:
    """Temporary mock for the finance expert."""
    return (
        "[MOCK FINANCE EXPERT] "
        f"Identify budget, cash flow, and financial risks for: {question}"
    )


def tax_expert(question: str) -> str:
    """Temporary mock for the tax expert."""
    return (
        "[MOCK TAX EXPERT] "
        f"Identify tax questions and filing obligations for: {question}"
    )
