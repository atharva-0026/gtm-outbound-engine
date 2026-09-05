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


def test_extract_json_plain_object():
    assert rp._extract_json('{"subject": "a", "body": "b"}') == {"subject": "a", "body": "b"}


def test_extract_json_with_leading_commentary():
    """LLMs commonly ignore 'respond with ONLY valid JSON' and add a
    lead-in sentence."""
    text = 'Sure, here you go:\n{"subject": "a", "body": "b"}'
    assert rp._extract_json(text) == {"subject": "a", "body": "b"}


def test_extract_json_with_trailing_commentary_containing_a_brace():
    """Regression test: the previous greedy regex implementation
    (re.search(r'\\{.*\\}', text, re.DOTALL)) spanned from the first '{'
    to the LAST '}' anywhere in the text, so trailing commentary
    containing even one stray brace produced invalid combined JSON and
    silently fell back to the plain template. Confirmed this exact
    scenario used to raise JSONDecodeError before the fix."""
    text = '{"subject": "a", "body": "b"}\n\nNote: {this follows the format}'
    assert rp._extract_json(text) == {"subject": "a", "body": "b"}


def test_extract_json_with_brace_nested_inside_string_value():
    text = '{"subject": "a", "body": "Saw your {Series B} round"}'
    assert rp._extract_json(text) == {"subject": "a", "body": "Saw your {Series B} round"}


def test_extract_json_raises_when_no_json_present():
    import pytest
    with pytest.raises(ValueError, match="No JSON object found"):
        rp._extract_json("this response has no json at all")
