<!--
CHANGELOG (docs/04 §3: every prompt opens with this header)
version: 1 (placeholder — body written in Milestone M2)
date: 2026-07-11
changed: file created as scaffold; no prompt content yet
eval delta: n/a (no eval run against a placeholder)
rule: NEVER edit a released version in place — copy to triage-v2.md (CLAUDE.md rule 4).
      Any change requires `make eval`; report goes in the PR (CLAUDE.md rule 5).
-->

# Triage prompt v1 — TODO (M2)

Scores batches of pre-filtered items against PRACTICE_PROFILE.md into strict JSON tiers:
`relevance_tier` (practice_changing | worth_knowing | fyi | noise), `evidence_level`,
`one_line_takeaway`, `reasoning`, `topics[]`, `confidence`.

Design constraints already decided (docs/02 §5):
- Inclusive at the margins: torn between noise and FYI → FYI. Nothing recovers a false noise.
- The rubric lives in PRACTICE_PROFILE.md §7, injected verbatim — not restated here.
- Tier A journal items are never auto-noised.
