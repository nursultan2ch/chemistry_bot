import pytest

from answers import parse_answer, is_correct, match_common_error


@pytest.mark.parametrize("text, expected", [
    ("0.5", 0.5),
    ("0,5", 0.5),
    (" 14,6 g ", 14.6),
    ("3.01e23", 3.01e23),
    ("3,01e23", 3.01e23),
    ("3.01*10^23", 3.01e23),
    ("3.01 × 10^23", 3.01e23),
    ("6.02x10**23", 6.02e23),
    ("2.5e-3 mol", 2.5e-3),
    ("−0.76 V", -0.76),
    ("12 mol/L", 12.0),
    (".5", 0.5),
])
def test_parse_answer_accepts_how_students_type(text, expected):
    assert parse_answer(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", "abc", "1.2.3", "e5", "five"])
def test_parse_answer_rejects_non_numbers(text):
    assert parse_answer(text) is None


def test_is_correct_uses_tolerance():
    assert is_correct(14.7, 14.6, 0.2)
    assert not is_correct(15.0, 14.6, 0.2)
    assert is_correct(143, 143, 0)
    assert is_correct(3.0100000000000001e23, 3.01e23, 0)


def test_common_errors_match_numerically():
    errors = {"18.0": "one mole only", "72": "doubled"}
    assert match_common_error(18, errors, 0.5) == "one mole only"
    assert match_common_error(72.2, errors, 0.5) == "doubled"
    assert match_common_error(50, errors, 0.5) is None
    assert match_common_error(18, {"oops": "ignored"}, 0.5) is None
