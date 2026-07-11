"""The free, automated, non-LLM half of Anesthesia Intelligence.

Runs daily via GitHub Actions (docs/02 §1): ingest → normalize/dedupe → pre-filter →
open-access enrichment, writing into Supabase Postgres. No LLM, no API keys for
Anthropic, no patient data — ever (CLAUDE.md hard rules 1 and 3).
"""
