"""Split pre-filtered items into triage batches of compressed metadata.

STUB — implemented in Milestone M2 with the triage phase of /digest.

Design decided now:
- Batch size comes from config/settings.yaml (budget.triage_batch_size, ~25).
- Each batch entry is compressed metadata (id, title, journal, design/n when parsed,
  abstract) — enough to tier an item, small enough to keep a whole week comfortably
  inside one Pro session (docs/02 §3).
"""


def make_batches(items, batch_size):
    """Yield lists of compressed item dicts, `batch_size` at a time."""
    raise NotImplementedError("Implemented in M2 (triage phase).")
