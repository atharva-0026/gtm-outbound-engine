"""
Retrieval layer for RAG personalization.

Hybrid retrieval, not pure semantic search:
1. Direct lookup of the target company's own curated fact (deterministic
   metadata match — you always want a company's own facts in its email,
   not whatever a similarity score happens to rank highest).
2. Direct lookup of industry-context docs matching the company's known
   regulatory_flags (also deterministic — we already know the flags,
   no need to guess via embeddings).
3. Semantic TF-IDF search as a fallback ONLY for companies not in the
   curated knowledge base, so the system still produces something
   reasonable for unseen accounts instead of failing.

Uses ChromaDB as the vector store for step 3, with TF-IDF vectors
instead of a downloaded neural embedding model — keeps this fully
offline. Swap `_build` for sentence-transformers later if you want
denser semantic search; nothing downstream changes.
"""

import chromadb
from sklearn.feature_extraction.text import TfidfVectorizer

from app.knowledge_base import COMPANY_FACTS, INDUSTRY_CONTEXT

_collection = None
_vectorizer = None


def _all_documents():
    docs = []
    for fact in COMPANY_FACTS:
        docs.append(
            {
                "id": f"company:{fact['company']}",
                "text": fact["text"],
                "metadata": {"type": "company_fact", "company": fact["company"]},
            }
        )
    for ctx in INDUSTRY_CONTEXT:
        docs.append(
            {
                "id": f"industry:{ctx['flag']}",
                "text": ctx["text"],
                "metadata": {"type": "industry_context", "flag": ctx["flag"]},
            }
        )
    return docs


def _build():
    global _collection, _vectorizer
    if _collection is not None:
        return _collection, _vectorizer

    docs = _all_documents()
    texts = [d["text"] for d in docs]

    _vectorizer = TfidfVectorizer(stop_words="english")
    matrix = _vectorizer.fit_transform(texts)
    embeddings = matrix.toarray().tolist()

    client = chromadb.Client()
    _collection = client.get_or_create_collection("gtm_knowledge_base")
    _collection.add(
        ids=[d["id"] for d in docs],
        embeddings=embeddings,
        documents=texts,
        metadatas=[d["metadata"] for d in docs],
    )
    return _collection, _vectorizer


def semantic_retrieve(query: str, k: int = 3):
    """Pure semantic fallback search over the whole knowledge base."""
    collection, vectorizer = _build()
    query_vec = vectorizer.transform([query]).toarray().tolist()
    results = collection.query(query_embeddings=query_vec, n_results=k)
    return results["documents"][0] if results["documents"] else []


def retrieve_for_company(company: dict, k_industry: int = 2):
    """Hybrid retrieval: structured lookups first, semantic fallback only
    if the company isn't in the curated knowledge base."""
    company_name = (company.get("company_name") or "").strip()
    flags = set(f.lower() for f in (company.get("regulatory_flags") or []))

    docs = []

    own_fact = next(
        (f["text"] for f in COMPANY_FACTS if f["company"].lower() == company_name.lower()),
        None,
    )
    if own_fact:
        docs.append(own_fact)

    matched_context = [c["text"] for c in INDUSTRY_CONTEXT if c["flag"].lower() in flags]
    docs.extend(matched_context[:k_industry])

    if not docs:
        query = f"{company_name} {' '.join(flags)} AML compliance pain points"
        docs = semantic_retrieve(query, k=3)

    return docs
