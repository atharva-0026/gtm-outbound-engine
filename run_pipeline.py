"""
Quick CLI runner — proves the pipeline works without spinning up the API.

Usage:
    python run_pipeline.py data/sample_leads.csv
"""

import csv
import json
import sys

from app.enrichment import enrich_companies
from app.rag_personalize import generate_outreach_rag as generate_outreach
from app.scoring import score_company


def load_csv(path):
    companies = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # start=2: header is line 1
            name = row.get("company_name", f"<row {i}>")
            try:
                row["employee_count"] = int(row["employee_count"])
            except (ValueError, KeyError):
                print(
                    f"WARNING: skipping '{name}' (line {i}) — invalid or missing "
                    f"employee_count: {row.get('employee_count')!r}",
                    file=sys.stderr,
                )
                continue
            row["regulatory_flags"] = [
                f.strip() for f in (row.get("regulatory_flags") or "").split(",") if f.strip()
            ]
            companies.append(row)
    return companies


def main(path):
    companies = load_csv(path)
    results = []
    for c in companies:
        enriched = enrich_companies([c])[0]
        scored = score_company(enriched)
        draft = generate_outreach(scored)
        results.append({**scored, "email_draft": draft})

    results.sort(key=lambda x: x["icp_score"], reverse=True)

    print("\nRANKED LEADS\n" + "=" * 60)
    for r in results:
        print(f"\n{r['company_name']}  —  ICP score: {r['icp_score']}")
        print(f"  breakdown: {r['score_breakdown']}")
        print(f"  subject:   {r['email_draft']['subject']}")

    with open("pipeline_output.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nFull output written to pipeline_output.json\n")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_leads.csv"
    main(csv_path)
