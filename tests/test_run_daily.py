"""Tests for run_daily's --to-file path. No network: pubmed.fetch is monkeypatched."""

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


def test_to_file_writes_jsonl(tmp_path):
    out = tmp_path / "week.jsonl"
    run_daily.main(["--to-file", str(out), "--days", "7"])
    lines = out.read_text().strip().splitlines()
    # 3 fixture items; the letter is dropped by the default filters.yaml -> 2 pass.
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["pmid"] == "40000001"
    assert first["n"] == 1204
    assert "oa_url" not in first               # null field omitted


def test_dry_run_writes_nothing(tmp_path):
    out = tmp_path / "week.jsonl"
    summary = run_daily.run(run_daily._parse_args(["--to-file", str(out), "--dry-run"]))
    assert not out.exists()
    assert summary["passed"] == 2
    assert summary["dropped"] == 1


def test_file_is_default_target_without_db(tmp_path, monkeypatch):
    # No --to-file, no --to-db: file is the default target (DB not required).
    monkeypatch.setattr(run_daily, "_default_file_path", lambda: tmp_path / "wk.jsonl")
    summary = run_daily.run(run_daily._parse_args([]))
    assert summary["wrote_file"] == str(tmp_path / "wk.jsonl")
    assert (tmp_path / "wk.jsonl").exists()


def test_to_db_not_yet_wired(tmp_path):
    with pytest.raises(NotImplementedError):
        run_daily.run(run_daily._parse_args(["--to-db"]))
