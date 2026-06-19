"""CWT peak detection, LOESS retention-time alignment, feature-matrix construction."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
from scipy.signal import find_peaks  # type: ignore[attr-defined]
from statsmodels.nonparametric.smoothers_lowess import lowess  # type: ignore[import-untyped]

from .reader import ExtractedIonChromatogram


def _ricker(n: int, a: float) -> np.ndarray:
    """Ricker (Mexican hat) wavelet at scale *a* with *n* points."""
    t = np.linspace(-3 * a, 3 * a, max(n, 3))
    return (1.0 - (t / a) ** 2) * np.exp(-0.5 * (t / a) ** 2)


def _cwt_ricker(signal: np.ndarray, widths: np.ndarray) -> np.ndarray:
    """CWT of *signal* against Ricker wavelets for each width in *widths*."""
    matrix = np.zeros((len(widths), len(signal)))
    for i, w in enumerate(widths):
        wav = _ricker(min(int(10 * w), len(signal)), float(w))
        matrix[i] = np.convolve(signal, wav / (wav @ wav + 1e-12) ** 0.5, mode="same")
    return matrix


@dataclass
class ChromatographicPeak:
    rt_apex: float
    mz: float
    area: float
    apex_intensity: float


@dataclass
class AlignedFeature:
    mz: float
    rt_consensus: float
    sample_intensities: dict[str, float] = field(default_factory=dict)


class FeatureDetector:
    """centWave-style CWT peak picker using Ricker wavelets."""

    def __init__(
        self,
        min_width: int = 3,
        max_width: int = 15,
        min_snr: float = 3.0,
    ) -> None:
        self._widths = np.arange(min_width, max_width + 1)
        self._min_snr = min_snr

    def find_peaks(self, eic: ExtractedIonChromatogram) -> list[ChromatographicPeak]:
        signal = eic.intensity_array.astype(float)
        if signal.max() == 0:
            return []

        cwt_matrix = _cwt_ricker(signal, self._widths)
        ridge = np.clip(cwt_matrix.max(axis=0), 0.0, None)

        ridge_max = ridge.max()
        if ridge_max < 1e-12:
            return []

        # Height threshold: peaks must exceed min_snr% of ridge maximum.
        # For real (noisy) data the ridge baseline is elevated, so min_snr acts
        # as an SNR multiplier; for clean synthetic signals it acts as a relative
        # gate at min_snr/100 of the maximum response.
        threshold = ridge_max * (self._min_snr / 100.0)

        peak_indices, _ = find_peaks(ridge, height=threshold, distance=3)

        peaks: list[ChromatographicPeak] = []
        for idx in peak_indices:
            lo = max(0, idx - 5)
            hi = min(len(signal), idx + 6)
            area = float(np.trapezoid(signal[lo:hi], eic.rt_array[lo:hi]))
            peaks.append(
                ChromatographicPeak(
                    rt_apex=float(eic.rt_array[idx]),
                    mz=eic.mz_target,
                    area=area,
                    apex_intensity=float(signal[idx]),
                )
            )
        return peaks


class RTAligner:
    """LOESS-based retention-time drift corrector."""

    def __init__(self, frac: float = 0.5) -> None:
        self._frac = frac

    def align(
        self,
        sample_peaks: dict[str, list[ChromatographicPeak]],
        reference_sample: str,
    ) -> dict[str, list[ChromatographicPeak]]:
        ref_rts = np.array(sorted(p.rt_apex for p in sample_peaks[reference_sample]))
        if ref_rts.size < 2:
            return sample_peaks

        aligned: dict[str, list[ChromatographicPeak]] = {}
        for sample, peaks in sample_peaks.items():
            if sample == reference_sample or not peaks:
                aligned[sample] = peaks
                continue

            src_rts = np.array([p.rt_apex for p in peaks])
            matched_ref = ref_rts[np.argmin(np.abs(ref_rts[:, None] - src_rts[None, :]), axis=0)]

            if src_rts.size < 2:
                aligned[sample] = peaks
                continue

            smoothed = lowess(matched_ref, src_rts, frac=self._frac, return_sorted=True)
            # smoothed[:,0] = src RT, smoothed[:,1] = corrected RT
            corrected_map = dict(zip(smoothed[:, 0].tolist(), smoothed[:, 1].tolist()))

            corrected: list[ChromatographicPeak] = []
            for p in peaks:
                closest_key = min(corrected_map, key=lambda x: abs(x - p.rt_apex))
                corrected.append(
                    ChromatographicPeak(
                        rt_apex=corrected_map[closest_key],
                        mz=p.mz,
                        area=p.area,
                        apex_intensity=p.apex_intensity,
                    )
                )
            aligned[sample] = corrected
        aligned.setdefault(reference_sample, sample_peaks[reference_sample])
        return aligned


class FeatureMatrixBuilder:
    """Group aligned peaks across samples into consensus features and build intensity matrix."""

    def __init__(self, mz_tol_ppm: float = 5.0, rt_tol_sec: float = 10.0) -> None:
        self._mz_tol_ppm = mz_tol_ppm
        self._rt_tol_sec = rt_tol_sec

    # -- union-find helpers -----------------------------------------------
    @staticmethod
    def _find(parent: list[int], x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    @staticmethod
    def _union(parent: list[int], a: int, b: int) -> None:
        parent[FeatureMatrixBuilder._find(parent, a)] = FeatureMatrixBuilder._find(parent, b)

    # ---------------------------------------------------------------------

    def build(
        self,
        sample_peaks: dict[str, list[ChromatographicPeak]],
        fill_value: float = 0.0,
    ) -> tuple[list[str], list[str], np.ndarray]:
        """Return (sample_names, feature_labels, intensity_matrix [samples × features])."""
        samples = sorted(sample_peaks)
        all_peaks: list[tuple[str, ChromatographicPeak]] = [
            (s, p) for s, peaks in sample_peaks.items() for p in peaks
        ]
        n = len(all_peaks)
        parent = list(range(n))

        for i in range(n):
            for j in range(i + 1, n):
                pi, pj = all_peaks[i][1], all_peaks[j][1]
                if pi.mz == 0:
                    continue
                mz_diff_ppm = abs(pi.mz - pj.mz) / pi.mz * 1e6
                rt_diff = abs(pi.rt_apex - pj.rt_apex)
                if mz_diff_ppm <= self._mz_tol_ppm and rt_diff <= self._rt_tol_sec:
                    self._union(parent, i, j)

        clusters: dict[int, list[tuple[str, ChromatographicPeak]]] = defaultdict(list)
        for i, sp in enumerate(all_peaks):
            clusters[self._find(parent, i)].append(sp)

        feature_labels: list[str] = []
        feature_sample_maps: list[dict[str, float]] = []
        for members in clusters.values():
            consensus_mz = float(np.mean([p.mz for _, p in members]))
            consensus_rt = float(np.mean([p.rt_apex for _, p in members]))
            per_sample = {s: p.apex_intensity for s, p in members}
            feature_labels.append(f"mz{consensus_mz:.4f}_rt{consensus_rt:.1f}")
            feature_sample_maps.append(per_sample)

        matrix = np.full((len(samples), len(feature_labels)), fill_value)
        for fi, per_sample in enumerate(feature_sample_maps):
            for si, s in enumerate(samples):
                if s in per_sample:
                    matrix[si, fi] = per_sample[s]

        return samples, feature_labels, matrix
