"""Compress pre-filtered items for triage, and split them into batches.

`compress()` (implemented in M1 Step 3's --to-file addition) is the tight shape the
triage model actually reads — token efficiency matters because a whole week is scored
inside one Pro session (docs/02 §3). Null fields are omitted and the generic
"Journal Article" publication type is dropped to save tokens.

`make_batches()` (M2) groups compressed items for the /digest triage phase.
"""

# Publication types that carry no triage signal and just cost tokens.
_NOISE_TYPES = {"Journal Article"}


def compress(row: dict) -> dict:
    """Canonical item row -> tight triage dict. Omits nulls to save tokens."""
    out: dict = {"pmid": row.get("pmid"), "title": row.get("title")}
    for key in ("doi", "journal"):
        if row.get(key):
            out[key] = row[key]
    if row.get("published_on"):
        out["date"] = row["published_on"]
    if row.get("study_design"):
        out["design"] = row["study_design"]
    if row.get("sample_size") is not None:
        out["n"] = row["sample_size"]
    if row.get("oa_url"):
        out["oa_url"] = row["oa_url"]
    if row.get("abstract"):
        out["abstract"] = row["abstract"]
    # Drop null pmid if somehow absent, keeping the dict tight.
    if out.get("pmid") is None:
        out.pop("pmid", None)
    return out


def make_batches(items, batch_size):
    """Yield lists of compressed item dicts, `batch_size` at a time."""
    raise NotImplementedError("Implemented in M2 (triage phase).")
