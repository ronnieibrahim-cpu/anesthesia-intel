"""Lawful open-access enrichment: Unpaywall (by DOI) + PubMed Central ELink (by PMID).

Structure mirrors pipeline/ingest/pubmed.py: pure functions parse an API response
payload into a result, impure functions do the network call at the edges, and
`enrich()` orchestrates. That keeps the parsing logic (what the tests cover) free
of any live network dependency (docs/02 §8).

Precedence per row: Unpaywall first (by DOI), then PubMed Central ELink as a
fallback (by PMID) only if Unpaywall found nothing. If a legal OA copy exists,
store its link in row["oa_url"] and the provenance in row["oa_source"]
('unpaywall' | 'pmc'); the digest shows it as "Free full text".

This is the ONLY full-text mechanism in the project. No paywall circumvention of
any kind, ever (CLAUDE.md rule 2) — Unpaywall and PMC only, abstracts otherwise.
"""

import os
import sys

import httpx

DEFAULT_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


# ---- pure: response parsing --------------------------------------------------

def parse_unpaywall(payload: dict) -> tuple[str, str] | None:
    """Unpaywall /v2/{doi} JSON -> (oa_url, "unpaywall"), or None if no OA location."""
    location = payload.get("best_oa_location")
    if not location:
        return None
    url = location.get("url_for_pdf") or location.get("url")
    if not url:
        return None
    return url, "unpaywall"


def parse_pmc_elink(payload: dict) -> tuple[str, str] | None:
    """NCBI ELink pubmed->pmc JSON -> (pmc_url, "pmc"), or None if nothing linked."""
    linksets = payload.get("linksets") or []
    for linkset in linksets:
        for linksetdb in linkset.get("linksetdbs") or []:
            for pmcid in linksetdb.get("links") or []:
                return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/", "pmc"
    return None


# ---- impure: network calls ---------------------------------------------------

def _unpaywall_get(doi: str) -> dict:
    email = os.environ["UNPAYWALL_EMAIL"]
    resp = httpx.get(
        f"https://api.unpaywall.org/v2/{doi}", params={"email": email}, timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def _pmc_elink(pmid: str, eutils_base: str = DEFAULT_EUTILS_BASE) -> dict:
    base = eutils_base.rstrip("/")
    params = {"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json"}
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    resp = httpx.get(f"{base}/elink.fcgi", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---- orchestration ------------------------------------------------------------

# Unpaywall status codes that indicate a SYSTEMATIC config problem (bad/invalid
# contact email, auth) rather than a per-item miss. These fail identically for every
# row, so on the first one we warn loudly and stop trying Unpaywall for the batch —
# otherwise a misconfigured UNPAYWALL_EMAIL silently zeroes out OA coverage.
_UNPAYWALL_CONFIG_ERRORS = {401, 403, 422}


def enrich(rows: list[dict]) -> list[dict]:
    """Attach oa_url/oa_source to rows where a lawful open-access copy exists.

    Mutates rows in place and returns them. Only calls Unpaywall for rows with a
    DOI, and only calls PMC for rows with a PMID that still lack an oa_url after
    Unpaywall. A per-item network/HTTP error is caught and skipped (oa_url stays
    None) so one bad lookup never fails the whole batch. A *systematic* Unpaywall
    config error (bad email/auth) is warned about once and disables Unpaywall for
    the rest of the batch, since it would fail identically for every row.
    """
    unpaywall_enabled = bool(os.environ.get("UNPAYWALL_EMAIL"))

    for row in rows:
        row.setdefault("oa_source", None)

        if unpaywall_enabled and row.get("doi"):
            try:
                result = parse_unpaywall(_unpaywall_get(row["doi"]))
            except httpx.HTTPStatusError as e:
                result = None
                if e.response.status_code in _UNPAYWALL_CONFIG_ERRORS:
                    print(
                        f"[enrich] Unpaywall returned {e.response.status_code} "
                        "(likely an invalid UNPAYWALL_EMAIL) — disabling Unpaywall for "
                        "this run; items will fall back to PMC only.",
                        file=sys.stderr,
                    )
                    unpaywall_enabled = False
            except httpx.HTTPError:
                result = None
            if result:
                row["oa_url"], row["oa_source"] = result

        if not row.get("oa_url") and row.get("pmid"):
            try:
                result = parse_pmc_elink(_pmc_elink(row["pmid"]))
            except httpx.HTTPError:
                result = None
            if result:
                row["oa_url"], row["oa_source"] = result

    return rows
