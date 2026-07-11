"""Database access: one psycopg connection helper + plain SQL. No ORM (docs/02 §2).

STUB — implemented in M1 Step 2 alongside the dbmate migrations.

Design decided now:
- `connect()` reads DATABASE_URL from the environment and returns a psycopg connection.
- Callers use plain, readable SQL strings; anything reused across modules lives here
  as a small named function (e.g. `upsert_items`, `last_sent_digest_date`).
- Idempotency by construction: writes are upserts keyed on a unique `external_id`,
  so re-running any day is always safe (PRD FR-1).
"""


def connect():
    """Return a psycopg connection built from the DATABASE_URL environment variable."""
    raise NotImplementedError("Implemented in M1 Step 2 (migrations + DB access).")
