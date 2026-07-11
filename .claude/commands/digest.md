---
description: Weekly digest — triage the week's pre-filtered items against PRACTICE_PROFILE.md, synthesize, preview, and (on explicit confirmation) send via Resend.
---

# /digest — the Monday session

**Status: SKELETON.** Phase 1 is implemented in Milestone M2; Phases 2–3 in M3.
This file defines the structure now so later sessions fill in slots instead of
re-deciding architecture. Arguments: `$ARGUMENTS` (supports `--dry-run`).

## Preamble (always, before any phase)

1. Read `CLAUDE.md` (hard rules), `PRACTICE_PROFILE.md` (the rubric — apply literally),
   `config/models.yaml` (which model to use per phase), `config/settings.yaml` (tier caps).
2. Parse `$ARGUMENTS`. If it contains `--dry-run`: run everything up to and including the
   preview, but never send email and clearly say so at the end.
3. Default behavior is **preview-then-confirm** (CLAUDE.md rule 6): email is sent only
   after the founder explicitly replies "send".
4. Coverage window: everything since the **last sent digest** (query the `digests` table),
   NOT "the last 7 days". A skipped week simply means the next digest covers two weeks;
   the caps ensure only the best items survive (docs/07 promises this behavior).

## Phase 1 — Triage (M2) — TODO

- Switch to the triage model from `config/models.yaml`.
- Read items with `prefilter = 'passed'` and no current score, within the coverage window.
- Batch them via `llm/batching.py` (~25 items of compressed metadata per batch).
- Score each batch against the current `prompts/triage-vN.md` + PRACTICE_PROFILE.md.
  Output per item, strict JSON: `relevance_tier` (practice_changing | worth_knowing |
  fyi | noise), `evidence_level`, `one_line_takeaway`, `reasoning`, `topics[]`, `confidence`.
- Be **inclusive**: torn between noise and FYI → FYI. Nothing recovers a false noise.
- Write scores via `llm/scores.py` (append-only rows recording model + prompt version +
  profile version; model string `claude-code-session/<model>`).
- **Acceptance (M2 gate):** ≥90% practice-changing recall, ≥80% tier agreement on the
  eval set; one week's volume triaged comfortably in a single Pro session.

## Phase 2 — Synthesis (M3) — TODO

- Switch to the synthesis model from `config/models.yaml` (strongest available).
- Take surviving items (practice_changing / worth_knowing / fyi).
- Enforce caps from `config/settings.yaml` (≤5 / ≤12 / ≤15) by **demoting**, never expanding.
- For each surfaced item: 2–4 sentence synthesis per `prompts/synthesis-vN.md` — written
  against the founder's practice, academic-appointment voice, key caveat last.
- Render `templates/digest.html.j2` (include "Free full text" links where `oa_url` exists,
  feedback links, and the pipeline-health footer with screened→surfaced ratio).

## Phase 3 — Preview → confirm → send (M3) — TODO

- Show the rendered digest in the session for review; accept conversational edits
  ("demote item 4", "expand item 2") and re-render.
- On the founder's explicit "send": deliver via Resend, store the digest copy and its
  item list in the `digests` / `digest_items` tables.
- With `--dry-run`: stop after preview; state plainly that nothing was sent.
