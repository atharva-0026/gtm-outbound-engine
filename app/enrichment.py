"""
Enrichment layer.

This is a mock implementation so the pipeline runs end-to-end with zero
API keys. Set ENRICHMENT_PROVIDER=live (see _enrich_live below) once a
real provider is wired in; defaults to "mock" so nothing changes for
anyone who hasn't configured a provider.

Provider status as of 2026-09 (checked, not assumed):
- Clay (clay.com) — still the industry-standard orchestration tool for
  this; layers multiple sources rather than being a single API itself.
- Clearbit — DEAD as a standalone product. Acquired by HubSpot (Dec
  2023), folded into "Breeze Intelligence" inside HubSpot's CRM. All
  free tools and the standalone API were sunset by April 2025. There
  is no independent Clearbit API left to integrate against — remove
  this from consideration entirely, don't build against it.
- Apollo.io — still a real, live standalone product with a real API,
  but API access specifically requires a paid plan (Professional
  tier, ~$79/user/month+) — the free tier explicitly excludes API
  access. Real option, just not one that can be tested without a
  paid account.
- BuiltWith / Wappalyzer — technographic data (what tools a company
  runs), not re-verified this pass.

Keep the function signature the same so main.py never has to change.
"""
import os


def enrich_companies(companies: list[dict]) -> list[dict]:
    provider = os.environ.get("ENRICHMENT_PROVIDER", "mock")
    if provider == "mock":
        return _enrich_mock(companies)
    return _enrich_live(companies, provider)


def _enrich_mock(companies: list[dict]) -> list[dict]:
    enriched = []
    for c in companies:
        c = dict(c)
        c.setdefault("employee_count", 50)
        c.setdefault("funding_stage", "unknown")
        c.setdefault("country", "unknown")
        c.setdefault("regulatory_flags", [])
        c["enrichment_source"] = "mock_v1"
        enriched.append(c)
    return enriched


def _enrich_live(companies: list[dict], provider: str) -> list[dict]:
    """
    Placeholder for a real enrichment provider integration.

    Intentionally NOT implemented against a specific provider yet - see
    the module docstring for current provider status (Clearbit is dead,
    Apollo requires a paid plan for API access). Whoever wires this in
    with real credentials should implement the actual HTTP call here,
    keeping the same list[dict] -> list[dict] signature and setting
    enrichment_source to something identifying the real provider (e.g.
    "apollo_v1"), matching the "mock_v1" convention above.

    Raises clearly rather than silently falling back to mock data, so
    a misconfigured ENRICHMENT_PROVIDER env var fails loudly instead of
    quietly running on fake data in what looks like a real run.
    """
    raise NotImplementedError(
        f"ENRICHMENT_PROVIDER={provider!r} is not implemented. "
        "No live enrichment provider is wired in yet - see app/enrichment.py's "
        "module docstring for current provider research. Unset "
        "ENRICHMENT_PROVIDER (or set it to 'mock') to use mock data."
    )
