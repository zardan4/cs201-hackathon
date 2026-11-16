"""The swipe feed mixes match strengths instead of listing 100% matches first."""

import random

from app.services import jobs_service


def _rows(scores):
    return [{"id": str(i), "score": score} for i, score in enumerate(scores)]


def test_weighted_shuffle_returns_limit_unique_rows():
    rows = _rows([1.0, 0.8, 0.6, 0.4, 0.2, 0.2, 0.6])
    picked = jobs_service.weighted_shuffle(rows, 5, random.Random(1))
    assert len(picked) == 5
    assert len({row["id"] for row in picked}) == 5
    assert all(row in rows for row in picked)


def test_weighted_shuffle_is_not_sorted_by_score():
    rows = _rows([1.0, 1.0, 1.0, 0.4, 0.4, 0.2, 0.2, 0.6, 0.6, 0.8])
    orders = {tuple(row["id"] for row in jobs_service.weighted_shuffle(rows, 10, random.Random(seed))) for seed in range(30)}
    assert len(orders) > 10  # many different orders
    sorted_ids = tuple(row["id"] for row in sorted(rows, key=lambda row: -row["score"]))
    assert sorted_ids not in orders or len(orders) > 1


def test_weighted_shuffle_favours_better_matches_but_not_always():
    rows = _rows([1.0, 0.2])
    rng = random.Random(7)
    firsts = [jobs_service.weighted_shuffle(rows, 1, rng)[0]["id"] for _ in range(2000)]
    best = firsts.count("0") / len(firsts)
    assert 0.55 < best < 0.85  # weights 1.25 vs 0.45 -> about 0.74


def test_weighted_shuffle_handles_short_input():
    assert jobs_service.weighted_shuffle([], 10) == []
    assert len(jobs_service.weighted_shuffle(_rows([0.5]), 10)) == 1
