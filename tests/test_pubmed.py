"""Tests for the PubMed ingester's pure logic: query assembly + XML parsing.

No live network calls (docs/02 §8): parsing is exercised against a saved efetch
fixture, and query assembly against the real config/sources.yaml.
"""

from pathlib import Path

import pytest

from pipeline.ingest.pubmed import (
    build_pubmed_query,
    load_sources_config,
    parse_efetch_xml,
)

FIXTURE = Path(__file__).parent / "fixtures" / "pubmed_efetch_sample.xml"


@pytest.fixture
def parsed():
    return parse_efetch_xml(FIXTURE.read_bytes())


def test_parses_all_articles(parsed):
    assert len(parsed) == 3
    assert [i.pmid for i in parsed] == ["40000001", "40000002", "40000003"]


def test_first_article_full_fields(parsed):
    a = parsed[0]
    assert a.source == "pubmed"
    assert a.external_id == "40000001"
    assert a.doi == "10.1056/NEJMoa2400001"
    assert a.journal == "The New England journal of medicine"
    assert a.journal_abbrev == "N Engl J Med"
    assert a.title.startswith("Semaglutide and Residual Gastric Content")
    assert a.url == "https://pubmed.ncbi.nlm.nih.gov/40000001/"
    assert a.published_on == "2026-06-24"
    # Structured abstract sections are labelled and concatenated.
    assert "BACKGROUND:" in a.abstract
    assert "RESULTS:" in a.abstract
    # Publication types are preserved for normalize.py to derive item_type later.
    assert "Randomized Controlled Trial" in a.raw["publication_types"]


def test_medlinedate_and_missing_doi(parsed):
    a = parsed[1]
    assert a.doi is None
    # 'MedlineDate' of "2026 Jun-Jul" -> first month, day 1.
    assert a.published_on == "2026-06-01"
    assert a.abstract == "A single unlabelled abstract paragraph describing the association."


def test_letter_without_abstract_and_year_month_only(parsed):
    a = parsed[2]
    assert a.abstract is None
    assert a.doi == "10.1016/j.bja.2026.03.001"  # DOI from ArticleIdList
    assert a.published_on == "2026-07-01"  # Year+numeric Month, day defaults to 1
    assert a.raw["publication_types"] == ["Letter"]


def test_empty_set_returns_empty_list():
    assert parse_efetch_xml(b"<PubmedArticleSet></PubmedArticleSet>") == []


def test_build_query_from_real_config():
    pubmed_cfg = load_sources_config()["pubmed"]
    query = build_pubmed_query(pubmed_cfg)
    # Tier A journals appear as [ta] clauses.
    assert '"Anesthesiology"[ta]' in query
    assert '"N Engl J Med"[ta]' in query
    # Standing-question topics are OR'd in as parenthesized clauses.
    assert "semaglutide" in query
    assert "tranexamic" in query
    # YAML block-folding whitespace is collapsed (no doubled spaces / newlines).
    assert "\n" not in query
    assert "  " not in query


def test_build_query_raises_when_empty():
    with pytest.raises(ValueError):
        build_pubmed_query({"journal_allowlist": [], "topic_queries": []})
