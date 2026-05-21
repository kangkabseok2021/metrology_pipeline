"""Platform-adaptive JAX/NumPy backend."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    import jax.numpy as jnp
    from jax import jit

    JAX_AVAILABLE = True
except ImportError:
    import numpy as jnp  # type: ignore[no-redef]

    def jit(fn: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[no-redef]
        """No-op JIT decorator when JAX is unavailable."""
        return fn

    JAX_AVAILABLE = False

__all__ = ["jnp", "jit", "JAX_AVAILABLE"]
