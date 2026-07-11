"""FDA safety-communication ingester (MedWatch alerts + drug safety feeds).

STUB — implemented in M1 Step 4, following the interface established by pubmed.py,
with fixture-based tests (no live network calls in tests).

Feed URLs live in config/sources.yaml under `fda:`.
"""

import datetime

from pipeline.ingest import RawItem


def fetch(since: datetime.date) -> list[RawItem]:
    """Return FDA safety items published since `since` per config/sources.yaml."""
    raise NotImplementedError("Implemented in M1 Step 4 (FDA ingester).")
