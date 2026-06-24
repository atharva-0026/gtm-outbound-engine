"""
Knowledge base for RAG-based personalization.

Two kinds of documents:
- company_fact: specific facts about each target account (funding, size,
  what they do). Pulled from public sources, dated June 2026.
- industry_context: general AML/compliance pain points tied to a
  regulatory flag (crypto, cross-border, etc). These let retrieval pull
  in relevant context even for companies not explicitly covered below.

Add a company's facts here and it's automatically searchable — no other
code needs to change.
"""

COMPANY_FACTS = [
    {
        "company": "Airwallex",
        "text": (
            "Airwallex is a Singapore-headquartered cross-border payments and "
            "business banking platform with roughly 2,500 employees globally. "
            "It raised a Series G round of $330M in late 2025, valuing the "
            "company at around $8B, and holds multiple money-transmission "
            "licences across jurisdictions it operates in."
        ),
    },
    {
        "company": "Nium",
        "text": (
            "Nium provides cross-border payments infrastructure used by banks "
            "and other financial institutions to move money internationally "
            "in real time. It has raised over $330M to date and operates with "
            "money-transmission and e-money licences across multiple regions, "
            "serving regulated financial institutions as customers."
        ),
    },
    {
        "company": "dLocal",
        "text": (
            "dLocal is a publicly traded (NASDAQ: DLO) payments platform "
            "focused on emerging markets, with about 1,400 employees. It "
            "processes payments across Latin America, Africa, and Asia, "
            "regions that typically carry higher correspondent-banking and "
            "corridor risk than developed-market payment flows."
        ),
    },
    {
        "company": "Bitpanda",
        "text": (
            "Bitpanda is a crypto exchange headquartered in Vienna, Austria, "
            "with roughly 900 employees. It has raised around $589M and "
            "operates under MiCA, the EU's crypto-asset regulatory "
            "framework, which requires ongoing transaction monitoring and "
            "travel-rule compliance."
        ),
    },
    {
        "company": "Wise",
        "text": (
            "Wise is a publicly listed (LSE) cross-border money transfer "
            "company with over 5,500 employees, operating regulated money "
            "transmission services across dozens of countries with "
            "correspondent banking relationships in each."
        ),
    },
    {
        "company": "Revolut",
        "text": (
            "Revolut is a UK-based neobank with over 8,000 employees, "
            "offering banking, crypto trading, and cross-border payments "
            "under one app. Its breadth of regulated products (banking + "
            "crypto + FX) multiplies the number of compliance regimes it "
            "has to satisfy simultaneously."
        ),
    },
]

INDUSTRY_CONTEXT = [
    {
        "flag": "crypto",
        "text": (
            "Crypto exchanges face increasing AML scrutiny under frameworks "
            "like the EU's MiCA and FATF's travel rule, requiring wallet "
            "clustering, chain analysis, and cross-exchange transaction "
            "tracing that manual review teams struggle to scale."
        ),
    },
    {
        "flag": "cross-border payments",
        "text": (
            "Cross-border payment providers must screen transactions against "
            "sanctions and PEP lists across multiple jurisdictions "
            "simultaneously, which multiplies false-positive rates compared "
            "to single-jurisdiction providers and creates a growing backlog "
            "of manual case review."
        ),
    },
    {
        "flag": "high-risk corridors",
        "text": (
            "Payment corridors involving emerging markets carry elevated "
            "correspondent-banking and trade-based money laundering risk, "
            "requiring enhanced due diligence that most rules-based systems "
            "flag too broadly, generating high false-positive volume."
        ),
    },
    {
        "flag": "correspondent banking",
        "text": (
            "Correspondent banking relationships remain a top FATF "
            "enforcement focus following a wave of de-risking and "
            "regulatory fines tied to inadequate counterparty-bank "
            "due diligence."
        ),
    },
    {
        "flag": "neobank",
        "text": (
            "Neobanks scaling user growth quickly often outpace their "
            "compliance headcount, creating a widening gap between "
            "transaction volume and manual review capacity that shows up "
            "as SAR filing backlogs."
        ),
    },
    {
        "flag": "lending",
        "text": (
            "Lending platforms carry AML obligations around tracing loan "
            "proceeds and verifying beneficial ownership of borrowing "
            "entities, which is harder to automate than transaction "
            "monitoring alone."
        ),
    },
]
