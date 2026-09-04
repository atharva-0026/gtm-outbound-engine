"""
Regression test: app/retrieval.py must keep using chromadb.Client()
(in-process, no network listener) and must never switch to
chromadb.HttpClient() or run a Chroma server, which would expose
the 4 known chromadb advisories (CVE-2026-45829, -45830, -45831,
-45833), all unpatched upstream as of chromadb 1.5.9, all requiring
the HTTP server. See requirements.txt/SECURITY.md for the full writeup.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_retrieval_does_not_use_chromadb_http_server():
    with open(os.path.join(BASE_DIR, "app", "retrieval.py"), encoding="utf-8") as f:
        content = f.read()

    assert "chromadb.Client()" in content, "expected in-process chromadb.Client() usage"
    assert "HttpClient" not in content, (
        "chromadb.HttpClient() would run/connect to a Chroma server — "
        "unsafe until the known chromadb CVEs are patched upstream"
    )
    assert "chroma run" not in content


def test_security_md_tracks_all_known_chromadb_cves():
    """SECURITY.md must stay in sync with what pip-audit actually
    reports — this test doesn't call pip-audit itself (no network in
    CI for that), but guards against the doc silently reverting to
    only mentioning the original CVE after someone edits it."""
    with open(os.path.join(BASE_DIR, "SECURITY.md"), encoding="utf-8") as f:
        content = f.read()

    for cve in ["CVE-2026-45829", "CVE-2026-45830", "CVE-2026-45831", "CVE-2026-45833"]:
        assert cve in content, f"SECURITY.md should track {cve}"
