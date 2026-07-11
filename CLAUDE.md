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
