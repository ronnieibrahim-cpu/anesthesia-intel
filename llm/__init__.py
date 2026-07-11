"""Deterministic support code for the LLM phases of the weekly /digest session.

Nothing in this package calls any model API — there is no Anthropic API key in this
project (CLAUDE.md rule 3). The interactive Claude Code session does the reasoning;
these modules do the plumbing around it: batching items for triage, validating the
strict-JSON scores the session produces, and writing them to the database with full
version provenance.
"""
