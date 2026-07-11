"""Validate triage JSON and write score rows with full version provenance.

STUB — implemented in Milestone M2 with the triage phase of /digest.

Design decided now:
- Validates the session's strict-JSON output per item: relevance_tier
  (practice_changing | worth_knowing | fyi | noise), evidence_level,
  one_line_takeaway, reasoning, topics[], confidence. Malformed output is rejected
  loudly — never silently coerced.
- Scores are APPEND-ONLY with an `is_current` flag; every row records model
  ("claude-code-session/<model>"), prompt version, and profile version, so any score
  is traceable and the backlog is re-scorable when a better model ships (docs/02 §5).
"""


def validate(score_json):
    """Return a validated score dict or raise ValueError with a plain explanation."""
    raise NotImplementedError("Implemented in M2 (triage phase).")


def write_scores(conn, scores, model, prompt_version, profile_version):
    """Append score rows, flipping is_current off on any prior score for the same item."""
    raise NotImplementedError("Implemented in M2 (triage phase).")
