"""
RAG-based outreach generation.

Retrieves grounded facts (app/retrieval.py) and passes them to a local
LLM via Ollama for generation, instead of filling a fixed template.
Same retrieve-then-generate pattern as the SAR narrative generator
(LangChain + ChromaDB + Llama 3.1), retargeted from compliance
narratives to outreach copy.

Requires Ollama running locally with a model pulled:
    ollama pull llama3.1
    ollama serve   (usually already running as a background service)

Falls back to the plain template (app/personalize.py) if Ollama isn't
reachable, times out, or returns something unparseable — so the
pipeline never breaks just because the model server is down.
"""

import json
import os
import re

import requests

from app.personalize import generate_outreach as _template_outreach
from app.retrieval import retrieve_for_company

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
OLLAMA_TIMEOUT_SECONDS = 30


def _call_ollama(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["response"]


def _build_prompt(company: dict, facts: list) -> str:
    name = company.get("company_name", "this company")
    facts_block = "\n".join(f"- {f}" for f in facts) if facts else "- No specific facts available."

    return f"""You are writing a short, specific cold outbound email from a sales rep at an AML/compliance software company to a prospect.

Target company: {name}

Facts about the target and relevant industry context (use these, don't invent other facts):
{facts_block}

Write a cold email that:
- References one specific fact above naturally, not as a list
- Identifies a plausible compliance pain point implied by those facts
- Is under 80 words
- Has a clear, low-friction call to action (e.g. a 15-minute call)
- Does not use generic phrases like "I hope this email finds you well" or "I wanted to reach out"

Respond with ONLY valid JSON, no other text, in this exact format:
{{"subject": "...", "body": "..."}}
"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def generate_outreach_rag(company: dict) -> dict:
    name = company.get("company_name", "there")
    score = company.get("icp_score", 0)

    try:
        facts = retrieve_for_company(company)
        prompt = _build_prompt(company, facts)
        raw = _call_ollama(prompt)
        parsed = _extract_json(raw)

        return {
            "company_name": name,
            "icp_score": score,
            "subject": parsed["subject"],
            "body": parsed["body"],
            "retrieved_facts": facts,
            "generation_method": f"rag_ollama_{OLLAMA_MODEL}",
        }
    except Exception as e:
        fallback = _template_outreach(company)
        fallback["generation_method"] = f"template_fallback ({type(e).__name__}: {e})"
        return fallback
