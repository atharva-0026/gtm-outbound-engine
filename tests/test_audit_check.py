import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from audit_check import check  # noqa: E402


def _report(*deps):
    return {"dependencies": list(deps)}


def test_known_unfixed_chromadb_advisory_passes():
    dep = {"name": "chromadb", "version": "1.5.9", "vulns": [{"id": "GHSA-xxxx", "aliases": ["CVE-2026-45829"], "fix_versions": []}]}
    assert check(_report(dep)) == []


def test_known_advisory_with_fix_available_fails():
    dep = {"name": "chromadb", "version": "1.5.9", "vulns": [{"id": "CVE-2026-45829", "fix_versions": ["1.6.0"]}]}
    problems = check(_report(dep))
    assert len(problems) == 1 and "now has a fix (1.6.0)" in problems[0]


def test_new_vulnerability_fails():
    dep = {"name": "requests", "version": "2.0", "vulns": [{"id": "CVE-2099-1", "fix_versions": ["2.1"]}]}
    problems = check(_report(dep))
    assert len(problems) == 1 and "is new" in problems[0]


def test_unknown_chromadb_advisory_is_not_accepted():
    dep = {"name": "chromadb", "version": "1.5.9", "vulns": [{"id": "CVE-2099-9", "fix_versions": []}]}
    assert len(check(_report(dep))) == 1


def test_clean_report_passes():
    assert check(_report({"name": "numpy", "version": "2.0", "vulns": []})) == []
