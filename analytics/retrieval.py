"""Real embedding + cosine-similarity retrieval over the risk policy doc.

The pipeline this module implements, spelled out for reference:

  document -> chunking -> embeddings -> vector store -> retrieval

- Chunking: split the policy markdown on its "## " section headers. Each
  numbered rule becomes one chunk, a reasonable chunk boundary here since
  each section is a single self-contained rule.
- Embeddings: a small local sentence-transformer model turns each chunk
  (and, at query time, the question) into a dense vector that captures
  meaning, not just keywords, this is what lets "has the fund breached
  any limits" match a chunk that never uses the word "breach".
- Vector store: at this scale (5 chunks) a real vector database is
  overkill. The "store" here is just the chunk embeddings held in memory
  as a small numpy array, computed once at startup.
- Retrieval: cosine similarity between the query embedding and every
  chunk embedding, ranked, top-k returned.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

POLICY_PATH = Path(__file__).parent.parent / "policy" / "risk_policy.md"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None
_chunks: list[str] | None = None
_chunk_embeddings: np.ndarray | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def _chunk_policy(text: str) -> list[str]:
    """Split the policy doc into one chunk per "## " section."""
    sections = re.split(r"\n(?=## )", text)
    return [s.strip() for s in sections if s.strip().startswith("## ")]


def _get_chunks_and_embeddings() -> tuple[list[str], np.ndarray]:
    """Load the policy doc and compute its chunk embeddings once, then cache."""
    global _chunks, _chunk_embeddings
    if _chunks is None or _chunk_embeddings is None:
        text = POLICY_PATH.read_text(encoding="utf-8")
        _chunks = _chunk_policy(text)
        model = _get_model()
        _chunk_embeddings = model.encode(_chunks, normalize_embeddings=True)
    return _chunks, _chunk_embeddings


def retrieve(query: str, top_k: int = 2) -> list[dict]:
    """Return the top_k policy chunks most similar to the query.

    Embeddings are normalized, so cosine similarity reduces to a dot
    product between the query vector and each chunk vector.
    """
    chunks, chunk_embeddings = _get_chunks_and_embeddings()
    model = _get_model()
    query_embedding = model.encode([query], normalize_embeddings=True)[0]

    scores = chunk_embeddings @ query_embedding
    ranked_indices = np.argsort(scores)[::-1][:top_k]

    return [
        {"section": chunks[i].splitlines()[0].lstrip("# ").strip(), "text": chunks[i], "score": round(float(scores[i]), 4)}
        for i in ranked_indices
    ]
