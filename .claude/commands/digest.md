---
description: Weekly digest — triage the week's pre-filtered items against PRACTICE_PROFILE.md, synthesize, preview, and (on explicit confirmation) send via Resend.
---

# /digest — the Monday session

**Status: BUILT through preview-to-file.** Phase 1 (triage) is implemented (M2); Phase 2
(synthesis + deterministic render) and Phase 3 *preview-to-file* are implemented (M3); the
Phase 3 *email send* (Resend) is deferred by founder choice. This file is the authoritative
behavioral spec. Arguments: `$ARGUMENTS` (supports `--dry-run`).

**Implementers:** read `docs/08_HANDOFF_DIGEST.md` first (milestone plan, what's built vs
stub, Sonnet-subagent strategy). The output design bar is `templates/digest.sample.html`.

## The single-command flow (what to run, in order)

A fresh session starts empty (the repo is re-cloned; `data/` is gitignored). This one
command sheet fetches, triages, synthesizes, and renders — the founder types only `/digest`.

0. **Ensure the corpus** — if `data/untriaged.jsonl` is missing (fresh session) or the
   founder wants a fresh pull, run `make ingest-file`. It fetches the last ~21 days from
   PubMed and enriches OA links — deterministic, no DB, no API key, ~a few hundred items.
1. **Triage** (Phase 1) → write `data/scores.jsonl`.
2. **Synthesize** (Phase 2) the surviving items → write `data/synthesis.jsonl`.
3. **Render** → `python -m pipeline.digest_render --screened <N> [--brief "…"]` writes
   `data/digest-<today>.html`. Show it to the founder (Phase 3).

The steps below are the authoritative detail for each phase.

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

## Phase 1 — Triage (M2) — BUILT

- Switch to the triage model from `config/models.yaml`.
- Read the pre-filtered items from `data/untriaged.jsonl` (the interim source; each line is
  already the compressed, `prefilter='passed'` triage shape), within the coverage window.
- Batch them via `llm/batching.make_batches()` (~25 items per batch, size from
  `config/settings.yaml` budget.triage_batch_size).
- Score each batch against `prompts/triage-v1.md` + PRACTICE_PROFILE.md. Output per item,
  strict JSON: `relevance_tier` (practice_changing | worth_knowing | fyi | noise),
  `evidence_level` (A|B|C|D — see scale below), `one_line_takeaway`, `reasoning`,
  `topics[]`, `confidence`.
- Be **inclusive**: torn between noise and FYI → FYI. Nothing recovers a false noise.
- Validate + write with `llm/scores.py`: `validate()` each item (rejects malformed JSON
  loudly), then `write_scores_to_file("data/scores.jsonl", …, model, "triage-v1",
  <profile_version>)` (append-only; latest-per-pmid wins). When the DB is reachable,
  `write_scores(conn, …)` writes the `scores` table instead.
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

## Phase 2 — Synthesis (M3) — BUILT (preview-to-file; email is Phase 3, deferred)

- Switch to the synthesis model from `config/models.yaml` (strongest available).
- Take surviving items (practice_changing / worth_knowing / fyi — never noise).
- Score each with `prompts/synthesis-v1.md`: it returns, per item (strict JSON keyed by
  pmid), a **four-part brief** — `summary`, `practice_impact` (the founder's own practice),
  `field_impact` (anesthesia broadly), `future_considerations` (caveat last) — plus two
  short display descriptors (`design_line`, `grade_label`). Write the array to a JSONL the
  renderer reads (e.g. `data/synthesis.jsonl`, latest-per-pmid winning).
- **Every surfaced item shows (binding, founder requirement):** the four-part write-up
  above, its **evidence grade A–D** (from Phase 1) as an inline chip, and a **"Free full
  text" link whenever `oa_url` is present** (abstract-only otherwise — never a paywalled or
  circumvented link, CLAUDE.md rule 2). FYI depth follows `config/settings.yaml`
  `digest.fyi_writeup`: `full` gives FYI the same four-part brief (the founder's V1 choice),
  `one_line` collapses FYI to its triage `one_line_takeaway`.
- **Caps and rendering are deterministic — not the model's job.** `pipeline/digest_render.py`
  merges item metadata + triage score + synthesis prose by pmid, enforces the
  `config/settings.yaml` caps (≤5 / ≤12 / ≤15) by **demoting** the weakest overflow (never
  expanding), and renders `templates/digest.html.j2` — the four-part blocks, grade chips,
  "Free full text" links, and the pipeline-health footer (screened→surfaced ratio + how many
  surfaced items had a free full-text link). Feedback links arrive in M4.
- The `week_in_brief` masthead blurb is short synthesis prose the session supplies to the
  renderer; the rest of the digest is assembled deterministically.

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

## Phase 3 — Preview → confirm → send

**Preview-to-file — BUILT.** Run `python -m pipeline.digest_render --screened <N>`
(optionally `--brief "…"` for the masthead blurb); it reads `data/untriaged.jsonl` +
`data/scores.jsonl` + `data/synthesis.jsonl` and writes `data/digest-<today>.html`
(gitignored) for the founder to open and read. Accept conversational edits in-session
("demote item 4", "drop item 2") by adjusting the synthesis/score inputs and re-rendering —
the render step is free and deterministic, so iterate freely before any send.

**Email send — DEFERRED (founder chose preview-to-file first).** When the founder wants
real delivery: add a `pipeline/send.py` (Resend API) with `--dry-run` support and the
preview-then-confirm default (CLAUDE.md rule 6) — email is sent only after the founder
explicitly replies "send". Needs `RESEND_API_KEY` and a confirmed recipient. Until then,
`--dry-run` behavior is the whole command: render, preview, send nothing, say so plainly.
On a real send (later), store the digest copy and item list in `digests` / `digest_items`
once the DB is reachable; until then the on-disk HTML is the record.
