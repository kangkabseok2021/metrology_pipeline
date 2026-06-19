"""Tests for formula prediction, isotope scoring, spectral matching, Schymanski levels."""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from metabopipe.annotation import (
    FormulaCandidate,
    FormulaPredictor,
    IsotopeScorer,
    SpectralMatch,
    SpectralMatcher,
    assign_schymanski_level,
)

# Glucose: neutral mass C6H12O6 = 180.06339 Da; [M+H]+ = 181.07067 Da
_GLUCOSE_MZ = 181.07067


def test_formula_prediction_finds_glucose() -> None:
    predictor = FormulaPredictor(ppm_tolerance=5.0)
    candidates = predictor.predict(_GLUCOSE_MZ)
    formulas = [c.formula for c in candidates]
    assert "C6H12O6" in formulas


def test_formula_prediction_sorted_by_ppm() -> None:
    predictor = FormulaPredictor(ppm_tolerance=5.0)
    candidates = predictor.predict(_GLUCOSE_MZ)
    assert candidates == sorted(candidates, key=lambda c: c.ppm_error)


def test_formula_prediction_all_within_tolerance() -> None:
    ppm = 3.0
    predictor = FormulaPredictor(ppm_tolerance=ppm)
    for c in predictor.predict(_GLUCOSE_MZ):
        assert c.ppm_error <= ppm


def test_isotope_scorer_ranks_best_first() -> None:
    predictor = FormulaPredictor(ppm_tolerance=5.0)
    candidates = predictor.predict(_GLUCOSE_MZ)
    scorer = IsotopeScorer()
    # Observed isotopes roughly matching C6H12O6
    scored = scorer.score(candidates, observed_m1_rel=0.068, observed_m2_rel=0.002)
    assert scored[0][1].formula == "C6H12O6"


def test_cosine_score_perfect_match() -> None:
    matcher = SpectralMatcher()
    peaks = [(100.0, 1000.0), (200.0, 500.0), (300.0, 250.0)]
    assert matcher.cosine_score(peaks, peaks) == pytest.approx(1.0, abs=1e-6)


def test_cosine_score_no_overlap() -> None:
    matcher = SpectralMatcher()
    a = [(100.0, 1000.0)]
    b = [(600.0, 1000.0)]
    assert matcher.cosine_score(a, b) == pytest.approx(0.0, abs=1e-6)


def test_cosine_score_partial_overlap() -> None:
    matcher = SpectralMatcher()
    a = [(100.0, 1000.0), (200.0, 500.0)]
    b = [(100.0, 1000.0), (300.0, 500.0)]
    score = matcher.cosine_score(a, b)
    assert 0.0 < score < 1.0


def test_spectral_matcher_load_and_match(tmp_path: Path) -> None:
    msp = tmp_path / "lib.msp"
    msp.write_text(
        "Name: TestCompound\nInChIKey: ABCDEFGHIJ\nNum Peaks: 2\n100.0 1000\n200.0 500\n\n"
    )
    matcher = SpectralMatcher(threshold=0.5)
    matcher.load_msp(msp)
    query = [(100.0, 1000.0), (200.0, 500.0)]
    matches = matcher.match(query)
    assert len(matches) == 1
    assert matches[0].compound_name == "TestCompound"
    assert matches[0].cosine_score == pytest.approx(1.0, abs=1e-4)


def test_spectral_matcher_no_match_below_threshold(tmp_path: Path) -> None:
    msp = tmp_path / "lib.msp"
    msp.write_text("Name: Different\nNum Peaks: 1\n600.0 1000\n\n")
    matcher = SpectralMatcher(threshold=0.7)
    matcher.load_msp(msp)
    matches = matcher.match([(100.0, 1000.0)])
    assert matches == []


def test_schymanski_level_1_reference_standard() -> None:
    level = assign_schymanski_level([], [], has_reference_standard=True)
    assert level == 1


def test_schymanski_level_2_high_cosine() -> None:
    matches = [SpectralMatch("X", "", cosine_score=0.85, matched_peaks=5)]
    level = assign_schymanski_level([FormulaCandidate("C6H12O6", 180.063, 0.1)], matches)
    assert level == 2


def test_schymanski_level_4_formula_only() -> None:
    level = assign_schymanski_level([FormulaCandidate("C6H12O6", 180.063, 0.1)], [])
    assert level == 4


def test_schymanski_level_5_no_evidence() -> None:
    level = assign_schymanski_level([], [])
    assert level == 5
