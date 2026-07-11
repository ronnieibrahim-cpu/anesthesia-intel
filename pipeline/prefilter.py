"""The free, deterministic pre-filter (docs/02 §3) — protects the Pro subscription.

STUB — implemented in M1 Step 4, rules driven entirely by config/filters.yaml.

Design decided now:
- Tier A journals always pass to LLM triage (never auto-noised).
- Tier B (everything else, incl. surgical literature) passes only on a
  standing-question keyword match.
- Hard drops: configured item types, retrospective n < floor, animal/bench unless
  keyword-tied.
- Nothing is deleted: every item gets `items.prefilter` set to 'passed' or to the
  NAME of the rule that dropped it — auditable and re-scorable later.
"""


def apply(items, filters_config):
    """Mark each item row 'passed' or with the dropping rule's name. Returns the items."""
    raise NotImplementedError("Implemented in M1 Step 4 (config-driven pre-filter).")
