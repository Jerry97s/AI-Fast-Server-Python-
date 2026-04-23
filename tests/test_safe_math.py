from __future__ import annotations

import pytest

from safe_math import evaluate_arithmetic


def test_basic_arithmetic():
    assert evaluate_arithmetic("2 + 3") == 5
    assert evaluate_arithmetic("(1 + 2) * 3") == 9
    assert evaluate_arithmetic("2 ** 10") == 1024


def test_rejects_arbitrary_code():
    with pytest.raises(ValueError):
        evaluate_arithmetic("__import__('os')")


def test_rejects_empty():
    with pytest.raises(ValueError):
        evaluate_arithmetic("")
