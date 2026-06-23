"""
Enrichment layer.

This is a mock implementation so the pipeline runs end-to-end with zero
API keys. Swap this for real calls when you're ready:

- Clay (clay.com) — data orchestration, the industry-standard tool for this
- Clearbit / Apollo — firmographic data
- BuiltWith / Wappalyzer — technographic data (what tools a company runs)

Keep the function signature the same so main.py never has to change.
"""

from typing import List, Dict


def enrich_companies(companies: List[Dict]) -> List[Dict]:
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
