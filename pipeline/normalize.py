"""Normalize RawItems into canonical item rows; compute the dedupe key.

STUB — implemented in M1 Step 4 (after the first ingester exists in Step 3).

Design decided now:
- One canonical dict per item matching the `items` table columns.
- Dedupe key precedence: DOI, else PMID, else a stable hash of the URL (PRD FR-1).
- Deduplication itself is NOT in-memory bookkeeping: it is a DB upsert on the unique
  `external_id` column, so re-running any day — or a killed mid-run job — is
  idempotent by construction (M1 acceptance criterion).
"""


def normalize(raw_items):
    """Turn list[RawItem] into canonical item rows ready for upsert."""
    raise NotImplementedError("Implemented in M1 Step 4 (normalize + dedupe).")
