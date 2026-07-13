"""Tests for normalize, pre-filter, and the compressed triage shape."""

from pathlib import Path

from llm.batching import compress
from pipeline import normalize, prefilter
from pipeline.ingest.pubmed import parse_efetch_xml

FIXTURE = Path(__file__).parent / "fixtures" / "pubmed_efetch_sample.xml"


def _rows():
    return normalize.normalize(parse_efetch_xml(FIXTURE.read_bytes()))


def test_normalize_derives_type_design_and_n():
    rows = {r["pmid"]: r for r in _rows()}
    rct = rows["40000001"]
    assert rct["item_type"] == "journal_article"
    assert rct["study_design"] == "rct"
    assert rct["sample_size"] == 1204          # parsed "1204 patients" from abstract
    assert rct["oa_url"] is None               # enrichment is Step 4
    assert rows["40000003"]["item_type"] == "letter"


def test_dedupe_by_key():
    raw = parse_efetch_xml(FIXTURE.read_bytes())
    rows = normalize.normalize(raw + raw)      # feed everything twice
    assert len(rows) == 3                      # duplicates collapse on dedupe_key


def test_prefilter_drops_letters_passes_articles():
    filters = {"hard_drops": {"item_types": ["letter", "erratum"]}}
    rows = prefilter.apply(_rows(), filters)
    marks = {r["pmid"]: r["prefilter"] for r in rows}
    assert marks["40000001"] == "passed"
    assert marks["40000002"] == "passed"
    assert marks["40000003"] == "drop:letter"


def test_prefilter_does_not_drop_when_config_empty():
    rows = prefilter.apply(_rows(), {"hard_drops": {"item_types": []}})
    assert all(r["prefilter"] == "passed" for r in rows)


def test_compress_is_tight_and_omits_nulls():
    rct = next(r for r in _rows() if r["pmid"] == "40000001")
    c = compress(rct)
    assert c["pmid"] == "40000001"
    assert c["n"] == 1204
    assert c["design"] == "rct"
    assert c["doi"].startswith("10.1056")
    assert "abstract" in c
    # A null field (oa_url) must not appear at all.
    assert "oa_url" not in c

    letter = next(r for r in _rows() if r["pmid"] == "40000003")
    c2 = compress(letter)
    assert "abstract" not in c2                # letter had no abstract -> omitted
    assert "n" not in c2                       # no sample size -> omitted
