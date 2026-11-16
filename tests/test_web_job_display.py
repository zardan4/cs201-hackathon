"""Seniority and category icon shown on job cards."""

import pytest

from app.job_display import category_icon, job_level


@pytest.mark.parametrize("title, level", [
    ("Senior Backend Developer / AI Engineer", "Senior"),
    ("Junior System Administrator", "Junior"),
    ("Middle strong Full Stack Developer", "Middle"),
    ("Early-to-Middle / Middle Product Owner", "Middle"),
    ("Team Lead QA", "Lead"),
    ("Python Intern", "Intern"),
    ("Fullstack Engineer (TypeScript)", None),
    ("", None),
])
def test_job_level(title, level):
    assert job_level(title) == level


def test_category_icon_uses_first_known_category_and_falls_back():
    assert category_icon(["QA"]) == "qa"
    assert category_icon(["Other", "Python"]) == "code"
    assert category_icon([]) == "briefcase"
    assert category_icon(None) == "briefcase"
