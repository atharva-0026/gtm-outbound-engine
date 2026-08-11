# Security Policy

This is a personal/academic project, not a funded product with a
dedicated security team — but reports are still welcome and taken
seriously.

## Reporting a vulnerability

Please open a GitHub issue or contact the repo owner directly rather
than disclosing publicly first, especially for anything involving
credential leakage or remote code execution.

## Known dependency findings

Dependencies are checked with `pip-audit`. As of the last check:

- **CVE-2026-45829** (ChromaDB pre-auth RCE, CVSS 9.3–10.0): affects
  ChromaDB's HTTP server mode. This repo only uses `chromadb.Client()`
  in-process and never runs a Chroma server, so the vulnerable code
  path is not reachable here. See `tests/test_security.py` and the
  note in `requirements.txt`/`README.md`. Still unpatched upstream as
  of chromadb 1.5.9 — do not switch to `HttpClient()` or `chroma run`
  until a fix ships.

No other known vulnerabilities were found.
