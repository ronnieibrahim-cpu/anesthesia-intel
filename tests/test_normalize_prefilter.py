"""Tests for normalize, the two-stage pre-filter, and the compressed triage shape."""

from pathlib import Path

from llm.batching import compress
from pipeline import normalize, prefilter
from pipeline.ingest.pubmed import parse_efetch_xml

FIXTURE = Path(__file__).parent / "fixtures" / "pubmed_efetch_sample.xml"


def _rows():
    return normalize.normalize(parse_efetch_xml(FIXTURE.read_bytes()))


def _row(item_type="journal_article", journal_abbrev="Ann Surg", title="", abstract=""):
    return {"item_type": item_type, "journal_abbrev": journal_abbrev,
            "title": title, "abstract": abstract}


def test_normalize_derives_type_design_and_n():
    rows = {r["pmid"]: r for r in _rows()}
    rct = rows["40000001"]
    assert rct["item_type"] == "journal_article"
    assert rct["study_design"] == "rct"
    assert rct["sample_size"] == 1204          # parsed "1204 patients" from abstract
    assert rct["oa_url"] is None               # enrichment is Step 4
    assert rct["journal_abbrev"] == "N Engl J Med"
    assert rows["40000003"]["item_type"] == "letter"


def test_dedupe_by_key():
    raw = parse_efetch_xml(FIXTURE.read_bytes())
    rows = normalize.normalize(raw + raw)      # feed everything twice
    assert len(rows) == 3                      # duplicates collapse on dedupe_key


def test_prefilter_drops_letters_passes_tier_a_articles():
    # All 3 fixture journals (N Engl J Med, Anaesthesia, Br J Anaesth) are Tier A.
    filters = {
        "hard_drops": {"item_types": ["letter", "erratum"]},
        "tier_a_journals": ["N Engl J Med", "Anaesthesia", "Br J Anaesth"],
    }
    rows = prefilter.apply(_rows(), filters)
    marks = {r["pmid"]: r["prefilter"] for r in rows}
    assert marks["40000001"] == "passed"           # Tier A (NEJM)
    assert marks["40000002"] == "passed"           # Tier A (Anaesthesia)
    assert marks["40000003"] == "drop:letter"       # hard-drop wins over Tier A


def test_hard_drop_short_circuits_before_tier_check():
    row = _row(item_type="letter", journal_abbrev="Anesthesiology")  # Tier A journal
    filters = {"hard_drops": {"item_types": ["letter"]}, "tier_a_journals": ["Anesthesiology"]}
    result = prefilter.apply([row], filters)
    assert result[0]["prefilter"] == "drop:letter"


def test_tier_a_journal_passes_regardless_of_keywords():
    row = _row(journal_abbrev="Anesthesiology", title="Nothing keyword-related here")
    filters = {"tier_a_journals": ["Anesthesiology"], "tier_b_keywords": ["semaglutide"]}
    assert prefilter.apply([row], filters)[0]["prefilter"] == "passed"


def test_tier_b_journal_passes_on_keyword_match():
    row = _row(title="Semaglutide and aspiration risk before elective surgery")
    filters = {"tier_a_journals": ["Anesthesiology"], "tier_b_keywords": ["semaglutide"]}
    assert prefilter.apply([row], filters)[0]["prefilter"] == "passed"


def test_tier_b_journal_drops_without_keyword_match():
    row = _row(title="An unrelated surgical outcomes study")
    filters = {"tier_a_journals": ["Anesthesiology"], "tier_b_keywords": ["semaglutide"]}
    assert prefilter.apply([row], filters)[0]["prefilter"] == "drop:tier_b_no_keyword_match"


def test_keyword_match_is_word_boundary_not_substring():
    # "mina" (MINA = myocardial injury after noncardiac surgery) must not match
    # inside an unrelated word like "elimination".
    filters = {"tier_a_journals": [], "tier_b_keywords": ["mina"]}
    unrelated = _row(title="Renal elimination pharmacokinetics after surgery")
    assert prefilter.apply([unrelated], filters)[0]["prefilter"] == "drop:tier_b_no_keyword_match"

    on_topic = _row(title="MINA: myocardial injury after noncardiac surgery, a review")
    assert prefilter.apply([on_topic], filters)[0]["prefilter"] == "passed"


def test_empty_config_is_a_safe_default_drops_tier_b():
    row = _row(title="anything at all")
    assert prefilter.apply([row], {})[0]["prefilter"] == "drop:tier_b_no_keyword_match"


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
