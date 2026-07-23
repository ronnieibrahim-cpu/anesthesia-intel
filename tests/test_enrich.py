"""Tests for lawful open-access enrichment (Unpaywall + PubMed Central ELink).

No live network calls (docs/02 §8): parsing is exercised against small realistic
fixture dicts, and enrich() orchestration against monkeypatched network functions.
"""

import httpx
import pytest

from pipeline import enrich


# ---- parse_unpaywall ----------------------------------------------------------

def test_parse_unpaywall_prefers_url_for_pdf():
    payload = {
        "best_oa_location": {
            "url_for_pdf": "https://example.org/article.pdf",
            "url": "https://example.org/article",
        },
        "doi": "10.1056/nejmoa2400001",
    }
    assert enrich.parse_unpaywall(payload) == ("https://example.org/article.pdf", "unpaywall")


def test_parse_unpaywall_falls_back_to_url():
    payload = {
        "best_oa_location": {
            "url_for_pdf": None,
            "url": "https://example.org/article",
        },
    }
    assert enrich.parse_unpaywall(payload) == ("https://example.org/article", "unpaywall")


def test_parse_unpaywall_no_oa_location_returns_none():
    payload = {"best_oa_location": None, "doi": "10.1056/nejmoa2400001"}
    assert enrich.parse_unpaywall(payload) is None


def test_parse_unpaywall_missing_key_returns_none():
    assert enrich.parse_unpaywall({}) is None


# ---- parse_pmc_elink -----------------------------------------------------------

def test_parse_pmc_elink_with_linked_pmc_id():
    payload = {
        "linksets": [
            {
                "dbfrom": "pubmed",
                "ids": ["40000001"],
                "linksetdbs": [
                    {
                        "dbto": "pmc",
                        "linkname": "pubmed_pmc",
                        "links": ["11123456"],
                    }
                ],
            }
        ]
    }
    assert enrich.parse_pmc_elink(payload) == (
        "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11123456/",
        "pmc",
    )


def test_parse_pmc_elink_no_linkset_returns_none():
    payload = {"linksets": [{"dbfrom": "pubmed", "ids": ["40000002"]}]}
    assert enrich.parse_pmc_elink(payload) is None


def test_parse_pmc_elink_empty_linksets_returns_none():
    assert enrich.parse_pmc_elink({"linksets": []}) is None


# ---- enrich() orchestration -----------------------------------------------------

def test_enrich_doi_row_uses_unpaywall(monkeypatch):
    monkeypatch.setenv("UNPAYWALL_EMAIL", "founder@example.com")
    monkeypatch.setattr(
        enrich,
        "_unpaywall_get",
        lambda doi: {"best_oa_location": {"url_for_pdf": "https://oa.example/a.pdf"}},
    )
    monkeypatch.setattr(enrich, "_pmc_elink", lambda pmid: pytest.fail("should not be called"))

    rows = [{"doi": "10.1056/nejmoa2400001", "pmid": "40000001", "oa_url": None}]
    result = enrich.enrich(rows)

    assert result[0]["oa_url"] == "https://oa.example/a.pdf"
    assert result[0]["oa_source"] == "unpaywall"


def test_enrich_pmid_only_row_falls_back_to_pmc(monkeypatch):
    monkeypatch.delenv("UNPAYWALL_EMAIL", raising=False)
    monkeypatch.setattr(enrich, "_pmc_elink", lambda pmid: {
        "linksets": [{"linksetdbs": [{"links": ["11123456"]}]}]
    })

    rows = [{"doi": None, "pmid": "40000002", "oa_url": None}]
    result = enrich.enrich(rows)

    assert result[0]["oa_url"] == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11123456/"
    assert result[0]["oa_source"] == "pmc"


def test_enrich_no_oa_found_keeps_oa_url_none(monkeypatch):
    monkeypatch.setenv("UNPAYWALL_EMAIL", "founder@example.com")
    monkeypatch.setattr(enrich, "_unpaywall_get", lambda doi: {"best_oa_location": None})
    monkeypatch.setattr(enrich, "_pmc_elink", lambda pmid: {"linksets": []})

    rows = [{"doi": "10.1056/nejmoa2400001", "pmid": "40000001", "oa_url": None}]
    result = enrich.enrich(rows)

    assert result[0]["oa_url"] is None
    assert result[0]["oa_source"] is None


def test_enrich_unpaywall_error_is_isolated_and_falls_back_to_pmc(monkeypatch):
    """A raising Unpaywall call for one row must not fail the batch; PMC is still tried."""
    monkeypatch.setenv("UNPAYWALL_EMAIL", "founder@example.com")

    def _raise(doi):
        raise httpx.ConnectTimeout("simulated network failure")

    monkeypatch.setattr(enrich, "_unpaywall_get", _raise)
    monkeypatch.setattr(enrich, "_pmc_elink", lambda pmid: {
        "linksets": [{"linksetdbs": [{"links": ["11123456"]}]}]
    })

    rows = [{"doi": "10.1056/nejmoa2400001", "pmid": "40000001", "oa_url": None}]
    result = enrich.enrich(rows)

    # Unpaywall raised and was caught; the row still gets enriched via the PMC fallback.
    assert result[0]["oa_url"] == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11123456/"
    assert result[0]["oa_source"] == "pmc"


def test_enrich_unpaywall_error_with_no_pmid_leaves_row_untouched(monkeypatch):
    """Proves per-row error isolation: no pmid to fall back on, row stays as-is."""
    monkeypatch.setenv("UNPAYWALL_EMAIL", "founder@example.com")

    def _raise(doi):
        raise httpx.ConnectTimeout("simulated network failure")

    monkeypatch.setattr(enrich, "_unpaywall_get", _raise)
    monkeypatch.setattr(enrich, "_pmc_elink", lambda pmid: pytest.fail("should not be called"))

    rows = [{"doi": "10.1056/nejmoa2400001", "pmid": None, "oa_url": None}]
    result = enrich.enrich(rows)

    assert result[0]["oa_url"] is None


def test_enrich_multiple_rows_isolated(monkeypatch):
    """Multiple rows in one batch; one Unpaywall failure doesn't affect the others."""
    monkeypatch.setenv("UNPAYWALL_EMAIL", "founder@example.com")

    def _unpaywall(doi):
        if doi == "bad-doi":
            raise httpx.ConnectTimeout("simulated failure")
        return {"best_oa_location": {"url": "https://oa.example/good"}}

    monkeypatch.setattr(enrich, "_unpaywall_get", _unpaywall)
    monkeypatch.setattr(enrich, "_pmc_elink", lambda pmid: {})

    rows = [
        {"doi": "bad-doi", "pmid": None, "oa_url": None},
        {"doi": "good-doi", "pmid": None, "oa_url": None},
    ]
    result = enrich.enrich(rows)

    assert result[0]["oa_url"] is None
    assert result[1]["oa_url"] == "https://oa.example/good"
    assert result[1]["oa_source"] == "unpaywall"


def test_enrich_skips_unpaywall_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("UNPAYWALL_EMAIL", raising=False)
    monkeypatch.setattr(
        enrich, "_unpaywall_get", lambda doi: pytest.fail("should not be called")
    )
    monkeypatch.setattr(enrich, "_pmc_elink", lambda pmid: {})

    rows = [{"doi": "10.1056/nejmoa2400001", "pmid": None, "oa_url": None}]
    result = enrich.enrich(rows)

    assert result[0]["oa_url"] is None


def _http_status_error(code):
    request = httpx.Request("GET", "https://api.unpaywall.org/v2/x")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError("err", request=request, response=response)


def test_enrich_disables_unpaywall_after_systematic_config_error(monkeypatch, capsys):
    monkeypatch.setenv("UNPAYWALL_EMAIL", "invalid@example.com")
    calls = {"unpaywall": 0}

    def _unpaywall(doi):
        calls["unpaywall"] += 1
        raise _http_status_error(422)  # invalid-email style systematic failure

    # PMC still works, so a row with a PMID recovers even when Unpaywall is disabled.
    def _pmc(pmid):
        return {"linksets": [{"linksetdbs": [{"links": ["8005924"]}]}]} if pmid else {}

    monkeypatch.setattr(enrich, "_unpaywall_get", _unpaywall)
    monkeypatch.setattr(enrich, "_pmc_elink", _pmc)

    rows = [
        {"doi": "d1", "pmid": "33782057", "oa_url": None},
        {"doi": "d2", "pmid": None, "oa_url": None},
    ]
    enrich.enrich(rows)

    # Unpaywall tried once, then disabled for the rest of the batch.
    assert calls["unpaywall"] == 1
    # First row recovered via PMC fallback despite Unpaywall being down.
    assert rows[0]["oa_source"] == "pmc"
    assert "PMC8005924" in rows[0]["oa_url"]
    # Second row: Unpaywall disabled, no PMID -> nothing.
    assert rows[1]["oa_url"] is None
    assert "disabling Unpaywall" in capsys.readouterr().err
