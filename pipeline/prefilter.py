"""The free, deterministic pre-filter (docs/02 §3) — protects the Pro subscription.

Implemented (core) in M1 Step 3's --to-file addition, ahead of the rest of Step 4.
Rules are config-driven (config/filters.yaml). Nothing is deleted: each row's
`prefilter` becomes 'passed' or 'drop:<rule>' — auditable and re-scorable later.

What exists now: hard-drop by item type (errata/retractions/letters/editorials/news).
Deliberately NOT dropped here: retrospective studies below the n-floor — per
PRACTICE_PROFILE.md §6 that is a *demotion to FYI at triage*, not a silent drop, and
this project treats missing a signal as worse than surfacing noise (PRD §9). The
`retrospective_n_below` value is carried through as a triage signal, not a drop rule.

Still Step 4: Tier B standing-question keyword matching (items already arrive via the
Tier A allowlist or a topic query, so the interim set is legitimately pre-filtered;
keyword re-matching is a precision refinement, not a recall safeguard).
"""


def apply(items: list[dict], filters_config: dict) -> list[dict]:
    """Mark each row 'passed' or 'drop:<item_type>'. Returns the same list."""
    hard = (filters_config or {}).get("hard_drops", {}) or {}
    drop_item_types = set(hard.get("item_types", []) or [])
    for row in items:
        item_type = row.get("item_type")
        if item_type in drop_item_types:
            row["prefilter"] = f"drop:{item_type}"
        else:
            row["prefilter"] = "passed"
    return items
