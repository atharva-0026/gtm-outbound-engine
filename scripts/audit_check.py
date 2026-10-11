"""
Gate for `pip-audit --format json` output, used by .github/workflows/audit.yml.

Fails (exit 1) when:
  * any vulnerability is found that is not in ACCEPTED below, or
  * an ACCEPTED vulnerability now has a fixed version upstream - that is the
    signal to bump the pin and close issue #1 (see SECURITY.md).

ACCEPTED holds the chromadb advisories that only affect ChromaDB's HTTP
server; this repo uses chromadb.Client() in-process only (guarded by
tests/test_security.py).

Usage: pip-audit -r requirements.txt --format json | python scripts/audit_check.py
"""
import json
import sys

ACCEPTED = {
    "chromadb": {"CVE-2026-45829", "CVE-2026-45830", "CVE-2026-45831", "CVE-2026-45833"},
}


def check(report: dict) -> list[str]:
    problems = []
    for dep in report.get("dependencies", []):
        name = (dep.get("name") or "").lower()
        for vuln in dep.get("vulns", []):
            ids = {vuln.get("id", "")} | set(vuln.get("aliases") or [])
            label = f"{name} {dep.get('version')}: {vuln.get('id')}"
            if ids & ACCEPTED.get(name, set()):
                if vuln.get("fix_versions"):
                    problems.append(
                        f"{label} now has a fix ({', '.join(vuln['fix_versions'])}) - bump the pin "
                        "in requirements.txt and drop it from ACCEPTED"
                    )
            else:
                fix = ", ".join(vuln.get("fix_versions") or []) or "no fix yet"
                problems.append(f"{label} is new ({fix})")
    return problems


def main() -> int:
    raw = sys.stdin.read()
    if "{" not in raw:
        print("::error::pip-audit produced no JSON report - it failed before auditing (see the step above)")
        return 1
    # pip-audit prints the JSON report on stdout; tolerate a leading log line.
    report = json.loads(raw[raw.index("{"):])
    problems = check(report)
    for p in problems:
        print(f"::error::{p}")
    if not problems:
        print("pip-audit: no new vulnerabilities; accepted chromadb advisories still unfixed upstream")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
