"""
Retriever ("System 1")
-----------------------
Simulates a knowledge-base / vector-store lookup. In production this would
call a real vector DB (pgvector, Pinecone, etc). It's kept in-memory here so
the whole pipeline runs deterministically with zero external dependencies —
that's what makes the eval suite and CI gate reproducible.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class RetrievedDoc:
    doc_id: str
    text: str
    score: float


_KNOWLEDGE_BASE = {
    "refund_policy": "Refunds are issued within 14 days of purchase if the "
                      "item is unused and in original packaging.",
    "shipping_policy": "Standard shipping takes 3-5 business days within the "
                        "country. International orders take 7-14 business days.",
    "warranty_policy": "All electronics carry a 12-month manufacturer warranty "
                        "covering defects, not accidental damage.",
    "support_hours": "Customer support is available Monday to Friday, "
                      "9am-6pm local time, excluding public holidays.",
}


def retrieve(query: str, top_k: int = 1) -> list[RetrievedDoc]:
    """Very small keyword-overlap retriever, standing in for a real
    embedding-similarity search. Returns the top_k scoring documents."""
    query_tokens = set(query.lower().split())
    scored = []
    for doc_id, text in _KNOWLEDGE_BASE.items():
        doc_tokens = set((doc_id + " " + text).lower().replace(".", "").split())
        overlap = len(query_tokens & doc_tokens)
        score = overlap / max(len(query_tokens), 1)
        scored.append(RetrievedDoc(doc_id=doc_id, text=text, score=score))

    scored.sort(key=lambda d: d.score, reverse=True)
    return scored[:top_k]
