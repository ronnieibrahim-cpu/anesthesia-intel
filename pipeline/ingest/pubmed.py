"""PubMed ingester via NCBI E-utilities (esearch + efetch).

Implemented in M1 Step 3. Structure keeps every impure (network) call at the edges
so the two things worth testing — query assembly and XML parsing — are pure functions
exercised against fixture XML in tests/, with no live network calls (docs/02 §8).

Flow (fetch): build a search term from config/sources.yaml → esearch for PMIDs within
the date window → efetch those PMIDs as XML → parse into RawItem list. Abstracts +
metadata only (CLAUDE.md rule 2).
"""

import datetime
import os
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx
import yaml

from pipeline.ingest import RawItem

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_PATH = REPO_ROOT / "config" / "sources.yaml"

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


# ---- config -----------------------------------------------------------------

def load_sources_config(path: Path | None = None) -> dict:
    """Load config/sources.yaml (the whole file)."""
    path = path or DEFAULT_SOURCES_PATH
    return yaml.safe_load(path.read_text())


# ---- pure: query assembly ---------------------------------------------------

def _journal_token(entry) -> str:
    """A single journal allowlist entry -> a PubMed [ta] clause."""
    ta = entry["ta"] if isinstance(entry, dict) else entry
    return f'"{ta}"[ta]'


def _topic_clause(entry) -> str:
    """A single topic_queries entry -> its raw PubMed query string (parenthesized)."""
    query = entry["query"] if isinstance(entry, dict) else entry
    return f"({' '.join(query.split())})"  # collapse YAML-folded whitespace


def build_pubmed_query(pubmed_cfg: dict) -> str:
    """Assemble the esearch term: (Tier A journals) OR (standing-question topics).

    Date restriction is applied separately via esearch params, not baked in here,
    so this stays a pure, easily-tested function.
    """
    journals = pubmed_cfg.get("journal_allowlist", []) or []
    topics = pubmed_cfg.get("topic_queries", []) or []

    clauses = []
    if journals:
        clauses.append("(" + " OR ".join(_journal_token(j) for j in journals) + ")")
    for topic in topics:
        clauses.append(_topic_clause(topic))

    if not clauses:
        raise ValueError("sources.yaml pubmed section has no journals or topic_queries")
    return " OR ".join(clauses)


# ---- pure: XML parsing ------------------------------------------------------

def _text(el: ET.Element | None) -> str | None:
    """All inner text of an element (handles inline markup like <i>), or None."""
    if el is None:
        return None
    text = "".join(el.itertext()).strip()
    return text or None


def _parse_pubdate(pubdate: ET.Element | None) -> str | None:
    """PubDate element -> ISO 'YYYY-MM-DD' string, best-effort, or None.

    Handles both structured Year/Month/Day and free-text MedlineDate (e.g.
    '2026 Jun-Jul'), which is common for issue-level dates.
    """
    if pubdate is None:
        return None
    year = pubdate.findtext("Year")
    if not year:
        medline = pubdate.findtext("MedlineDate") or ""
        digits = "".join(c for c in medline[:4] if c.isdigit())
        if len(digits) != 4:
            return None
        year = digits
        month = next((_MONTHS[t.lower()[:3]] for t in medline.split()
                      if t.lower()[:3] in _MONTHS), 1)
        day = 1
    else:
        month_raw = (pubdate.findtext("Month") or "1").strip()
        month = _MONTHS.get(month_raw.lower()[:3], None)
        if month is None:
            month = int(month_raw) if month_raw.isdigit() else 1
        day_raw = (pubdate.findtext("Day") or "1").strip()
        day = int(day_raw) if day_raw.isdigit() else 1
    try:
        return datetime.date(int(year), month, day).isoformat()
    except ValueError:
        return None


def _parse_abstract(article: ET.Element) -> str | None:
    """Join AbstractText sections, prefixing structured labels (BACKGROUND: ...)."""
    parts = []
    for node in article.findall("Abstract/AbstractText"):
        text = _text(node)
        if not text:
            continue
        label = node.get("Label")
        parts.append(f"{label}: {text}" if label else text)
    return "\n".join(parts) if parts else None


def _parse_doi(pubmed_article: ET.Element, article: ET.Element) -> str | None:
    """DOI from either PubmedData/ArticleIdList or Article/ELocationID."""
    node = pubmed_article.find("PubmedData/ArticleIdList/ArticleId[@IdType='doi']")
    if node is not None and node.text:
        return node.text.strip()
    for eloc in article.findall("ELocationID[@EIdType='doi']"):
        if eloc.text:
            return eloc.text.strip()
    return None


def parse_efetch_xml(xml: bytes | str) -> list[RawItem]:
    """Parse an efetch PubmedArticleSet into RawItems. Pure; the tests' entry point."""
    root = ET.fromstring(xml)
    items: list[RawItem] = []
    for pubmed_article in root.findall("PubmedArticle"):
        medline = pubmed_article.find("MedlineCitation")
        if medline is None:
            continue
        pmid = medline.findtext("PMID")
        article = medline.find("Article")
        if pmid is None or article is None:
            continue

        pub_types = [
            pt.text for pt in article.findall("PublicationTypeList/PublicationType")
            if pt.text
        ]
        items.append(
            RawItem(
                source="pubmed",
                external_id=pmid.strip(),
                pmid=pmid.strip(),
                doi=_parse_doi(pubmed_article, article),
                title=_text(article.find("ArticleTitle")) or "(no title)",
                journal=article.findtext("Journal/Title"),
                abstract=_parse_abstract(article),
                published_on=_parse_pubdate(article.find("Journal/JournalIssue/PubDate")),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid.strip()}/",
                raw={"publication_types": pub_types},
            )
        )
    return items


# ---- impure: network + orchestration ----------------------------------------

def _common_params(pubmed_cfg: dict) -> dict:
    params = {"db": "pubmed", "tool": pubmed_cfg.get("tool", "anesthesia-intel")}
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    email = os.environ.get("NCBI_EMAIL") or os.environ.get("UNPAYWALL_EMAIL")
    if email:
        params["email"] = email
    return params


def _esearch(term: str, since: datetime.date, pubmed_cfg: dict) -> list[str]:
    base = pubmed_cfg["eutils_base"].rstrip("/")
    today = datetime.date.today()
    params = _common_params(pubmed_cfg) | {
        "term": term,
        "retmode": "json",
        "retmax": pubmed_cfg.get("retmax", 500),
        "datetype": pubmed_cfg.get("datetype", "pdat"),
        "mindate": since.strftime("%Y/%m/%d"),
        "maxdate": today.strftime("%Y/%m/%d"),
    }
    resp = httpx.get(f"{base}/esearch.fcgi", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("esearchresult", {}).get("idlist", [])


def _efetch(pmids: list[str], pubmed_cfg: dict) -> bytes:
    base = pubmed_cfg["eutils_base"].rstrip("/")
    params = _common_params(pubmed_cfg) | {"id": ",".join(pmids), "retmode": "xml"}
    resp = httpx.post(f"{base}/efetch.fcgi", data=params, timeout=60)
    resp.raise_for_status()
    return resp.content


def fetch(since: datetime.date) -> list[RawItem]:
    """Return PubMed items published/indexed since `since` per config/sources.yaml.

    Network-facing; not exercised in tests. The pure pieces it calls
    (build_pubmed_query, parse_efetch_xml) are what the tests cover.
    """
    pubmed_cfg = load_sources_config()["pubmed"]
    term = build_pubmed_query(pubmed_cfg)
    pmids = _esearch(term, since, pubmed_cfg)
    if not pmids:
        return []
    return parse_efetch_xml(_efetch(pmids, pubmed_cfg))
