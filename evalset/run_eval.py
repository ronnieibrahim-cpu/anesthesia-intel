"""The eval harness: how we measure before we trust (PRD FR-6).

STUB — implemented in Milestone M2; runnable inside a Claude Code session via
`make eval` ($0, no API key).

Design decided now:
- Compares current prompt + model scores against the founder's hand labels
  (evalset/labels.csv, also loaded into the eval_labels table).
- Reports, in this order of importance:
    1. practice-changing RECALL (missing a signal is worse than including noise),
    2. overall tier agreement,
    3. a confusion matrix.
- Mandatory before merging any change to prompts, filters, or PRACTICE_PROFILE.md
  (CLAUDE.md rule 5); the report goes in the PR description.
"""


def main() -> None:
    raise NotImplementedError("Implemented in M2 (eval harness).")


if __name__ == "__main__":
    main()
