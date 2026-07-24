"""Tests for run_daily's --to-file path (docs/decisions/0001, 0002).

No network: pubmed.fetch is monkeypatched. Default-target tests exercise the
seen-ledger cross-run dedupe against isolated tmp_path files; explicit-path tests
confirm that mode stays a fresh, ledger-independent overwrite.
"""

import json
from pathlib import Path

import pytest

from pipeline import run_daily
from pipeline.ingest.pubmed import parse_efetch_xml

FIXTURE = Path(__file__).parent / "fixtures" / "pubmed_efetch_sample.xml"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Replace the one network call with fixture-backed RawItems."""
    raw = parse_efetch_xml(FIXTURE.read_bytes())
    monkeypatch.setattr(run_daily.pubmed, "fetch", lambda since: raw)
    # enrich() also hits the network (Unpaywall/PMC) for non-dry-run calls; keep
    # these tests deterministic and network-free by making both lookups miss.
    monkeypatch.setattr(run_daily.enrich, "_unpaywall_get", lambda doi: {})
    monkeypatch.setattr(run_daily.enrich, "_pmc_elink", lambda pmid: {})


@pytest.fixture(autouse=True)
def _isolated_default_paths(tmp_path, monkeypatch):
    """Point the default target + ledger at tmp_path so tests never touch data/."""
    monkeypatch.setattr(run_daily, "UNTRIAGED_PATH", tmp_path / "untriaged.jsonl")
    monkeypatch.setattr(run_daily, "SEEN_PATH", tmp_path / ".seen_ids.json")


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().strip().splitlines()]


def test_first_run_appends_all_passing_items():
    run_daily.main(["--days", "7"])
    lines = _lines(run_daily.UNTRIAGED_PATH)
    # 3 fixture items; the letter is dropped by config/filters.yaml -> 2 pass.
    assert len(lines) == 2
    assert lines[0]["pmid"] == "40000001"
    assert "oa_url" not in lines[0]                 # null field omitted


def test_second_run_with_same_data_appends_nothing_new():
    run_daily.main(["--days", "7"])
    first_size = run_daily.UNTRIAGED_PATH.stat().st_size
    summary = run_daily.run(run_daily._parse_args(["--days", "7"]))
    assert summary["new_since_last_run"] == 0
    assert summary["passed"] == 0
    # File is unchanged: nothing new was appended on the second run.
    assert run_daily.UNTRIAGED_PATH.stat().st_size == first_size
    assert len(_lines(run_daily.UNTRIAGED_PATH)) == 2


def test_reset_seen_forces_full_resurface():
    run_daily.main(["--days", "7"])
    run_daily.main(["--days", "7", "--reset-seen"])
    # Same 3 fixture rows reprocessed -> 2 more pass -> 4 lines total (append, not
    # overwrite). Duplicate entries after a manual reset are an accepted tradeoff
    # (docs/decisions/0002), not silently hidden.
    assert len(_lines(run_daily.UNTRIAGED_PATH)) == 4


def test_dry_run_mutates_nothing():
    summary = run_daily.run(run_daily._parse_args(["--days", "7", "--dry-run"]))
    assert summary["passed"] == 2
    assert summary["new_since_last_run"] == 3       # nothing seen yet
    assert not run_daily.UNTRIAGED_PATH.exists()
    assert not run_daily.SEEN_PATH.exists()


def test_explicit_path_is_untracked_fresh_overwrite(tmp_path):
    out = tmp_path / "one_off.jsonl"
    run_daily.main(["--to-file", str(out), "--days", "7"])
    assert len(_lines(out)) == 2
    # Running again with the same explicit path overwrites, not appends, and never
    # touches the seen-ledger (it's the default target's mechanism only).
    run_daily.main(["--to-file", str(out), "--days", "7"])
    assert len(_lines(out)) == 2
    assert not run_daily.SEEN_PATH.exists()


def test_to_db_not_yet_wired():
    with pytest.raises(NotImplementedError):
        run_daily.run(run_daily._parse_args(["--to-db"]))


def test_lookback_default_comes_from_config():
    args = run_daily._parse_args([])  # no --days, no --since
    pubmed_cfg = run_daily.pubmed.load_sources_config()["pubmed"]
    since = run_daily._since_date(args, pubmed_cfg)
    assert since == run_daily.datetime.date.today() - run_daily.datetime.timedelta(
        days=pubmed_cfg["lookback_days_default"]
    )
