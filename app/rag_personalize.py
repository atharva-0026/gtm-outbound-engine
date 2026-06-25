"""
RAG-based outreach generation.

Retrieves grounded facts (app/retrieval.py) and passes them to an LLM
for generation, instead of filling a fixed template. Same retrieve-then-
generate pattern as the SAR narrative generator (LangChain + ChromaDB +
Llama 3.1), retargeted from compliance narratives to outreach copy.

Three-tier fallback, in order:
1. Local Ollama (free, unlimited, what you use day-to-day):
    ollama pull llama3.1
2. Groq API (used automatically when Ollama is unreachable — this is
   what makes the cloud-hosted demo work, since Streamlit Community
   Cloud has no GPU/persistent compute to run Ollama on). Free tier,
   no credit card. Get a key at console.groq.com and set GROQ_API_KEY
   as an environment variable (locally) or a Streamlit secret (cloud).
3. Plain template (app/personalize.py) if neither LLM is reachable —
   the pipeline never breaks just because a model server is down.
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

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_TIMEOUT_SECONDS = 30


def _call_ollama(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["response"]


def _call_groq(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        timeout=GROQ_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_llm(prompt: str):
    """Tries Ollama, then Groq. Returns (text, method_used). Raises only
    if both backends fail."""
    try:
        return _call_ollama(prompt), f"rag_ollama_{OLLAMA_MODEL}"
    except Exception as ollama_error:
        try:
            return _call_groq(prompt), f"rag_groq_{GROQ_MODEL}"
        except Exception as groq_error:
            raise RuntimeError(
                f"Ollama failed ({ollama_error}); Groq failed ({groq_error})"
            )


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


def generate_outreach_rag(company: dict, extra_context: list = None) -> dict:
    name = company.get("company_name", "there")
    score = company.get("icp_score", 0)

    try:
        facts = retrieve_for_company(company)
        if extra_context:
            facts = list(facts) + list(extra_context)
        prompt = _build_prompt(company, facts)
        raw, method = _call_llm(prompt)
        parsed = _extract_json(raw)

        return {
            "company_name": name,
            "icp_score": score,
            "subject": parsed["subject"],
            "body": parsed["body"],
            "retrieved_facts": facts,
            "generation_method": method,
        }
    except Exception as e:
        fallback = _template_outreach(company)
        fallback["generation_method"] = f"template_fallback ({type(e).__name__}: {e})"
        return fallback
