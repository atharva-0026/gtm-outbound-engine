"""
Quick CLI runner — proves the pipeline works without spinning up the API.

Usage:
    python run_pipeline.py data/sample_leads.csv
"""

import sys
import csv
import json

from app.enrichment import enrich_companies
from app.scoring import score_company
from app.personalize import generate_outreach


def load_csv(path):
    companies = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["employee_count"] = int(row["employee_count"])
            row["regulatory_flags"] = [
                f.strip() for f in row["regulatory_flags"].split(",") if f.strip()
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
