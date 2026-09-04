# Security Policy

This is a personal/academic project, not a funded product with a
dedicated security team — but reports are still welcome and taken
seriously.

## Reporting a vulnerability

Please open a GitHub issue or contact the repo owner directly rather
than disclosing publicly first, especially for anything involving
credential leakage or remote code execution.

## Known dependency findings

Dependencies are checked with `pip-audit`. As of the last check
(2026-08), chromadb 1.5.9 has 4 known advisories, all unpatched
upstream:

- **CVE-2026-45829** (pre-auth RCE, CVSS 9.3–10.0): malicious
  HuggingFace embedding-function config executes code before auth
  runs, on ChromaDB's Python FastAPI server.
- **CVE-2026-45830** (cross-tenant authorization bypass): any
  authenticated user can read/write/update/delete another tenant's
  collection data.
- **CVE-2026-45831** (SimpleRBACAuthorizationProvider flaw): RBAC
  permissions checked without verifying tenant/database/collection
  scope, enabling cross-tenant actions.
- **CVE-2026-45833**: additional advisory, same family (see
  `pip-audit` output for the current ID).

**All four require ChromaDB's Python FastAPI server** (`HttpClient()`
or a standalone `chroma run` instance) — none are reachable through
in-process usage. This repo only ever calls `chromadb.Client()`
in-process in `app/retrieval.py`, so none of these code paths are
exposed here. See `tests/test_security.py`, which fails loudly if that
ever changes, and the note in `requirements.txt`/`README.md`.

Re-check `pip-audit -r requirements.txt` periodically — do not switch
to `HttpClient()`/`chroma run` until fixes ship for all four.

No other known vulnerabilities were found.
