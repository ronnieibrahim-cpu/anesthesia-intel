"""Scaffold smoke test: every module imports, every config file parses.

Keeps CI green from day one and catches syntax errors or broken YAML the moment
they're committed, before any real logic exists.
"""

import importlib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

MODULES = [
    "pipeline",
    "pipeline.db",
    "pipeline.ingest",
    "pipeline.ingest.pubmed",
    "pipeline.ingest.fda",
    "pipeline.ingest.rss",
    "pipeline.normalize",
    "pipeline.prefilter",
    "pipeline.enrich",
    "pipeline.run_daily",
    "llm",
    "llm.batching",
    "llm.scores",
]

CONFIG_FILES = [
    "config/sources.yaml",
    "config/filters.yaml",
    "config/models.yaml",
    "config/settings.yaml",
]


def test_all_modules_import():
    for name in MODULES:
        importlib.import_module(name)


def test_all_config_files_parse():
    for rel_path in CONFIG_FILES:
        parsed = yaml.safe_load((REPO_ROOT / rel_path).read_text())
        assert isinstance(parsed, dict), f"{rel_path} should parse to a mapping"


def test_settings_caps_match_prd():
    settings = yaml.safe_load((REPO_ROOT / "config/settings.yaml").read_text())
    caps = settings["digest"]["caps"]
    assert caps == {"practice_changing": 5, "worth_knowing": 12, "fyi": 15}
