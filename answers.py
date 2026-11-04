"""Parsing and checking numeric answers typed by students."""
import re

# A number, optional exponent ("e23", "*10^23", "x10**23", "×10^-5"), then an optional unit ("g", "kJ/mol").
_ANSWER = re.compile(
    r"^(?P<num>[-+]?(?:\d+\.?\d*|\.\d+))"
    r"(?:(?:e|[x×*]10(?:\^|\*\*))(?P<exp>[-+]?\d+))?"
    r"(?P<unit>[^\d.].*)?$",
    re.IGNORECASE,
)


def parse_answer(text: str):
    """Turn a typed answer into a float, or return None if it isn't a number.

    Accepts comma decimals, scientific notation written several ways, and a trailing unit
    (e.g. "14,6 g"), since that is how students actually type.
    """
    s = text.strip().replace(" ", "").replace(",", ".").replace("−", "-")
    match = _ANSWER.match(s)
    if not match:
        return None
    return float(f"{match['num']}e{match['exp'] or 0}")


def is_correct(value: float, answer: float, tolerance: float) -> bool:
    return abs(value - answer) <= (tolerance or 0) + 1e-12 * max(abs(answer), 1)


def match_common_error(value: float, common_errors: dict, tolerance: float):
    """Return the feedback for a known wrong answer, matching numerically rather than by string."""
    for wrong, message in (common_errors or {}).items():
        try:
            wrong_value = float(wrong)
        except ValueError:
            continue
        if is_correct(value, wrong_value, tolerance):
            return message
    return None
