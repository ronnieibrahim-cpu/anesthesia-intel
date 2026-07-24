STATE OF THE WORLD log

## 2026-07-11 — M1 Step 1: repository scaffold
The full repo skeleton exists per docs/04 (plus config/filters.yaml, which docs/02 §3
requires but the docs/04 tree omitted): all pipeline/llm/evalset modules are documented
stubs stating which step implements them, /digest is a phase-by-phase skeleton in
.claude/commands/digest.md, and `make doctor`/`make test` are real (doctor fails if an
ANTHROPIC_API_KEY is ever set). The weekly.yml/eval.yml workflows from the docs/04 tree
were deliberately not created — docs/02 §7 says the weekly step is the interactive
/digest session and eval runs in-session; daily.yml exists with its cron commented out
until Step 5. Next: Step 2 — dbmate migrations for the docs/02 §4 schema, run against
the founder's Supabase project.

## 2026-07-11 — M1 Step 2: database schema (dbmate migrations)
7 numbered dbmate migrations in db/migrations/ create sources, items, digests, scores,
digest_items, feedback, eval_labels — reconstructed from the PRD (FR-1 through FR-6) and
docs/02 §5, since docs/02 §4 only documents three ALTER-TABLE additions (oa_url,
oa_source, prefilter) against a "v1" schema that has no standalone doc in this repo;
those three columns are folded into `items` from the start. Notable choices: items
dedupes on UNIQUE(source_id, external_id) so re-running any day is idempotent by
construction; scores is append-only with a partial UNIQUE index enforcing exactly one
is_current row per item; sources carries last_success_at/last_error for the digest's
pipeline-health footer; nothing is ever deleted, only marked (items.prefilter). Verified
by applying, rolling back, and re-applying all 7 migrations against a local Postgres 16
instance (inserted one realistic row per table; confirmed the one-current-score
constraint rejects a duplicate). `make migrate` is now real: it installs dbmate via
`go install` if missing (tested against a clean PATH) and applies db/migrations to
$DATABASE_URL. db/schema.sql is the committed, verified snapshot. Founder walked through
running `make migrate` against Supabase from a Claude Code cloud session. Next: Step 3 —
pipeline/ingest/pubmed.py against config/sources.yaml, with fixture-based pytest tests.

## 2026-07-13 — M1 Step 2 addendum: schema applied out-of-band + open DATABASE_URL issue
The schema was applied to the founder's Supabase project MANUALLY via the Supabase SQL
Editor (all 7 tables live, confirmed in the Table Editor), NOT via `make migrate`. Reason:
`DATABASE_URL` is not resolving inside Claude Code cloud sessions yet, so dbmate can't
reach the DB from the sandbox. After a manual apply, dbmate's bookkeeping table must be
seeded so a future `make migrate` recognizes the schema (INSERT the 7 version rows into
schema_migrations — SQL handed to the founder to paste).
OPEN ISSUE (deferred, does not block fixture-based work): DATABASE_URL unresolved in the
sandbox. Two things to check when revisited: (1) the var must be set in the Claude Code
cloud environment (not GitHub Actions secrets) and a NEW session started; (2) network
allowlist — the working Supabase connection is the Transaction pooler host, which is
`*.pooler.supabase.com` (port 6543), a DIFFERENT domain from `*.supabase.co`; the direct
`db.<ref>.supabase.co:5432` host is IPv6-only on the free tier and won't connect from an
IPv4 sandbox. Add `*.pooler.supabase.com` to the sandbox's allowed domains when wiring
this up (docs/07 Part 3 currently lists only *.supabase.co / *.pooler.supabase.com — keep
the pooler entry).

## 2026-07-13 — M1 Step 3: PubMed ingester
pipeline/ingest/pubmed.py implements the shared fetch(since)->list[RawItem] interface via
NCBI E-utilities (esearch+efetch). config/sources.yaml now carries the 19 MEDLINE-indexed
Tier A journals from PRACTICE_PROFILE.md §8 (APSF Newsletter deliberately excluded — not
MEDLINE-indexed, will come via society RSS in Step 4) plus 11 standing-question/controversy
topic queries from §4–5 (GLP-1 pinned first). Design: network calls (_esearch/_efetch) live
at the edges; the two things worth testing — build_pubmed_query and parse_efetch_xml — are
pure functions. Parser uses stdlib xml.etree (no new dependency); it extracts pmid/doi/
title/journal/abstract (structured labels concatenated)/published_on and stashes PubMed
publication_types in raw for normalize.py (Step 4) to derive item_type/study_design.
7 fixture-based tests, no live network in the suite (docs/02 §8). Verified additionally
by a manual live run (NOT in tests): the assembled query returned 399 PMIDs for the last
7 days (within docs/02's expected 300–800/week) and 3 real records parsed cleanly through
efetch. Next: Step 4 — fda.py, rss.py, normalize.py + dedupe, config-driven pre-filter,
Unpaywall/PMC enrichment.

## 2026-07-13 — M1 Step 3 addition: DB-optional --to-file ingestion (ADR 0001)
run_daily.py gained a --to-file target writing normalized, pre-filtered, compressed items
to data/week-YYYY-MM-DD.jsonl so /digest can run before DATABASE_URL is resolved; the DB
write (--to-db) is separate and NOT required (raises until Step 5). This front-loaded the
core of normalize.py (RawItem->canonical row, in-memory dedupe by DOI/PMID/URL, item_type/
study_design/sample_size derivation) and prefilter.py (config-driven hard-drops from
config/filters.yaml, now populated) — both additive to Step 4, not throwaway. compress()
lives in llm/batching.py and defines the tight triage shape (nulls omitted for tokens).
Deliberately NOT dropped at prefilter: retrospective n<floor — that's a triage demotion to
FYI (profile §6), not a silent drop (recall > precision). oa_url present-but-null until
enrichment (Step 4). data/ is git-ignored. Verified: 19 fixture-based tests pass (no
network in suite), and a live end-to-end run produced 324 items (fetched 410 → deduped 406
→ dropped 82) into a real JSONL file. Decision recorded in docs/decisions/0001. Interim
source noted in .claude/commands/digest.md; `make ingest-file` added. Next unchanged:
Step 4 — fda.py, rss.py, complete enrichment + Tier B keyword pre-filter + DB-backed dedupe.

## 2026-07-13 — Wide net + seen-ledger, edat rejected (ADR 0002)
Founder pushed back on the "indexing lag" framing of the audit and proposed switching
PubMed's datetype from pdat to edat to fix low weekly counts for Anesthesiology/RAPM/CCM.
Tested directly (not just theorized): edat performed the SAME OR WORSE for every flagged
journal (Anesthesiology 1->0, RAPM 18->3 over 7 days; 410 vs 401 in aggregate) — rejected
on evidence. Root cause is real per-journal weekly variance, not a query bug (confirmed
by widening the test window: Anesthesiology 90d avg ~15/week but 1 this week).
Fix instead: config/sources.yaml pubmed.lookback_days_default 3->21 (widened per
founder's explicit "cast a wider net" instruction) and retmax 500->3000 (verified 21-day
true count is 1828 — old retmax would have silently truncated). New pipeline/seen_store.py
adds a persistent, gitignored ledger (data/.seen_ids.json) so the wide, overlapping window
doesn't reprocess the same item every run. run_daily.py's default --to-file target changed
from a per-run OVERWRITE of a dated snapshot (data/week-YYYY-MM-DD.jsonl) to an APPEND to
a single accumulating backlog, data/untriaged.jsonl — explicit --to-file PATH still does
an untracked one-off overwrite (used for the audit itself) and is unaffected. Added
--reset-seen as an escape hatch. Verified live: first run against the real 21-day window
processed 1814 new items (378 dropped, 1436 surfaced — a one-time backlog catch-up, well
above the ~100-300/week steady-state target; will shrink to small daily deltas once this
is running continuously and once Step 4's Tier B keyword pre-filter tightens volume);
immediate second run appended exactly 0. 27 tests pass (7 new for seen_store +
run_daily rewrites), no network in suite. .claude/commands/digest.md, README, and
Makefile updated to reference untriaged.jsonl. Full rationale in docs/decisions/0002.
Next unchanged: Step 4 — fda.py, rss.py, enrichment, Tier B keyword pre-filter, DB dedupe.

## 2026-07-13 — M1 Step 3 addition: Tier-B keyword pre-filter (ADR 0003)
Pulled the Tier-B keyword gate forward from Step 4 after the founder's audit showed 79%
of the 21-day corpus passing (far above docs/02's ~100-300/week). Added journal_abbrev
(PubMed ISOAbbreviation) through RawItem->normalize->row so Tier A/B classification uses
the stable NLM abbreviation, not the drift-prone full title. prefilter.py is now two-stage:
hard-drops, then Tier A always-pass / Tier B keyword-match (word-boundary regex, not
substring). Keywords in config/filters.yaml drawn 1:1 from PRACTICE_PROFILE.md §4-5.
Impact: 1436->817 passed (79%->62%). 32 tests pass, lint clean. OPEN (founder decision,
not made unilaterally): 527 of 817 passed are general medical journals (JAMA 186/21d)
whose content is mostly non-anesthesia, but profile §8 says Tier A never auto-noises —
tightening further contradicts §8 and needs a profile edit. Diagnosis + options in ADR
0003. Also confirmed the ADR 0002 window mechanism on evidence: monthly journals
(Anesthesiology, CCM) publish in single-day batches at month-start — a 7-day window's
count is decided by whether it straddles a batch day, not by "quiet weeks"; 21 days
absorbs this but ~32 days would be more robust if a run lands late in a month (still
open). Next: enrichment (oa_url full-text links) + evidence grading in the digest spec.

## 2026-07-13 — M1 Step 3 addition: OA full-text enrichment + digest requirements
Implemented pipeline/enrich.py (Unpaywall by DOI, then PubMed Central ELink by PMID as
fallback), mirroring pubmed.py's pure-parse / network-at-edges split; wired into
run_daily.run() to enrich only the passed set before compress(), skipped on --dry-run.
Per-row error isolation, PLUS a systematic-config-error guard: a Unpaywall 401/403/422
(e.g. an invalid UNPAYWALL_EMAIL) warns once and disables Unpaywall for the batch so it
doesn't silently zero out OA coverage — items still fall back to PMC. Verified live: PMC
path resolves real articles (PMID 33782057 -> PMC8005924); Unpaywall connectivity
confirmed (needs a real email; test@example.com 422s, which now trips the guard and PMC
fallback still recovers the item). 47 tests pass (14 enrich + 1 guard, all network-free).
Founder requirements baked into .claude/commands/digest.md: every surfaced item shows a
2-4 sentence summary, an evidence grade (A-D scale defined: A=RCT-meta/guideline/FDA ...
D=case report/bench/preprint, stored in scores.evidence_level), and a "Free full text"
link whenever oa_url exists (abstract-only otherwise; never paywalled/circumvented per
CLAUDE.md rule 2); footer reports OA coverage. Added a token-efficient-operation section
to the digest spec. Next: Step 4 remainder — fda.py, rss.py, DB-backed dedupe (Step 5);
the general-journal Tier-A tiering decision (ADR 0003) remains open for the founder.

## 2026-07-23 — Handoff for M2/M3 (/digest) + reference digest
Wrote docs/08_HANDOFF_DIGEST.md: the full handoff for the next agent (an Opus overseer) to
build the working /digest command — definition of done, what's built vs stub, the M2/M3
milestone plan + acceptance gates, environment reality (no ANTHROPIC_API_KEY; DATABASE_URL
unresolved so operate off data/untriaged.jsonl; UNPAYWALL_EMAIL/RESEND_API_KEY unset), the
guardrails, the open founder decisions (general-journal tiering ADR 0003; window length ADR
0002; secrets), and a key-file map. Handoff §7 mandates the token-efficiency workflow the
founder asked for: Opus holds context + prompt engineering + eval interpretation + review;
Sonnet subagents implement well-specified modules/tests (mirroring pubmed.py/enrich.py),
with the overseer verifying every subagent's output before committing. Captured a real
generated digest as templates/digest.sample.html — the design/quality bar for M3's Jinja
template (marked DESIGN REFERENCE, not the live template). Updated docs to match reality:
README status points to the handoff; .claude/commands/digest.md flagged authoritative-spec +
handoff pointer; PRD FR-3 now makes the evidence grade (A-D) and maximized OA coverage
binding requirements; roadmap M2/M3 deliverables reference the handoff, the A-D grade, the
sample template, and the DB-optional reality. No code changed; 47 tests still green. Next:
a fresh Opus session picks up docs/08_HANDOFF_DIGEST.md and starts M2 (triage prompt +
batching + scores + eval harness), pending the founder's eval-label set and tiering decision.

## 2026-07-24 — M2: triage layer (prompt + batching + scores + eval harness)
Built the M2 deliverables from docs/08_HANDOFF_DIGEST.md §4. Merged the completed M1
(claude/m1-step3-pubmed) into main first — it carried Step 3 + ADRs 0001-0003 + the handoff
and had never landed on main (main only had Steps 1-2); verified green (47 tests, ruff, make
doctor) before merging. Then, on top of it:
- prompts/triage-v1.md got its real body (was a placeholder awaiting M2). Injects
  PRACTICE_PROFILE.md by reference (not restated — §7 applied literally), takes the compact
  compressed-item shape, emits a strict per-item JSON array (relevance_tier, evidence_level
  A-D, one_line_takeaway, reasoning, topics[], confidence). Bakes in the three easy-to-miss
  rules: inclusive at the margin (torn noise/fyi -> fyi), Tier A never auto-noised (§8),
  retrospective n<30 floored at FYI (§6). Evidence grade derived from design/n/type per the
  A-D scale in .claude/commands/digest.md, independent of topic appeal.
- llm/batching.make_batches(): simple chunking to config/settings.yaml budget.triage_batch_size
  (~25); loud ValueError on a non-positive size. llm/scores.py: validate() rejects malformed
  triage JSON loudly (names the offending pmid), normalizes (str pmid, upper-cased grade,
  2dp confidence); two append-only sinks sharing that shape — write_scores(conn,...) for the
  Postgres scores table (resolves item_id by pmid, flips is_current, records
  model/prompt/profile) and write_scores_to_file()/load_current_scores() for the interim disk
  path while DATABASE_URL is unresolved (handoff §6). The DB path is unit-tested against a
  fake connection (no live DB in the suite, docs/02 §8).
- evalset/run_eval.py + `make eval`: a PURE comparator (no model call). The /digest session
  writes predictions to evalset/predictions.jsonl (gitignored, derived); this reads them vs
  evalset/labels.csv and reports practice-changing recall (primary; a missing prediction is
  an honest miss), tier agreement over scored items, and a 4x4 confusion matrix, with the M2
  gate (>=90% recall, >=80% agreement) shown as PASS/BELOW banners — informational, since the
  founder decides "fix profile or prompt?".
Verified: 94 tests pass (47 new: batching/scores/eval), ruff clean, make doctor OK. Ran the
eval harness end-to-end on synthetic (non-founder) data to confirm the report renders.
OPEN / founder tasks (surfaced, not fabricated): (1) evalset/labels.csv is still header-only
— the gate is BLOCKED until the founder hand-labels ~100-150 items (leftover M0, handoff
§4.3); `make eval` prints exactly this. (2) The general-journal Tier-A tiering decision (ADR
0003) and the 21-vs-32-day window (ADR 0002) remain the founder's calls. Next: run the real
eval once labels exist (record the delta in triage-v1's changelog per rule 5, iterate profile
-first), then M3 (synthesis prompt + Jinja template + Resend send).
