"""Date parsing and formatting.

`_sort` decides the order roles appear in, so a parse bug reorders a career
rather than failing loudly.
"""

import pytest

from render import format_month, format_range, parse_month


def test_parses_a_normal_month():
    assert parse_month("2024-06") == (2024, 6)


def test_parses_a_single_digit_month():
    assert parse_month("2024-6") == (2024, 6)


@pytest.mark.parametrize("value", ["present", "Present", "  PRESENT  "])
def test_present_sorts_after_everything(value):
    assert parse_month(value) == (9999, 12)


@pytest.mark.parametrize(
    "value",
    ["", "2024", "2024-06-01", "24-06", "june 2024", "2024/06", "not a date"],
)
def test_malformed_dates_are_rejected(value):
    with pytest.raises(SystemExit):
        parse_month(value)


@pytest.mark.parametrize("value", ["2024-0", "2024-13", "2024-99"])
def test_out_of_range_months_are_rejected(value):
    with pytest.raises(SystemExit):
        parse_month(value)


def test_present_formats_as_a_word():
    assert format_month("present") == "Present"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("2024-01", "Jan 2024"), ("2024-06", "Jun 2024"), ("2024-12", "Dec 2024")],
)
def test_month_names_are_correct_at_both_ends(value, expected):
    """MONTHS is indexed with `month - 1`; January and December catch an off-by-one."""
    assert format_month(value) == expected


def test_range_joins_with_an_en_dash():
    """The en-dash is deliberate: the finalizer turns it into LaTeX's `--`."""
    assert format_range("2024-06", "2026-07") == "Jun 2024 – Jul 2026"


def test_an_ongoing_range_reads_as_present():
    assert format_range("2024-06", "present") == "Jun 2024 – Present"
