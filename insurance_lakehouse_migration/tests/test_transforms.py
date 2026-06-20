"""Tests for pure-Python transform helpers (no Spark needed)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from pipeline.silver.transforms import parse_ddmmyyyy, pascal_to_snake


def test_parse_ddmmyyyy_valid() -> None:
    assert parse_ddmmyyyy("15/03/2023") == "2023-03-15"


def test_parse_ddmmyyyy_none_returns_none() -> None:
    assert parse_ddmmyyyy(None) is None  # type: ignore[arg-type]


def test_parse_ddmmyyyy_empty_returns_none() -> None:
    assert parse_ddmmyyyy("") is None


def test_parse_ddmmyyyy_whitespace_returns_none() -> None:
    assert parse_ddmmyyyy("  ") is None


def test_pascal_to_snake_basic() -> None:
    assert pascal_to_snake("CustomerID") == "customer_i_d"


def test_pascal_to_snake_multi_word() -> None:
    assert pascal_to_snake("PolicyVersion") == "policy_version"


def test_pascal_to_snake_already_snake() -> None:
    assert pascal_to_snake("policy_id") == "policy_id"


def test_pascal_to_snake_lower() -> None:
    assert pascal_to_snake("PremiumAmount") == "premium_amount"
