# Repository Structure, Claude Code Workflow & Documentation Strategy

## 1. Repository structure

```
anesthesia-intel/                  (private GitHub repo)
├── CLAUDE.md                      ← Claude Code's standing instructions (draft below)
├── .claude/
│   └── commands/
│       └── digest.md              ← the weekly /digest slash command (triage → synthesis
│                                     → preview → send; supports --dry-run)
├── README.md                      ← what/why/how-to-run, kept current
├── PRACTICE_PROFILE.md            ← THE product knob. Versioned. Injected into prompts.
├── docs/
│   ├── 00_EXECUTIVE_SUMMARY.md    ← these four documents, checked in as the
│   ├── 01_PRD.md                     project's source of truth so Claude Code
│   ├── 02_TECHNICAL_DESIGN.md        can always read the full context
│   ├── 03_ROADMAP.md
│   └── decisions/                 ← ADRs: one short file per irreversible decision
├── config/
│   ├── sources.yaml               ← journals, PubMed strategy, feeds
│   ├── models.yaml                ← tier → model string (the ONE place)
│   └── settings.yaml              ← caps, schedule, budget guardrail
├── prompts/
│   ├── triage-v1.md               ← versioned; never edit in place, copy to vN+1
│   ├── synthesis-v1.md
│   └── deep_dive-v1.md
├── pipeline/                      ← see Technical Design §4
├── llm/
├── evalset/
│   ├── labels.csv                 ← ground truth (also loaded into DB)
│   └── run_eval.py
├── db/
│   └── migrations/                ← dbmate SQL migrations, numbered
├── templates/
│   └── digest.html.j2
├── functions/
│   └── feedback/index.ts          ← Supabase Edge Function
├── tests/
├── .github/workflows/             ← daily.yml · weekly.yml · eval.yml · ci.yml
├── Makefile                       ← ingest · triage · digest · eval · deep-dive · rescore · backup
└── pyproject.toml
```

## 2. Claude Code workflow (how a physician ships software safely)

**Session ritual**
1. Start every session by stating the milestone and pasting the relevant roadmap section, or just:
   *"Read docs/03_ROADMAP.md; we're on M2. Read CLAUDE.md."*
2. One session = one coherent task (a module, a bug, a prompt iteration). Resist scope creep;
   the roadmap gates exist so you don't have to negotiate with yourself mid-session.
3. End every session with: *"Update README/docs for anything that changed, run the tests, and
   summarize what a future session needs to know."*

**Branch discipline (yes, even solo)**
- `main` is always deployable (it literally deploys — Actions runs from `main`).
- Every change on a branch → PR → you read Claude Code's PR description → merge. The PR
  description is your engineering log. For prompt/model changes, the eval report goes in the PR.

**Guardrails that prevent expensive or unsafe mistakes**
- Claude Code never gets production secrets beyond what a task needs; `--dry-run` paths exist
  for everything that sends email or spends tokens.
- The eval set is the safety net: *"Run make eval and show me the diff vs. the last report"*
  before merging anything touching prompts, models, or the Practice Profile.
- When Claude Code proposes architecture changes, the bar is: does it contradict
  `docs/02_TECHNICAL_DESIGN.md`? If yes → write an ADR first, decide deliberately, then code.

**Prompting patterns that work well for this project**
- "Implement `pipeline/ingest/fda.py` following the interface in `pipeline/ingest/pubmed.py`;
  write tests with a fixture response; do not touch other files."
- "The digest miscategorized these 3 items [paste]. Diagnose: prompt, profile, or model?
  Propose the smallest change and show the eval impact."
- "Explain this module to me like I'm a smart clinician, not an engineer, before changing it."

## 3. Documentation strategy

Principle: **documentation is for two readers — future-you and future-Claude-Code sessions.**
Both have zero memory of past sessions. Optimize accordingly.

1. **The four docs in `docs/` are the constitution.** Changing product direction means editing
   them first, in a PR, so drift is impossible.
2. **ADRs for irreversible decisions only** (~10 lines each: context, decision, alternatives
   rejected, date). Examples: "no ORM," "Batch API for triage," "no patient data ever."
3. **README stays runnable:** a new machine → working local dev in ≤10 commands, verified
   occasionally by actually doing it.
4. **Prompts are self-documenting:** each prompt file opens with a changelog header (version,
   date, what changed, eval delta).
5. **No wikis, no Notion, no separate design docs.** Everything lives in the repo where Claude
   Code can read it.

## 4. Draft CLAUDE.md (check this into the repo root)

```markdown
# CLAUDE.md — standing instructions for Claude Code

## What this project is
A single-user pipeline that ingests medical literature daily, scores it against
PRACTICE_PROFILE.md, and emails a weekly digest. The founder is a physician, not an
engineer. Read docs/01_PRD.md and docs/02_TECHNICAL_DESIGN.md before structural changes.

## Hard rules
1. NEVER ingest, store, or process patient data. This is permanent and absolute.
2. No full-text scraping of paywalled journals and no paywall-circumvention services
   (Sci-Hub etc.) — ever. Reasons: (a) it violates copyright and publisher terms and creates
   legal exposure for the founder; (b) scrapers are brittle and break silently, poisoning the
   pipeline; (c) it is unnecessary — triage works on abstracts, and lawful open-access links
   (Unpaywall/PMC) are fetched automatically for full text where available.
3. This project has NO Anthropic API key. All LLM work happens inside interactive Claude Code
   sessions on the founder's Pro subscription (the /digest command). Never introduce, request,
   or read an ANTHROPIC_API_KEY; its presence would silently switch billing to pay-per-token.
   `make doctor` must fail if one is set. (A future API upgrade path is documented in
   docs/02_TECHNICAL_DESIGN.md but requires the founder's explicit written go-ahead.)
4. Model names live ONLY in config/models.yaml. Prompts live ONLY in prompts/ as
   versioned files — copy to a new version, never edit in place.
5. Any change to prompts, filters, or PRACTICE_PROFILE.md requires `make eval`; include
   the report in the PR description.
6. Anything that sends email must support --dry-run; /digest defaults to preview-then-confirm.
7. Respect docs/01_PRD.md §7 (Non-Goals). Do not build V2 features during V1, even if asked
   casually — note the idea in docs/decisions/ideas.md and confirm intent.
8. Prefer plain, readable Python and SQL. No new frameworks or dependencies without
   explaining the tradeoff in one paragraph and getting explicit approval.
9. Explain technical tradeoffs in clinical-adjacent plain language. The founder makes
   product decisions; you make technical recommendations with reasoning.

## Working style
- Small PRs, one concern each. Update docs in the same PR as behavior changes.
- Write tests for deterministic logic; do not mock LLM prose.
- When uncertain, choose simplicity. When still uncertain, ask.
```
