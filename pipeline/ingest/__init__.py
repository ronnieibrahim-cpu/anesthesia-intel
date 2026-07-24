"""Source ingesters. Every source module implements the same tiny interface.

The shared contract (all of pubmed.py, fda.py, rss.py conform):

    fetch(since: datetime.date) -> list[RawItem]

- `since` is the start of the lookback window; ingesters may return overlap —
  dedupe downstream makes that safe (PRD FR-1: idempotent, re-running a day is safe).
- A failed source raises; the orchestrator (run_daily.py) catches per-source so one
  failure never fails the pipeline, and logs it for the digest-footer health line.
- Abstracts + metadata only. Never full-text scraping (CLAUDE.md rule 2).
"""

from dataclasses import dataclass, field


@dataclass
class RawItem:
    """One item exactly as a source returned it, before normalization.

    `external_id` is the source's stable identifier (PMID for PubMed, URL hash for
    feeds); normalize.py turns this into the canonical items row and dedupe key.
    """

    source: str                      # 'pubmed' | 'fda' | 'society_feed'
    external_id: str
    title: str
    url: str
    published_on: str | None = None  # ISO date string when the source provides one
    journal: str | None = None
    journal_abbrev: str | None = None  # NLM Title Abbreviation (PubMed ISOAbbreviation);
                                        # the reliable field for Tier A/B matching —
                                        # journal (full title) varies in formatting
                                        # (e.g. "Lancet (London, England)") in ways
                                        # that break fuzzy matching against config.
    abstract: str | None = None
    doi: str | None = None
    pmid: str | None = None
    raw: dict = field(default_factory=dict)  # full source payload, kept for audit
