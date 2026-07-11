"""Society/guideline feed watcher (ASA, ASRA, SCA, ESAIC, SAMBA, ACC/AHA, SCCM).

STUB — implemented in M1 Step 4, following the interface established by pubmed.py.

Change detection ONLY — "a new/updated guideline appeared" (PRD FR-1). No guideline
comparison (that's a V1 non-goal, PRD §7.6). Feed list lives in config/sources.yaml
under `society_feeds:`.
"""

import datetime

from pipeline.ingest import RawItem


def fetch(since: datetime.date) -> list[RawItem]:
    """Return new/updated society feed entries since `since` per config/sources.yaml."""
    raise NotImplementedError("Implemented in M1 Step 4 (society feed watcher).")
