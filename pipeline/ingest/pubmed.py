"""PubMed ingester via NCBI E-utilities (esearch + efetch).

STUB — implemented in M1 Step 3, with pytest tests against fixture XML in
tests/fixtures/ (no live network calls in tests).

Design decided now:
- Reads the search strategy from config/sources.yaml (journal allowlist + topic
  queries); never hard-codes journals or keywords.
- Uses NCBI_API_KEY from the environment when present (higher rate limits);
  works without it.
- Returns list[RawItem] per the interface in pipeline/ingest/__init__.py.
- Abstracts + metadata only (CLAUDE.md rule 2).
"""

import datetime

from pipeline.ingest import RawItem


def fetch(since: datetime.date) -> list[RawItem]:
    """Return PubMed items published/indexed since `since` per config/sources.yaml."""
    raise NotImplementedError("Implemented in M1 Step 3 (PubMed ingester + fixture tests).")
