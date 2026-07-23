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
5. **Item source (interim while DATABASE_URL is unresolved — ADR 0001/0002):** if the
   DB is not reachable, read the accumulating `data/untriaged.jsonl` (appended to by
   `make ingest-file` / `pipeline.run_daily --to-file`, cross-run deduped via
   pipeline/seen_store.py) instead of the `items` table. Each line is already the
   compressed, pre-filtered triage shape. When the DB is wired (Step 5), prefer the
   `items` table; the file remains an offline fallback. After a real triage pass,
   clear consumed lines from this file (M2/M3 concern — not yet automated).

## Phase 1 — Triage (M2) — TODO

- Switch to the triage model from `config/models.yaml`.
- Read items with `prefilter = 'passed'` and no current score, within the coverage window.
- Batch them via `llm/batching.py` (~25 items of compressed metadata per batch).
- Score each batch against the current `prompts/triage-vN.md` + PRACTICE_PROFILE.md.
  Output per item, strict JSON: `relevance_tier` (practice_changing | worth_knowing |
  fyi | noise), `evidence_grade` (A|B|C|D — see scale below; stored in the
  `scores.evidence_level` column), `one_line_takeaway`, `reasoning`, `topics[]`,
  `confidence`.
- Be **inclusive**: torn between noise and FYI → FYI. Nothing recovers a false noise.
- Write scores via `llm/scores.py` (append-only rows recording model + prompt version +
  profile version; model string `claude-code-session/<model>`).
- **Acceptance (M2 gate):** ≥90% practice-changing recall, ≥80% tier agreement on the
  eval set; one week's volume triaged comfortably in a single Pro session.

### Evidence grade scale (binding — every surfaced item carries one)

Derived from study design + sample size + item type (already on each item). Maps to
GRADE certainty and to the PRACTICE_PROFILE.md §7 rubric:

- **A — High:** meta-analysis/systematic review of RCTs, a large well-conducted RCT, an
  updated major society guideline (ASA/ASRA/AHA-ACC/APSF), or an FDA safety action.
- **B — Moderate:** a single or smaller RCT, or a strong prospective study with adequate n.
- **C — Low:** retrospective/observational, registry/database, or small-n studies (the
  PRACTICE_PROFILE.md §6 retrospective-n<30 floor caps these at FYI regardless of topic).
- **D — Very low:** case reports/series, mechanistic/bench, narrative reviews, unrefereed
  preprints.

State the grade honestly — an eye-catching topic with grade C/D evidence is still C/D,
and the synthesis should say so (that is exactly the journal-club caveat the founder wants).

## Phase 2 — Synthesis (M3) — TODO

- Switch to the synthesis model from `config/models.yaml` (strongest available).
- Take surviving items (practice_changing / worth_knowing / fyi).
- Enforce caps from `config/settings.yaml` (≤5 / ≤12 / ≤15) by **demoting**, never expanding.
- **Every surfaced item shows three things (binding, founder requirement):**
  1. A **2–4 sentence summary** per `prompts/synthesis-vN.md` — written against the
     founder's practice, academic-appointment voice, key caveat last. (FYI items get the
     one-line takeaway rather than the full summary; practice_changing / worth_knowing get
     the full 2–4 sentences.)
  2. Its **evidence grade** (A–D from Phase 1), shown inline next to the design/n line, so
     the strength of evidence is visible at a glance, not buried in prose.
  3. A **"Free full text" link whenever `oa_url` is present.** Maximizing this coverage is
     a goal: the daily pipeline already enriches every passed item via Unpaywall + PMC
     (`pipeline/enrich.py`), so the link is shown for every item that has a lawful
     open-access copy. Never link to or imply a paywalled/circumvented full text
     (CLAUDE.md rule 2) — abstract-only when no `oa_url` exists.
- Render `templates/digest.html.j2` (the "Free full text" links, the evidence grade,
  feedback links, and the pipeline-health footer with screened→surfaced ratio — plus, in
  the footer, how many surfaced items had a free full-text link, so OA coverage is visible).

## Token-efficient operation (how to keep the weekly session cheap)

The founder shares this session's usage with regular Claude chatting, so the digest must
be token-frugal. The design already does most of the work; the session should honor it:

1. **Read the compressed shape, not raw records.** `data/untriaged.jsonl` (or the `items`
   table projected through `llm/batching.compress()`) is already stripped to
   pmid/title/journal/date/design/n/abstract/oa_url with nulls omitted. Never re-read full
   source XML or re-fetch PubMed inside the session.
2. **Deterministic work happens outside the LLM.** Ingestion, dedupe, pre-filtering, and
   OA enrichment all run in the free daily pipeline (`make ingest-file`). The session only
   does triage + synthesis — the two things that genuinely need judgment.
3. **Triage on a mid-tier model, synthesize on the strong one** (`config/models.yaml`).
   Triage is high-volume/low-nuance; synthesis is low-volume/high-nuance. Only the ~20–40
   surviving items get the expensive model.
4. **Keep the corpus small before the session.** The pre-filter (`config/filters.yaml`)
   is the lever: a corpus in the ~100–300/week target range triages in one comfortable
   pass. If a session ever strains limits, tighten filters — not the model, not the caps.

## Phase 3 — Preview → confirm → send (M3) — TODO

- Show the rendered digest in the session for review; accept conversational edits
  ("demote item 4", "expand item 2") and re-render.
- On the founder's explicit "send": deliver via Resend, store the digest copy and its
  item list in the `digests` / `digest_items` tables.
- With `--dry-run`: stop after preview; state plainly that nothing was sent.
