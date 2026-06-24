"""
Checks for new public signals (funding, regulatory licences, partnerships,
acquisitions) on your tracked leads, and prints only what's new since the
last check.

Run manually:
    python check_signals.py data/real_leads.csv

Run on a schedule (recommended — this is what makes it "monitoring"
instead of a one-off check):

  macOS, daily at 9am, using launchd:
    1. Create ~/Library/LaunchAgents/com.gtm.signalcheck.plist with a
       <key>ProgramArguments</key> pointing to this script and your
       python3 path, and <key>StartCalendarInterval</key> with Hour=9.
    2. launchctl load ~/Library/LaunchAgents/com.gtm.signalcheck.plist

  Simpler alternative — cron:
    crontab -e
    0 9 * * * cd /path/to/gtm-outbound-engine && /usr/bin/python3 check_signals.py data/real_leads.csv >> signal_log.txt 2>&1
"""

import sys

from app.signals import check_for_new_signals
from run_pipeline import load_csv


def main(csv_path):
    companies = load_csv(csv_path)
    new_signals = check_for_new_signals(companies)

    if not new_signals:
        print("No new signals since last check.")
        return

    print(f"\n{len(new_signals)} companies with new signals:\n" + "=" * 60)
    for company_name, signals in new_signals.items():
        print(f"\n{company_name}")
        for s in signals:
            print(f"  [{s['category'].upper()}] {s['title']}")
            print(f"    {s['link']}")
    print(f"\nRecommended action: re-score and consider re-engaging the companies above.")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/real_leads.csv"
    main(csv_path)
