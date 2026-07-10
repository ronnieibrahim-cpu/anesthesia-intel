# Operating Prompts: Weekly Fallback + Claude Code Kickoff

## A. Zero-code fallback — run the digest manually in claude.ai TODAY (before any code exists)

Use this while the pipeline is being built, or any week the pipeline is down. Paste into a
claude.ai chat (web search on), ideally in a Project whose instructions contain your
PRACTICE_PROFILE.md so you never re-paste it:

```
You are my academic literature screener. My practice profile and tier rubric are in the
project instructions (PRACTICE_PROFILE.md) — apply them literally.

Task: search the literature published in the last 7 days across anesthesiology, regional
anesthesia, perioperative medicine, pain medicine, and generalist-relevant critical care,
plus FDA anesthesia-relevant safety communications and major society guideline updates
(ASA, ASRA, APSF, AHA/ACC perioperative). Prioritize my Tier A journals; include other
journals (including surgical literature) only for my standing questions.

Output a digest with hard caps — demote rather than exceed:
- PRACTICE-CHANGING (max 5): title, journal, design/n, 2–4 sentence synthesis written
  against MY practice, key caveat, link. Academic voice: relate to landmark trials and
  guidelines; note what a journal club would criticize.
- WORTH KNOWING (max 12): same, tighter.
- FYI (max 15): title + one line.
Then: a one-paragraph "week in brief." Flag any item with a free full-text version.
Be inclusive at the margins between FYI and noise, and honest when a week is quiet —
do not inflate weak findings to fill tiers.
```

Limitations vs the pipeline (be aware): web-search coverage is less systematic than a PubMed
API strategy, there's no deduplication memory between weeks, no feedback capture, and no eval
set. Fine as a bridge; not the destination.

## B. Claude Code kickoff prompt (copy-paste to start implementation)

**Model strategy for sessions:** use **Opus-class (Opus 4.8) or Fable 5 when available in
Claude Code** for this kickoff/architecture session and for M2 prompt-engineering sessions —
these decide structure and quality. Use **Sonnet 4.6** for routine implementation sessions
(M1 ingestion modules, templates, tests): materially cheaper on your usage limits with no
real fidelity loss on well-specified tasks. Check `/model` in Claude Code to switch.

Paste this to begin (after creating the repo and adding the docs — see README instructions):

```
Read, in this order: CLAUDE.md, docs/00_EXECUTIVE_SUMMARY.md, docs/01_PRD.md,
docs/02_TECHNICAL_DESIGN.md, docs/03_ROADMAP.md, docs/04_REPO_AND_CLAUDE_CODE.md,
PRACTICE_PROFILE.md. These are binding. I am the founder: a physician, not an engineer.

We are at Milestone M1. Work in plan mode first. Step-by-step protocol:

1. Propose the full repository scaffold as a file tree per docs/04, including the
   .claude/commands/digest.md skeleton, Makefile targets, and empty module stubs with
   docstrings. WAIT for my approval before writing files.
2. After approval: scaffold, then implement db/migrations for the schema in docs/02 §4,
   with dbmate. Show me how to run it against my Supabase project.
3. Implement pipeline/ingest/pubmed.py per config/sources.yaml (build sources.yaml from
   PRACTICE_PROFILE.md §8 Tier A + standing-question keywords), with pytest tests using
   fixture XML. No live network calls in tests.
4. Implement fda.py and rss.py to the same interface; then normalize.py + dedupe;
   then the pre-filter per docs/02 §3 (config-driven rules in config/filters.yaml);
   then Unpaywall/PMC enrichment.
5. Wire .github/workflows/daily.yml and ci.yml. Walk me through adding secrets
   (Supabase, Resend, HMAC) in plain language. Then a supervised live backfill of the
   last 90 days.

Rules for every step: one step per PR-sized change; run tests before declaring done;
update README/docs in the same change; end each step with "STATE OF THE WORLD" — three
sentences a future session needs. Never introduce an ANTHROPIC_API_KEY. If you're unsure
whether something is V1 scope, check docs/01_PRD.md §7 and ask me. Explain tradeoffs in
plain clinical-adjacent language. Begin with step 1 now.
```

## C. Session-handoff hygiene (every session, to prevent drift)

- **Open** each session with: "Read CLAUDE.md and docs/03_ROADMAP.md; we're on <milestone>.
  Read the last STATE OF THE WORLD note in docs/decisions/log.md."
- **Close** each session with: "Append a STATE OF THE WORLD entry to docs/decisions/log.md:
  what changed, what's next, any open questions. Update README if commands changed."
- CLAUDE.md + the docs/ folder + docs/decisions/log.md are the complete handoff surface;
  no session should ever depend on chat memory.
