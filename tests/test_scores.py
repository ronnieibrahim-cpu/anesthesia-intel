"""Tests for triage score validation and the two persistence sinks."""

import pytest

from llm import scores


def _valid_raw(**overrides):
    base = {
        "pmid": "40012345",
        "relevance_tier": "worth_knowing",
        "evidence_level": "B",
        "one_line_takeaway": "Block cut opioid use after VATS.",
        "reasoning": "RCT in a population the attending staffs.",
        "topics": ["regional anesthesia", "opioid-sparing"],
        "confidence": 0.8,
    }
    base.update(overrides)
    return base


# ---- validate() --------------------------------------------------------------

def test_validate_happy_path_normalizes():
    out = scores.validate(_valid_raw(pmid=40012345, confidence=0.8049))
    assert out["pmid"] == "40012345"          # coerced to str
    assert out["confidence"] == 0.8           # rounded to 2 dp
    assert out["relevance_tier"] == "worth_knowing"


def test_validate_uppercases_grade():
    assert scores.validate(_valid_raw(evidence_level="b"))["evidence_level"] == "B"


def test_validate_allows_empty_topics_list():
    assert scores.validate(_valid_raw(topics=[]))["topics"] == []


@pytest.mark.parametrize("bad_tier", ["PracticeChanging", "great", "", None])
def test_validate_rejects_bad_tier(bad_tier):
    with pytest.raises(ValueError):
        scores.validate(_valid_raw(relevance_tier=bad_tier))


@pytest.mark.parametrize("bad_grade", ["E", "A+", "", None, 1])
def test_validate_rejects_bad_grade(bad_grade):
    with pytest.raises(ValueError):
        scores.validate(_valid_raw(evidence_level=bad_grade))


def test_validate_requires_pmid():
    raw = _valid_raw()
    del raw["pmid"]
    with pytest.raises(ValueError, match="pmid"):
        scores.validate(raw)


@pytest.mark.parametrize("bad_conf", [-0.1, 1.1, "0.5", True, None])
def test_validate_rejects_bad_confidence(bad_conf):
    with pytest.raises(ValueError):
        scores.validate(_valid_raw(confidence=bad_conf))


def test_validate_rejects_empty_takeaway_and_reasoning():
    with pytest.raises(ValueError):
        scores.validate(_valid_raw(one_line_takeaway="   "))
    with pytest.raises(ValueError):
        scores.validate(_valid_raw(reasoning=""))


def test_validate_rejects_non_string_topics():
    with pytest.raises(ValueError):
        scores.validate(_valid_raw(topics=["ok", 3]))


def test_error_names_the_pmid():
    with pytest.raises(ValueError, match="40012345"):
        scores.validate(_valid_raw(relevance_tier="bogus"))


# ---- file sink ---------------------------------------------------------------

def test_write_and_load_current_scores(tmp_path):
    path = tmp_path / "predictions.jsonl"
    validated = [scores.validate(_valid_raw())]
    n = scores.write_scores_to_file(path, validated, "sonnet", "triage-v1", "2026-07-10")
    assert n == 1

    current = scores.load_current_scores(path)
    rec = current["40012345"]
    assert rec["relevance_tier"] == "worth_knowing"
    assert rec["model"] == "claude-code-session/sonnet"
    assert rec["prompt_version"] == "triage-v1"
    assert rec["profile_version"] == "2026-07-10"
    assert "created_at" in rec


def test_append_only_latest_wins(tmp_path):
    path = tmp_path / "predictions.jsonl"
    scores.write_scores_to_file(path, [scores.validate(_valid_raw(relevance_tier="fyi"))],
                                "sonnet", "triage-v1", "2026-07-10")
    scores.write_scores_to_file(path, [scores.validate(_valid_raw(relevance_tier="practice_changing"))],
                                "sonnet", "triage-v2", "2026-07-10")
    # Both lines are on disk (append-only)...
    assert sum(1 for _ in path.open()) == 2
    # ...but the current score is the latest one written for that pmid.
    assert scores.load_current_scores(path)["40012345"]["relevance_tier"] == "practice_changing"


def test_load_missing_file_is_empty(tmp_path):
    assert scores.load_current_scores(tmp_path / "nope.jsonl") == {}


# ---- DB sink (fake connection; no live database) -----------------------------

class _FakeCursor:
    def __init__(self, ids_by_pmid):
        self.ids_by_pmid = ids_by_pmid
        self.executed = []
        self._fetch = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))
        if sql.strip().startswith("SELECT id FROM items"):
            pmid = params[0]
            self._fetch = (self.ids_by_pmid[pmid],) if pmid in self.ids_by_pmid else None

    def fetchone(self):
        return self._fetch


class _FakeConn:
    def __init__(self, ids_by_pmid):
        self._cursor = _FakeCursor(ids_by_pmid)
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True


def test_write_scores_db_flips_current_and_inserts():
    conn = _FakeConn({"40012345": 10})
    result = scores.write_scores(conn, [scores.validate(_valid_raw())],
                                 "sonnet", "triage-v1", "2026-07-10")
    assert result == {"written": 1, "skipped": []}
    assert conn.committed
    sqls = [sql for sql, _ in conn._cursor.executed]
    assert any(s.startswith("SELECT id FROM items") for s in sqls)
    assert any(s.startswith("UPDATE scores SET is_current = false") for s in sqls)
    assert any(s.startswith("INSERT INTO scores") for s in sqls)
    # provenance recorded on the insert
    insert = next(p for s, p in conn._cursor.executed if s.startswith("INSERT"))
    assert "claude-code-session/sonnet" in insert
    assert "triage-v1" in insert


def test_write_scores_db_skips_unknown_pmid():
    conn = _FakeConn({})  # no items match
    result = scores.write_scores(conn, [scores.validate(_valid_raw())],
                                 "sonnet", "triage-v1", "2026-07-10")
    assert result["written"] == 0
    assert result["skipped"] == ["40012345"]
    # nothing inserted for an unknown item
    assert not any(s.startswith("INSERT") for s, _ in conn._cursor.executed)
