"""Normalize RawItems into canonical item rows; compute the dedupe key.

Implemented (core) in M1 Step 3's --to-file addition, ahead of the rest of Step 4.
What exists now: RawItem -> canonical row dict, in-memory dedupe by DOI/PMID/URL,
and best-effort derivation of item_type / study_design / sample_size from PubMed
metadata so the pre-filter has something deterministic to act on.

Still Step 4: DB-backed dedupe (upsert on the unique external_id, the durable form
of idempotency); the file path uses the same dedupe key so behavior matches later.
"""

import hashlib
import re

# PubMed PublicationType strings -> our normalized item_type. Anything not matched
# is a plain 'journal_article'.
_ITEM_TYPE_MAP = {
    "Published Erratum": "erratum",
    "Retraction of Publication": "retraction",
    "Letter": "letter",
    "Editorial": "editorial",
    "News": "news",
    "Comment": "comment",
}

_DESIGN_MAP = {
    "Randomized Controlled Trial": "rct",
    "Meta-Analysis": "meta_analysis",
    "Systematic Review": "systematic_review",
    "Observational Study": "observational",
    "Multicenter Study": "multicenter",
}

# Conservative sample-size patterns. First match wins; unmatched -> None (never guess).
_N_PATTERNS = [
    re.compile(r"\bn\s*=\s*([\d,]{2,})", re.IGNORECASE),
    re.compile(r"\b([\d,]{2,})\s+patients\b", re.IGNORECASE),
    re.compile(r"\benrolled\s+([\d,]{2,})", re.IGNORECASE),
]


def _parse_sample_size(text: str | None) -> int | None:
    if not text:
        return None
    for pattern in _N_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _classify(pub_types: list[str], title: str | None, abstract: str | None):
    """Return (item_type, study_design) from PubMed publication types + text."""
    item_type = "journal_article"
    for pt in pub_types:
        if pt in _ITEM_TYPE_MAP:
            item_type = _ITEM_TYPE_MAP[pt]
            break

    study_design = None
    for pt in pub_types:
        if pt in _DESIGN_MAP:
            study_design = _DESIGN_MAP[pt]
            break
    # "retrospective" isn't a PubMed publication type; detect it from the text so the
    # rubric's retrospective-n signal (PRACTICE_PROFILE.md §6) is available downstream.
    if study_design is None:
        haystack = f"{title or ''} {abstract or ''}".lower()
        if "retrospective" in haystack:
            study_design = "retrospective"
    return item_type, study_design


def dedupe_key(row: dict) -> str:
    """DOI, else PMID, else a stable hash of the URL (PRD FR-1 precedence)."""
    if row.get("doi"):
        return f"doi:{row['doi'].lower()}"
    if row.get("pmid"):
        return f"pmid:{row['pmid']}"
    return "url:" + hashlib.sha256((row.get("url") or "").encode()).hexdigest()[:16]


def normalize(raw_items) -> list[dict]:
    """Turn RawItems into canonical rows, de-duplicated (first occurrence wins)."""
    seen: set[str] = set()
    rows: list[dict] = []
    for raw in raw_items:
        pub_types = (raw.raw or {}).get("publication_types", [])
        item_type, study_design = _classify(pub_types, raw.title, raw.abstract)
        row = {
            "source": raw.source,
            "external_id": raw.external_id,
            "doi": raw.doi,
            "pmid": raw.pmid,
            "title": raw.title,
            "journal": raw.journal,
            "journal_abbrev": raw.journal_abbrev,  # NLM ta -- reliable Tier A/B match key
            "item_type": item_type,
            "study_design": study_design,
            "sample_size": _parse_sample_size(raw.abstract),
            "published_on": raw.published_on,
            "abstract": raw.abstract,
            "url": raw.url,
            "oa_url": None,        # filled by enrich.py in Step 4; null until then
            "prefilter": "pending",
        }
        key = dedupe_key(row)
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows
