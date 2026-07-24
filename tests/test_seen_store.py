"""Tests for the persistent cross-run seen-ledger (docs/decisions/0002)."""

from pipeline import seen_store


def _row(pmid, doi=None):
    return {"pmid": pmid, "doi": doi, "url": f"https://pubmed/{pmid}"}


def test_load_missing_returns_empty(tmp_path):
    assert seen_store.load(tmp_path / "nope.json") == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "seen.json"
    seen_store.save(path, {"pmid:1": "2026-07-01"})
    assert seen_store.load(path) == {"pmid:1": "2026-07-01"}


def test_filter_unseen_splits_correctly():
    seen = {"pmid:1": "2026-07-01"}
    rows = [_row("1"), _row("2")]
    new_rows, updated = seen_store.filter_unseen(rows, seen, "2026-07-13")
    assert [r["pmid"] for r in new_rows] == ["2"]
    assert updated == {"pmid:1": "2026-07-01", "pmid:2": "2026-07-13"}


def test_filter_unseen_never_overwrites_existing_first_seen_date():
    seen = {"pmid:1": "2026-06-01"}  # seen weeks ago
    rows = [_row("1")]               # shows up again in a wide overlapping window
    new_rows, updated = seen_store.filter_unseen(rows, seen, "2026-07-13")
    assert new_rows == []                          # excluded: already seen
    assert updated["pmid:1"] == "2026-06-01"        # original date preserved


def test_filter_unseen_empty_seen_marks_everything_new():
    rows = [_row("1"), _row("2"), _row("3")]
    new_rows, updated = seen_store.filter_unseen(rows, {}, "2026-07-13")
    assert len(new_rows) == 3
    assert len(updated) == 3
