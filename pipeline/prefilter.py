"""The free, deterministic pre-filter (docs/02 §3) — protects the Pro subscription.

Rules are config-driven (config/filters.yaml). Nothing is deleted: each row's
`prefilter` becomes 'passed' or 'drop:<rule>' — auditable and re-scorable later.

Two stages, in order:
1. Hard drops by item type (errata/retractions/letters/editorials/news/comments).
   Deliberately NOT a hard drop here: retrospective studies below the n-floor — per
   PRACTICE_PROFILE.md §6 that is a *demotion to FYI at triage*, not a silent drop
   (missing a signal is worse than surfacing noise, PRD §9). Carried through as a
   triage signal (items.sample_size), not enforced here.
2. Tier A/B gate: a Tier A journal (journal_abbrev in config's tier_a_journals) always
   passes. A Tier B item (everything else) passes only if its title+abstract matches
   at least one config/filters.yaml tier_b_keyword — word-boundary, case-insensitive
   (docs/02 §3; every Tier B item already matched a broad PubMed topic query at fetch
   time (config/sources.yaml); this is the precision pass on top of that recall net).
"""

import re


def _keyword_pattern(keywords: list[str]) -> re.Pattern | None:
    if not keywords:
        return None
    alternation = "|".join(re.escape(k) for k in keywords)
    return re.compile(rf"\b(?:{alternation})\b", re.IGNORECASE)


def apply(items: list[dict], filters_config: dict) -> list[dict]:
    """Mark each row 'passed' or 'drop:<rule>'. Returns the same list."""
    cfg = filters_config or {}
    hard = cfg.get("hard_drops", {}) or {}
    drop_item_types = set(hard.get("item_types", []) or [])
    tier_a = set(cfg.get("tier_a_journals", []) or [])
    keyword_pattern = _keyword_pattern(cfg.get("tier_b_keywords", []) or [])

    for row in items:
        item_type = row.get("item_type")
        if item_type in drop_item_types:
            row["prefilter"] = f"drop:{item_type}"
            continue

        if row.get("journal_abbrev") in tier_a:
            row["prefilter"] = "passed"
            continue

        # Tier B: require a standing-question keyword match.
        haystack = f"{row.get('title') or ''} {row.get('abstract') or ''}"
        if keyword_pattern and keyword_pattern.search(haystack):
            row["prefilter"] = "passed"
        else:
            row["prefilter"] = "drop:tier_b_no_keyword_match"
    return items
