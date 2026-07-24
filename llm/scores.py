"""Validate triage JSON and persist score rows with full version provenance.

Implemented in Milestone M2 with the triage phase of /digest.

Design (docs/02 §5):
- `validate()` checks the session's strict-JSON output per item: relevance_tier
  (practice_changing | worth_knowing | fyi | noise), evidence_level (A-D),
  one_line_takeaway, reasoning, topics[], confidence. Malformed output is rejected
  LOUDLY with a plain explanation — never silently coerced (a wrong tier that slips
  through would quietly poison the digest).
- Scores are APPEND-ONLY with an `is_current` flag; every row records model
  ("claude-code-session/<model>"), prompt version, and profile version, so any score
  is traceable and the backlog is re-scorable when a better model ships.
- Two sinks share the same validated shape:
    * `write_scores(conn, ...)`  — the Postgres path (the `scores` table). Resolves
      item_id by pmid, flips the prior current row off, inserts the new current row.
    * `write_scores_to_file(path, ...)` — the interim disk path used while
      DATABASE_URL is unresolved in cloud sessions (handoff §6, ADR 0001). Appends
      JSONL; `load_current_scores()` reads it back with latest-per-pmid winning,
      the file analogue of the DB's is_current.
"""

import datetime
import json
from pathlib import Path

VALID_TIERS = ("practice_changing", "worth_knowing", "fyi", "noise")
VALID_GRADES = ("A", "B", "C", "D")

# The fields validate() emits, in a stable order, for both sinks.
SCORE_FIELDS = (
    "pmid",
    "relevance_tier",
    "evidence_level",
    "one_line_takeaway",
    "reasoning",
    "topics",
    "confidence",
)


def _require(cond, message):
    if not cond:
        raise ValueError(message)


def validate(score_json):
    """Return a validated, normalized score dict or raise ValueError.

    `score_json` is one item's parsed triage output (a dict). Every field is
    required; the error names the offending pmid so a bad batch is easy to trace.
    """
    _require(isinstance(score_json, dict), f"score must be a JSON object, got {type(score_json).__name__}")

    pmid = score_json.get("pmid")
    _require(pmid is not None and str(pmid).strip() != "", "score is missing a pmid")
    pmid = str(pmid).strip()
    where = f"item {pmid}"

    tier = score_json.get("relevance_tier")
    _require(tier in VALID_TIERS, f"{where}: relevance_tier must be one of {VALID_TIERS}, got {tier!r}")

    grade = score_json.get("evidence_level")
    grade = grade.strip().upper() if isinstance(grade, str) else grade
    _require(grade in VALID_GRADES, f"{where}: evidence_level must be one of {VALID_GRADES}, got {score_json.get('evidence_level')!r}")

    takeaway = score_json.get("one_line_takeaway")
    _require(isinstance(takeaway, str) and takeaway.strip() != "", f"{where}: one_line_takeaway must be a non-empty string")

    reasoning = score_json.get("reasoning")
    _require(isinstance(reasoning, str) and reasoning.strip() != "", f"{where}: reasoning must be a non-empty string")

    topics = score_json.get("topics")
    _require(isinstance(topics, list) and all(isinstance(t, str) for t in topics), f"{where}: topics must be a list of strings, got {topics!r}")

    confidence = score_json.get("confidence")
    _require(isinstance(confidence, (int, float)) and not isinstance(confidence, bool), f"{where}: confidence must be a number 0.0-1.0, got {confidence!r}")
    _require(0.0 <= float(confidence) <= 1.0, f"{where}: confidence must be between 0.0 and 1.0, got {confidence}")

    return {
        "pmid": pmid,
        "relevance_tier": tier,
        "evidence_level": grade,
        "one_line_takeaway": takeaway.strip(),
        "reasoning": reasoning.strip(),
        "topics": list(topics),
        "confidence": round(float(confidence), 2),
    }


def validate_all(score_jsons):
    """Validate a batch (list) of raw score dicts, returning validated dicts."""
    return [validate(s) for s in score_jsons]


# ---- Postgres sink (used once DATABASE_URL resolves; handoff §6) --------------

def write_scores(conn, scores, model, prompt_version, profile_version):
    """Append validated score rows to the `scores` table, one current row per item.

    `scores` are dicts from `validate()`. For each, the item_id is resolved by pmid;
    any existing current score for that item is flipped to is_current=false, then the
    new row is inserted as current — the append-only re-scoring semantics of
    db/migrations/...create_scores.sql. Skips (and reports) any pmid with no matching
    items row rather than failing the whole write.
    """
    written, skipped = 0, []
    model_str = f"claude-code-session/{model}"
    with conn.cursor() as cur:
        for score in scores:
            cur.execute("SELECT id FROM items WHERE pmid = %s", (score["pmid"],))
            row = cur.fetchone()
            if row is None:
                skipped.append(score["pmid"])
                continue
            item_id = row[0]
            cur.execute(
                "UPDATE scores SET is_current = false WHERE item_id = %s AND is_current",
                (item_id,),
            )
            cur.execute(
                """
                INSERT INTO scores (item_id, relevance_tier, evidence_level,
                    one_line_takeaway, reasoning, topics, confidence,
                    model, prompt_version, profile_version, is_current)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
                """,
                (item_id, score["relevance_tier"], score["evidence_level"],
                 score["one_line_takeaway"], score["reasoning"], score["topics"],
                 score["confidence"], model_str, prompt_version, profile_version),
            )
            written += 1
    conn.commit()
    return {"written": written, "skipped": skipped}


# ---- Interim disk sink (while DATABASE_URL is unresolved; ADR 0001) -----------

def _score_record(score, model, prompt_version, profile_version):
    return {
        **{k: score[k] for k in SCORE_FIELDS},
        "model": f"claude-code-session/{model}",
        "prompt_version": prompt_version,
        "profile_version": profile_version,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def write_scores_to_file(path, scores, model, prompt_version, profile_version):
    """Append validated scores to a JSONL file with full provenance.

    Append-only, mirroring the DB: re-scoring an item writes a new line rather than
    overwriting. `load_current_scores()` resolves the current score as the last line
    written for each pmid, the file analogue of the is_current flag.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [_score_record(s, model, prompt_version, profile_version) for s in scores]
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def load_current_scores(path):
    """Read a JSONL score file into {pmid: record}, latest line per pmid winning."""
    path = Path(path)
    current: dict[str, dict] = {}
    if not path.exists():
        return current
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            pmid = rec.get("pmid")
            if pmid is not None:
                current[str(pmid)] = rec
    return current
