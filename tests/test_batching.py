"""Tests for make_batches — the deterministic chunking of compressed triage items."""

import pytest

from llm.batching import make_batches


def _items(n):
    return [{"pmid": str(i)} for i in range(n)]


def test_even_split():
    batches = list(make_batches(_items(50), 25))
    assert [len(b) for b in batches] == [25, 25]


def test_remainder_goes_in_a_final_short_batch():
    batches = list(make_batches(_items(53), 25))
    assert [len(b) for b in batches] == [25, 25, 3]


def test_fewer_items_than_batch_size():
    batches = list(make_batches(_items(3), 25))
    assert [len(b) for b in batches] == [3]


def test_empty_yields_nothing():
    assert list(make_batches([], 25)) == []


def test_preserves_items_and_order():
    items = _items(7)
    flattened = [it for batch in make_batches(items, 3) for it in batch]
    assert flattened == items


def test_accepts_a_generator_not_just_a_list():
    batches = list(make_batches((it for it in _items(4)), 2))
    assert [len(b) for b in batches] == [2, 2]


@pytest.mark.parametrize("bad", [0, -1, 2.5, None, "25"])
def test_non_positive_or_non_int_batch_size_raises(bad):
    with pytest.raises(ValueError):
        list(make_batches(_items(3), bad))
