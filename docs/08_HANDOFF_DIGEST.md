# HANDOFF — Get `/digest` to a working command (M2 → M3)

**Audience:** the next Claude Code agent (run this as an **Opus overseer**). You have zero
memory of prior sessions; this document plus the constitution docs are your full context.
**Goal in one line:** make `/digest` a real, working slash command that does exactly what
docs/01_PRD.md FR-2/FR-3 and the founder asked for — triage → synthesize → preview → send,
with a summary, an evidence grade, and a free-full-text link on every surfaced item.

---

## 0. First actions (do these before writing any code)

1. Read, in order: `CLAUDE.md`, `docs/00`–`docs/04`, `PRACTICE_PROFILE.md`, then this file.
2. Read the latest **STATE OF THE WORLD** entries in `docs/decisions/log.md` and **ADRs
   0001, 0002, 0003** in `docs/decisions/`. They explain why the pipeline is shaped as it is.
3. Read `.claude/commands/digest.md` — it is the **authoritative behavioral spec** for the
   command you are implementing. This handoff tells you *how to get there*; that file says
   *what the end state is*.
4. Look at `templates/digest.sample.html` in a browser — it is a **real generated digest**
   and the **quality/design bar** for the output. Your `templates/digest.html.j2` must
   reproduce it.
5. Confirm environment reality (see §6). Do **not** assume the database works.

**You are the overseer. Use Sonnet subagents for token efficiency wherever the work is
well-specified — see §7. This is a standing instruction, not a suggestion.**

---

## 1. Definition of done

`/digest` (typed in an interactive Claude Code session) must:

- Read the week's pre-filtered items (from `data/untriaged.jsonl` today; from the `items`
  table once the DB is reachable — see §6).
- **Phase 1 (triage):** score every item against `PRACTICE_PROFILE.md` into strict JSON:
  `relevance_tier` (practice_changing | worth_knowing | fyi | noise), `evidence_grade`
  (A–D), `one_line_takeaway`, `reasoning`, `topics[]`, `confidence`. Inclusive at the
  margin (torn → FYI). Written via `llm/scores.py` with model + prompt + profile versions.
- **Phase 2 (synthesis):** for surviving items, enforce caps (≤5 / ≤12 / ≤15) by
  **demoting**, never expanding; write a 2–4 sentence summary per item (one line for FYI);
  render `templates/digest.html.j2`.
- **Every surfaced item shows three things (binding founder requirement):**
  1. a 2–4 sentence summary (one line for FYI),
  2. an **evidence grade A–D** (scale defined in `.claude/commands/digest.md`), shown inline,
  3. a **"Free full text" link whenever `oa_url` exists** (abstract-only otherwise — never a
     paywalled/circumvented link, CLAUDE.md rule 2).
- **Phase 3 (preview → send):** show the rendered digest; accept conversational edits
  ("demote 4"); on the founder's explicit "send", deliver via Resend and store the copy.
  `--dry-run` stops at preview and sends nothing.
- Be **token-frugal** (§ "Token-efficient operation" in `.claude/commands/digest.md`).

**Acceptance is milestone-gated — see §4.**

---

## 2. Current state — what is built vs. stub

**Built and tested (47 tests pass, `uv run pytest -q`; `uv run ruff check .` clean):**

| Area | File(s) | Status |
|---|---|---|
| PubMed ingest | `pipeline/ingest/pubmed.py`, `config/sources.yaml` | done |
| Normalize + dedupe | `pipeline/normalize.py` | done |
| Pre-filter (Tier A/B + hard-drops) | `pipeline/prefilter.py`, `config/filters.yaml` | done |
| OA enrichment (Unpaywall + PMC) | `pipeline/enrich.py` | done |
| Orchestrator + file output | `pipeline/run_daily.py` (`make ingest-file`) | done |
| Cross-run seen ledger | `pipeline/seen_store.py` | done |
| Compressed triage shape | `llm/batching.py` `compress()` | done |
| DB schema | `db/migrations/*` (live in Supabase, applied manually) | done |

**Stubs / not built — this is your work:**

| What | File | Milestone |
|---|---|---|
| Triage prompt | `prompts/triage-v1.md` (placeholder) | M2 |
| Batch builder | `llm/batching.py` `make_batches()` (raises) | M2 |
| Score validation + write | `llm/scores.py` (raises) | M2 |
| Eval harness | `evalset/run_eval.py` (raises), `evalset/labels.csv` (header only) | M2 |
| Synthesis prompt | `prompts/synthesis-v1.md` (placeholder) | M3 |
| Digest template | `templates/digest.html.j2` (skeleton) — target is `templates/digest.sample.html` | M3 |
| Resend send | *does not exist yet* — new module, e.g. `pipeline/send.py` | M3 |
| The command body | `.claude/commands/digest.md` (spec only; the orchestration prose that a session executes) | M2–M3 |

---

## 3. The behavioral spec

`.claude/commands/digest.md` is authoritative. It already contains: the preamble (what to
read, `--dry-run`, preview-then-confirm, coverage = "since last sent digest", the interim
file source), the Phase 1/2/3 breakdown, the **evidence-grade A–D scale**, and a
**token-efficient-operation** section. Do not re-derive these — implement to them. If you
change the intended behavior, update that file in the same change (docs travel with code).

---

## 4. Milestone plan & acceptance

### M2 — Triage that agrees with the founder
1. Write `prompts/triage-v1.md` (real body): inject `PRACTICE_PROFILE.md` verbatim, emit the
   strict JSON above, be inclusive, never auto-noise Tier A, derive `evidence_grade` from
   design/n/type. Versioned — never edit a released prompt in place (copy to v2).
2. Implement `llm/batching.make_batches()` (≈25 compressed items/batch, size from
   `config/settings.yaml`) and `llm/scores.py` (`validate()` rejects malformed JSON loudly;
   `write_scores()` append-only, flips `is_current`, records model/prompt/profile versions).
3. **Eval set (blocks the gate):** `evalset/labels.csv` needs ~100–150 founder-hand-labeled
   items — **this is a founder task (leftover M0)**; surface it, don't fabricate labels.
   Implement `evalset/run_eval.py`: practice-changing **recall** (primary), tier agreement,
   confusion matrix.
4. **Gate:** ≥90% practice-changing recall, ≥80% tier agreement on the eval set; one week's
   volume triaged comfortably in one session. Run `make eval` and paste the report in the PR
   (CLAUDE.md rule 5). Iterate on the **profile first, prompt second** when it disagrees.

### M3 — Synthesis + digest + send
1. Write `prompts/synthesis-v1.md`: 2–4 sentence per-item synthesis in the academic voice
   (PRACTICE_PROFILE.md §9), key caveat last, relate to landmark trials/guidelines.
2. Enforce caps by demotion; render `templates/digest.html.j2` — **reproduce
   `templates/digest.sample.html`** (single column, evidence-grade chips, "Free full text"
   links, footer honesty metric incl. OA coverage; dark-mode-safe; no images).
3. Build the send path (new `pipeline/send.py`): Resend API, `--dry-run` support,
   preview-then-confirm default (CLAUDE.md rule 6). Store the sent copy in `digests` /
   `digest_items` when the DB is reachable; until then, write the HTML to disk.
4. Wire `.claude/commands/digest.md` into a working command.
5. **Gate:** a real digest generated end-to-end in one session; a `--dry-run` golden test
   diffs rendered HTML against a fixture week (docs/02 §8).

---

## 5. The reference digest (your quality bar)

`templates/digest.sample.html` is a real digest generated this session from the live corpus.
It is the design and quality target: masthead + week-in-brief, three tiers with counts,
per-item summary + evidence-grade chip + "Free full text" link + PubMed link, and a
pipeline-health footer. Turn it into the Jinja template — keep the design tokens (clinical
cool-slate neutrals, teal accent, semantic A/B/C/D grade colors, system serif for titles +
system sans for data) and both light/dark themes.

---

## 6. Environment reality (read before you debug anything)

- **No `ANTHROPIC_API_KEY`, ever** (CLAUDE.md rule 3; `make doctor` enforces). All LLM work
  is *you*, the interactive session — there is no programmatic model call in this repo.
- **`DATABASE_URL` does not resolve in cloud sessions** (open issue; ADR-adjacent notes in
  the log). The schema is live in Supabase (applied manually via SQL Editor). **Until it
  works, operate off `data/untriaged.jsonl`** (produced by `make ingest-file`; ADR 0001/0002)
  and write outputs to disk. Do not block on the DB.
- **`UNPAYWALL_EMAIL` unset** → OA links are PMC-only (fewer). Setting a real email raises
  coverage; `pipeline/enrich.py` already warns + falls back if it's invalid.
- **`RESEND_API_KEY` unset** → real email can't send. M3's send path needs it; until then
  `--dry-run` / write-to-disk is the path. Surface this to the founder.
- Network allowlist gotcha (for the DB later): the working Supabase host is
  `*.pooler.supabase.com` (IPv4), a different domain from `*.supabase.co`.

---

## 7. How to work: Opus overseer + Sonnet subagents (token efficiency)

**Standing policy for this handoff:** minimize Opus tokens by delegating well-specified
implementation to **Sonnet subagents**, while you (Opus) hold context and judgment.

**Keep on Opus (needs the strong model):**
- Prompt engineering (`triage-v1`, `synthesis-v1`) and any triage-quality iteration.
- Interpreting `make eval` results and deciding profile-vs-prompt fixes.
- Reviewing/verifying subagent output; architectural calls; founder-facing decisions.

**Delegate to Sonnet subagents (well-specified, mechanical):**
- Deterministic modules: `llm/batching.make_batches`, `llm/scores.py`, `evalset/run_eval.py`,
  `pipeline/send.py`, the Jinja template, and their fixture-based tests.
- Give each subagent: the precise spec, the **pattern to mirror** (`pipeline/ingest/pubmed.py`
  and `pipeline/enrich.py` are the reference style — pure logic separated from I/O),
  "fixture-based tests, **no live network in tests**", and "**do not commit or push**".
- **Always verify a subagent's output yourself** — run the tests, read the diff — before
  committing. Do not trust the report alone (this session caught a real silent-failure bug
  that way).
- A subagent starts cold; a good spec is cheaper than three rounds of correction. See the
  `enrich.py` subagent prompt in this session's history for the level of detail that worked.

**Commit discipline:** small PRs, one concern each; update docs in the same change; run the
full suite + ruff + `make doctor` before committing; `make eval` before any prompt/filter/
profile change with the report in the PR.

---

## 8. Guardrails you must not break (from CLAUDE.md)

1. No patient data, ever. 2. No paywall circumvention (Unpaywall/PMC only). 3. No
`ANTHROPIC_API_KEY`. 4. Model names only in `config/models.yaml`; prompts versioned (copy,
never edit in place). 5. `make eval` before prompt/filter/profile changes. 6. Anything that
sends email supports `--dry-run` and defaults to preview-then-confirm. 7. No V2 features
during V1 (park ideas in `docs/decisions/ideas.md`). 8/9. Plain readable Python/SQL; explain
tradeoffs in clinical-adjacent language.

---

## 9. Open decisions for the founder (surface these; don't decide unilaterally)

- **General-journal tiering (ADR 0003):** ~527 of ~817 passed items are general medical
  journals (JAMA/NEJM/Lancet/…) that are mostly non-anesthesia. Keyword-gating them would
  cut the corpus ~817→~350 (roughly halves triage tokens) but contradicts PRACTICE_PROFILE.md
  §8 ("Tier A never auto-noises") — needs a profile edit. Biggest single token lever for M2.
- **Lookback window (ADR 0002):** 21 days now; ~32 days would more robustly catch monthly
  journals' single-day batch postings if a run lands late in a month.
- **Secrets to enable the full experience:** `RESEND_API_KEY` (email), `UNPAYWALL_EMAIL`
  (more OA links), `DATABASE_URL` (persistence + feedback). All optional for building.

---

## 10. Key file map

```
.claude/commands/digest.md   authoritative behavioral spec (implement to this)
templates/digest.sample.html the output quality/design bar (make the .j2 match it)
templates/digest.html.j2     skeleton -> build in M3
prompts/triage-v1.md         placeholder -> write in M2 (versioned)
prompts/synthesis-v1.md      placeholder -> write in M3 (versioned)
llm/batching.py              compress() done; make_batches() TODO (M2)
llm/scores.py                validate()/write_scores() TODO (M2)
evalset/run_eval.py          TODO (M2); labels.csv needs founder labels
pipeline/run_daily.py        --to-file works today; DB path (--to-db) is Step 5
pipeline/{normalize,prefilter,enrich,seen_store}.py   done, tested
config/{sources,filters,models,settings}.yaml         the knobs (no code changes needed)
data/untriaged.jsonl         the interim corpus /digest reads (gitignored)
docs/decisions/{log.md,0001,0002,0003,ideas.md}       why things are the way they are
```

Start with M2. Good luck — and keep the founder's Monday ritual in mind: this only works if
the digest is trustworthy and the session is cheap.
