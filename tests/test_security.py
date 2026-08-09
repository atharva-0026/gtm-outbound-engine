"""
Regression test: app/retrieval.py must keep using chromadb.Client()
(in-process, no network listener) and must never switch to
chromadb.HttpClient() or run a Chroma server, which would expose
CVE-2026-45829 (pre-auth RCE, unpatched upstream as of chromadb 1.5.9).
See requirements.txt for the full writeup.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_retrieval_does_not_use_chromadb_http_server():
    with open(os.path.join(BASE_DIR, "app", "retrieval.py"), encoding="utf-8") as f:
        content = f.read()

    assert "chromadb.Client()" in content, "expected in-process chromadb.Client() usage"
    assert "HttpClient" not in content, (
        "chromadb.HttpClient() would run/connect to a Chroma server — "
        "unsafe until CVE-2026-45829 is patched upstream"
    )
    assert "chroma run" not in content
