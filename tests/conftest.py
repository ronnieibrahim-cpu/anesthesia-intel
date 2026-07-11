"""Shared pytest fixtures.

Conventions (docs/02 §8): tests cover deterministic logic only — parsers, dedupe,
pre-filter rules, HMAC, template rendering, caps enforcement. No live network calls;
source responses live as fixture files in tests/fixtures/. LLM prose is never mocked.
"""
