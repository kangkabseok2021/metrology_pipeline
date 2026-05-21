"""End-to-end pipeline tests."""

from __future__ import annotations

import pytest

from metrology_pipeline import PipelineResult, PipelineRunner, SensorReading


@pytest.fixture(scope="module")
def runner() -> PipelineRunner:
    """Shared PipelineRunner."""
    return PipelineRunner()


def test_pipeline_returns_result(
    reading: SensorReading, runner: PipelineRunner
) -> None:
    """PipelineRunner.run() returns a PipelineResult."""
    result = runner.run(reading)
    assert isinstance(result, PipelineResult)


def test_pipeline_processing_time_non_negative(
    reading: SensorReading, runner: PipelineRunner
) -> None:
    """processing_time_ms is >= 0."""
    result = runner.run(reading)
    assert result.processing_time_ms >= 0.0


def test_pipeline_defects_is_list(
    reading: SensorReading, runner: PipelineRunner
) -> None:
    """Defects field is a list."""
    result = runner.run(reading)
    assert isinstance(result.defects, list)


def test_pipeline_algorithm_fft(reading: SensorReading, runner: PipelineRunner) -> None:
    """Default algorithm is fft_bandpass."""
    result = runner.run(reading)
    assert result.algorithm == "fft_bandpass"


def test_pipeline_algorithm_wiener(
    reading: SensorReading, runner: PipelineRunner
) -> None:
    """use_wiener=True sets algorithm to wiener_deconvolution."""
    result = runner.run(reading, use_wiener=True)
    assert result.algorithm == "wiener_deconvolution"


def test_pipeline_gpu_accelerated_is_bool(
    reading: SensorReading, runner: PipelineRunner
) -> None:
    """gpu_accelerated is a bool."""
    result = runner.run(reading)
    assert isinstance(result.gpu_accelerated, bool)


def test_pipeline_scan_matches_input(
    reading: SensorReading, runner: PipelineRunner
) -> None:
    """PipelineResult.scan matches the input SensorReading."""
    result = runner.run(reading)
    assert result.scan == reading


def test_pipeline_wiener_has_defects_list(
    reading: SensorReading, runner: PipelineRunner
) -> None:
    """Wiener pipeline also returns a list of defects."""
    result = runner.run(reading, use_wiener=True)
    assert isinstance(result.defects, list)
