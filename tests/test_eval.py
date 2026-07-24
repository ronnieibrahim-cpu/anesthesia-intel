"""Tests for the eval harness: label loading and the metric computation."""

import pytest

from evalset import run_eval


# ---- load_labels -------------------------------------------------------------

def _write_csv(path, rows):
    header = "pmid,doi,title,journal,publication_date,true_tier,notes\n"
    path.write_text(header + "".join(rows), encoding="utf-8")


def test_load_labels_reads_pmid_and_tier(tmp_path):
    csv_path = tmp_path / "labels.csv"
    _write_csv(csv_path, [
        "111,,A trial,NEJM,2026-07-01,practice_changing,\n",
        "222,,An obs study,BJA,2026-07-02,fyi,small n\n",
    ])
    assert run_eval.load_labels(csv_path) == {"111": "practice_changing", "222": "fyi"}


def test_load_labels_skips_rows_without_pmid_or_tier(tmp_path):
    csv_path = tmp_path / "labels.csv"
    _write_csv(csv_path, [
        "111,,A,NEJM,2026-07-01,worth_knowing,\n",
        ",,No pmid,NEJM,2026-07-01,fyi,\n",
        "333,,No tier,NEJM,2026-07-01,,\n",
    ])
    assert run_eval.load_labels(csv_path) == {"111": "worth_knowing"}


def test_load_labels_rejects_bad_tier(tmp_path):
    csv_path = tmp_path / "labels.csv"
    _write_csv(csv_path, ["111,,A,NEJM,2026-07-01,super_important,\n"])
    with pytest.raises(ValueError, match="true_tier"):
        run_eval.load_labels(csv_path)


def test_load_labels_missing_file_is_empty(tmp_path):
    assert run_eval.load_labels(tmp_path / "nope.csv") == {}


# ---- compute_metrics ---------------------------------------------------------

def test_recall_counts_missing_prediction_as_a_miss():
    labels = {"1": "practice_changing", "2": "practice_changing", "3": "fyi"}
    predictions = {"1": "practice_changing"}  # item 2 (a PC) never scored
    m = run_eval.compute_metrics(labels, predictions)
    assert m["pc_total"] == 2
    assert m["pc_recalled"] == 1
    assert m["pc_recall"] == 0.5
    assert m["n_unscored"] == 2  # items 2 and 3 have no prediction


def test_tier_agreement_is_over_scored_items_only():
    labels = {"1": "practice_changing", "2": "fyi", "3": "noise"}
    predictions = {"1": "practice_changing", "2": "worth_knowing"}  # 3 unscored
    m = run_eval.compute_metrics(labels, predictions)
    assert m["n_scored"] == 2
    assert m["agree"] == 1              # only item 1 matches
    assert m["tier_agreement"] == 0.5


def test_confusion_matrix_counts_true_by_pred():
    labels = {"1": "practice_changing", "2": "practice_changing"}
    predictions = {"1": "practice_changing", "2": "worth_knowing"}
    m = run_eval.compute_metrics(labels, predictions)
    assert m["matrix"]["practice_changing"]["practice_changing"] == 1
    assert m["matrix"]["practice_changing"]["worth_knowing"] == 1


def test_extra_predictions_not_in_labels_are_ignored_but_counted():
    labels = {"1": "fyi"}
    predictions = {"1": "fyi", "999": "practice_changing"}
    m = run_eval.compute_metrics(labels, predictions)
    assert m["n_scored"] == 1
    assert m["n_extra_predictions"] == 1
    assert m["tier_agreement"] == 1.0


def test_no_practice_changing_labels_gives_null_recall():
    m = run_eval.compute_metrics({"1": "fyi"}, {"1": "fyi"})
    assert m["pc_total"] == 0
    assert m["pc_recall"] is None


# ---- format_report -----------------------------------------------------------

def test_report_flags_pass_and_below_gate():
    # Perfect recall + agreement -> PASS shows up; nothing "BELOW GATE".
    labels = {"1": "practice_changing", "2": "fyi"}
    predictions = {"1": "practice_changing", "2": "fyi"}
    report = run_eval.format_report(run_eval.compute_metrics(labels, predictions))
    assert "PASS" in report
    assert "BELOW GATE" not in report

    # A missed practice-changing item drops recall below the 90% gate.
    labels2 = {"1": "practice_changing", "2": "practice_changing"}
    predictions2 = {"1": "practice_changing", "2": "noise"}
    report2 = run_eval.format_report(run_eval.compute_metrics(labels2, predictions2))
    assert "BELOW GATE" in report2
