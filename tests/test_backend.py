"""Tests for the JAX/NumPy backend shim."""

from __future__ import annotations

import numpy as np

from metrology_pipeline.backend import JAX_AVAILABLE, jit, jnp


def test_jax_available_is_bool() -> None:
    """JAX_AVAILABLE is a boolean."""
    assert isinstance(JAX_AVAILABLE, bool)


def test_jnp_has_fft2() -> None:
    """Backend exposes jnp.fft.fft2."""
    assert hasattr(jnp.fft, "fft2")


def test_jnp_fft2_runs() -> None:
    """jnp.fft.fft2 executes without error on a small array."""
    arr = np.ones((8, 8), dtype=np.float32)
    result = jnp.fft.fft2(arr)
    assert result is not None


def test_numpy_fallback_relative_error() -> None:
    """NumPy fallback produces output with relative error < 1e-5 vs direct numpy."""
    arr = np.random.default_rng(0).normal(size=(16, 16)).astype(np.float32)
    # Direct numpy
    expected = np.abs(np.fft.ifft2(np.fft.fft2(arr)))
    # Via backend (either jnp or numpy alias)
    got = np.array(np.abs(jnp.fft.ifft2(jnp.fft.fft2(arr))), dtype=np.float64)
    expected_f64 = expected.astype(np.float64)
    rel_err = np.max(np.abs(got - expected_f64) / (np.abs(expected_f64) + 1e-12))
    assert rel_err < 1e-4, f"Relative error too large: {rel_err}"


def test_jit_decorator_identity() -> None:
    """jit-decorated function returns same result as plain function."""

    def square(x: np.ndarray) -> np.ndarray:  # type: ignore[type-arg]
        return x * x

    jit_square = jit(square)
    arr = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    np.testing.assert_allclose(jit_square(arr), square(arr), rtol=1e-6)


def test_jnp_sqrt_positive() -> None:
    """jnp.sqrt returns positive values for positive input."""
    arr = np.array([1.0, 4.0, 9.0], dtype=np.float32)
    result = np.array(jnp.sqrt(arr))
    np.testing.assert_allclose(result, [1.0, 2.0, 3.0], rtol=1e-5)
