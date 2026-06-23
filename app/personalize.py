"""
Personalized outreach generation.

Template-based for now (zero API cost, runs anywhere). Same architecture
as the RAG-based SAR narrative generator in Aegis: pull facts about the
entity, slot them into a structured narrative. Upgrade path: call the
Claude API here, passing the company's regulatory_flags and icp_score
as context, and let the model write the email instead of the template.
"""

from typing import Dict


def generate_outreach(company: Dict) -> Dict:
    name = company.get("company_name", "there")
    flags = company.get("regulatory_flags", []) or []
    score = company.get("icp_score", 0)

    pain_point = (
        f"your exposure to {', '.join(flags)}"
        if flags
        else "your current compliance workflow"
    )

    subject = f"Cutting AML review time at {name}"
    body = (
        f"Hi {{first_name}},\n\n"
        f"Saw {name} is scaling and figured {pain_point} "
        f"is probably eating analyst hours right now.\n\n"
        f"We built a system that auto-scores transaction risk and drafts "
        f"SAR narratives in seconds instead of hours, cutting manual "
        f"review time significantly for teams your size.\n\n"
        f"Worth a 15-min look?\n\n"
        f"Best,\n{{sender_name}}"
    )

    return {
        "company_name": name,
        "icp_score": score,
        "subject": subject,
        "body": body,
        "upgrade_note": "Replace this template with a Claude API call for true per-account personalization.",
    }
