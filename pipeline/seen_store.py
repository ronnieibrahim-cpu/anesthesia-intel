"""Persistent "already ingested" ledger for the interim file-based pipeline.

Complements normalize.dedupe_key(): that function dedupes items WITHIN a single
fetch; this module dedupes ACROSS separate runs of run_daily.py, so a deliberately
wide, overlapping lookback window (config/sources.yaml pubmed.lookback_days_default)
doesn't repeatedly re-emit the same item into the accumulating data/untriaged.jsonl
file every time the pipeline runs (docs/decisions/0002).

Interim only: once DATABASE_URL resolves and Step 4/5 land, the `items` table's
UNIQUE(source_id, external_id) constraint is the permanent version of this same
idea, and this module retires.
"""

import json
from pathlib import Path

from pipeline.normalize import dedupe_key


def load(path: Path) -> dict[str, str]:
    """Return {dedupe_key: first_seen_iso_date}, or {} if no ledger exists yet."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save(path: Path, seen: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seen, indent=1, sort_keys=True))


def filter_unseen(rows: list[dict], seen: dict[str, str], today_iso: str):
    """Split rows into (new_rows, updated_seen).

    `new_rows` excludes anything whose dedupe_key is already in `seen`. `updated_seen`
    records EVERY row passed in (new or already-seen) — once an item has been
    considered, that's permanent, regardless of whether it later passes or is
    dropped by the pre-filter. An already-seen row's original first-seen date is
    preserved, never overwritten.
    """
    new_rows = []
    updated = dict(seen)
    for row in rows:
        key = dedupe_key(row)
        if key not in seen:
            new_rows.append(row)
        updated.setdefault(key, today_iso)
    return new_rows, updated
