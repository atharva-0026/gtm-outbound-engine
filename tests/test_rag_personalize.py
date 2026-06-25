import app.rag_personalize as rp


def test_falls_back_to_template_when_both_llm_backends_fail(monkeypatch):
    monkeypatch.setattr(rp, "_call_ollama", lambda prompt: (_ for _ in ()).throw(ConnectionError("no ollama")))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    company = {"company_name": "Acme", "icp_score": 50, "regulatory_flags": []}
    result = rp.generate_outreach_rag(company)

    assert "template_fallback" in result["generation_method"]
    assert result["subject"]
    assert result["body"]


def test_uses_groq_when_ollama_fails_but_groq_succeeds(monkeypatch):
    monkeypatch.setattr(rp, "_call_ollama", lambda prompt: (_ for _ in ()).throw(ConnectionError("no ollama")))
    monkeypatch.setattr(rp, "_call_groq", lambda prompt: '{"subject": "Test subject", "body": "Test body"}')
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")

    company = {"company_name": "Acme", "icp_score": 50, "regulatory_flags": []}
    result = rp.generate_outreach_rag(company)

    assert "rag_groq" in result["generation_method"]
    assert result["subject"] == "Test subject"


def test_uses_ollama_when_available_even_if_groq_also_configured(monkeypatch):
    monkeypatch.setattr(rp, "_call_ollama", lambda prompt: '{"subject": "Ollama subject", "body": "Ollama body"}')
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-should-not-be-used")

    company = {"company_name": "Acme", "icp_score": 50, "regulatory_flags": []}
    result = rp.generate_outreach_rag(company)

    assert "rag_ollama" in result["generation_method"]


def test_unparseable_model_output_falls_back_to_template(monkeypatch):
    monkeypatch.setattr(rp, "_call_ollama", lambda prompt: "this is not json at all")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    company = {"company_name": "Acme", "icp_score": 50, "regulatory_flags": []}
    result = rp.generate_outreach_rag(company)

    assert "template_fallback" in result["generation_method"]


def test_extra_context_is_included_when_llm_succeeds(monkeypatch):
    captured_prompt = {}

    def fake_ollama(prompt):
        captured_prompt["text"] = prompt
        return '{"subject": "S", "body": "B"}'

    monkeypatch.setattr(rp, "_call_ollama", fake_ollama)

    company = {"company_name": "Acme", "icp_score": 50, "regulatory_flags": []}
    rp.generate_outreach_rag(company, extra_context=["Recent news (funding): Acme raises $10M"])

    assert "Acme raises $10M" in captured_prompt["text"]
