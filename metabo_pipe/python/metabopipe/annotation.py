"""Metabolite annotation: formula prediction, isotope scoring, spectral matching, Schymanski levels."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Monoisotopic masses (Da)
_ELEMENT_MASSES: dict[str, float] = {
    "C": 12.000000,
    "H": 1.0078250319,
    "N": 14.0030740052,
    "O": 15.9949146221,
    "P": 30.97376151,
    "S": 31.97207069,
}

# (M+1 fraction, M+2 fraction) per element atom
_ISOTOPE_CONTRIB: dict[str, tuple[float, float]] = {
    "C": (0.01103, 0.0),
    "H": (0.000115, 0.0),
    "N": (0.00368, 0.0),
    "O": (0.000382, 0.00205),
    "S": (0.0076, 0.0422),
    "P": (0.0, 0.0),
}

_PROTON = 1.007276


@dataclass
class FormulaCandidate:
    formula: str
    exact_mass: float
    ppm_error: float


@dataclass
class SpectralMatch:
    compound_name: str
    inchikey: str
    cosine_score: float
    matched_peaks: int


@dataclass
class AnnotatedFeature:
    mz: float
    formula_candidates: list[FormulaCandidate]
    spectral_matches: list[SpectralMatch]
    schymanski_level: int


def _neutral_mass(c: int, h: int, n: int, o: int, p: int, s: int) -> float:
    return (
        c * _ELEMENT_MASSES["C"]
        + h * _ELEMENT_MASSES["H"]
        + n * _ELEMENT_MASSES["N"]
        + o * _ELEMENT_MASSES["O"]
        + p * _ELEMENT_MASSES["P"]
        + s * _ELEMENT_MASSES["S"]
    )


def _formula_str(c: int, h: int, n: int, o: int, p: int, s: int) -> str:
    parts = []
    for sym, count in [("C", c), ("H", h), ("N", n), ("O", o), ("P", p), ("S", s)]:
        if count > 0:
            parts.append(sym if count == 1 else f"{sym}{count}")
    return "".join(parts)


class FormulaPredictor:
    """Enumerate candidate molecular formulae within a ppm tolerance of the observed [M+H]+ m/z."""

    def __init__(self, ppm_tolerance: float = 5.0, adduct_mass: float = _PROTON) -> None:
        self._ppm = ppm_tolerance
        self._adduct = adduct_mass

    def predict(self, mz: float, max_c: int = 20, max_h: int = 42) -> list[FormulaCandidate]:
        target_neutral = mz - self._adduct
        if target_neutral <= 0:
            return []

        results: list[FormulaCandidate] = []
        for c in range(1, max_c + 1):
            for h in range(1, max_h + 1):
                for n in range(0, 4):
                    for o in range(0, 12):
                        mass = _neutral_mass(c, h, n, o, 0, 0)
                        ppm_err = abs(mass - target_neutral) / target_neutral * 1e6
                        if ppm_err <= self._ppm:
                            rdbe = (2 * c + 2 + n - h) / 2
                            if rdbe >= 0:
                                results.append(
                                    FormulaCandidate(
                                        formula=_formula_str(c, h, n, o, 0, 0),
                                        exact_mass=mass,
                                        ppm_error=round(ppm_err, 4),
                                    )
                                )
        results.sort(key=lambda x: x.ppm_error)
        return results


class IsotopeScorer:
    """Re-rank formula candidates by chi-squared isotope-pattern fit against observed M+1, M+2."""

    def _theoretical_isotopes(self, formula: str) -> tuple[float, float]:
        counts: dict[str, int] = {}
        for m in re.finditer(r"([A-Z][a-z]?)(\d*)", formula):
            sym, cnt = m.group(1), m.group(2)
            counts[sym] = int(cnt) if cnt else 1

        m1 = sum(counts.get(sym, 0) * contrib[0] for sym, contrib in _ISOTOPE_CONTRIB.items())
        m2 = sum(counts.get(sym, 0) * contrib[1] for sym, contrib in _ISOTOPE_CONTRIB.items())
        return m1, m2

    def score(
        self,
        candidates: list[FormulaCandidate],
        observed_m1_rel: float,
        observed_m2_rel: float,
    ) -> list[tuple[float, FormulaCandidate]]:
        scored: list[tuple[float, FormulaCandidate]] = []
        for cand in candidates:
            theo_m1, theo_m2 = self._theoretical_isotopes(cand.formula)
            chi2 = (observed_m1_rel - theo_m1) ** 2 / (theo_m1 + 1e-9) + (
                observed_m2_rel - theo_m2
            ) ** 2 / (theo_m2 + 1e-9)
            scored.append((chi2, cand))
        scored.sort(key=lambda x: x[0])
        return scored


class SpectralMatcher:
    """Cosine-similarity spectral library matcher (MSP format)."""

    def __init__(self, threshold: float = 0.7, bin_width: float = 0.01) -> None:
        self._threshold = threshold
        self._bin_width = bin_width
        self._mz_max = 1500.0
        self._n_bins = int(self._mz_max / self._bin_width) + 1
        self._library: list[dict] = []

    def load_msp(self, path: Path) -> None:
        with open(path) as f:
            text = f.read()
        for entry in re.split(r"\n\s*\n", text.strip()):
            lines = entry.strip().splitlines()
            record: dict = {}
            peaks: list[tuple[float, float]] = []
            in_peaks = False
            for line in lines:
                upper = line.strip().upper()
                if upper.startswith("NUM PEAKS"):
                    in_peaks = True
                    continue
                if in_peaks:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        try:
                            peaks.append((float(parts[0]), float(parts[1])))
                        except ValueError:
                            pass
                elif ":" in line:
                    key, _, val = line.partition(":")
                    record[key.strip().lower()] = val.strip()
            if peaks:
                record["_peaks"] = peaks
                self._library.append(record)

    def _bin_spectrum(self, peaks: list[tuple[float, float]]) -> np.ndarray:
        vec = np.zeros(self._n_bins)
        for mz, intensity in peaks:
            idx = int(mz / self._bin_width)
            if 0 <= idx < self._n_bins:
                vec[idx] += intensity
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def cosine_score(
        self,
        a: list[tuple[float, float]],
        b: list[tuple[float, float]],
    ) -> float:
        return float(np.dot(self._bin_spectrum(a), self._bin_spectrum(b)))

    def match(self, query_peaks: list[tuple[float, float]]) -> list[SpectralMatch]:
        if not self._library or not query_peaks:
            return []
        q_vec = self._bin_spectrum(query_peaks)
        results: list[SpectralMatch] = []
        for record in self._library:
            lib_peaks: list[tuple[float, float]] = record.get("_peaks", [])
            if not lib_peaks:
                continue
            score = float(np.dot(q_vec, self._bin_spectrum(lib_peaks)))
            if score >= self._threshold:
                matched = sum(
                    1
                    for qmz, _ in query_peaks
                    if any(abs(qmz - lmz) <= self._bin_width * 2 for lmz, _ in lib_peaks)
                )
                results.append(
                    SpectralMatch(
                        compound_name=record.get("name", "Unknown"),
                        inchikey=record.get("inchikey", ""),
                        cosine_score=round(score, 4),
                        matched_peaks=matched,
                    )
                )
        results.sort(key=lambda x: -x.cosine_score)
        return results


def assign_schymanski_level(
    formula_candidates: list[FormulaCandidate],
    spectral_matches: list[SpectralMatch],
    *,
    has_reference_standard: bool = False,
) -> int:
    """Assign Schymanski confidence level 1–5 based on available evidence."""
    if has_reference_standard:
        return 1
    if spectral_matches and spectral_matches[0].cosine_score >= 0.8:
        return 2
    if formula_candidates and spectral_matches:
        return 3
    if formula_candidates:
        return 4
    return 5
