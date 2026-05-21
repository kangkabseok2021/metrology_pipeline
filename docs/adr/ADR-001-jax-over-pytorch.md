# ADR-001: JAX over PyTorch for numerical kernels

**Status:** Accepted  
**Date:** 2026-05-21  
**Deciders:** Core team

## Context

The metrology pipeline performs large 2-D FFT operations and Wiener deconvolution on wafer height maps. Both PyTorch and JAX provide GPU-accelerated numerical computing, but they differ significantly in design philosophy.

## Decision

Use JAX (with `jax.numpy`) as the primary numerical backend.

## Rationale

1. **No graph overhead.** JAX transforms (`jit`, `grad`, `vmap`) are composable and compile to XLA HLO with no eager-mode graph construction overhead unlike PyTorch's `torch.compile`.
2. **XLA JIT compilation is transparent.** `@jax.jit` decorates arbitrary Python functions; the same function works on CPU, GPU, and TPU without code changes.
3. **NumPy-compatible API.** `jax.numpy` is a near-drop-in for `numpy`, enabling a clean CPU fallback shim (`backend.py`) with zero conditional logic in production code.
4. **Functional purity.** JAX enforces pure functions (no in-place mutation), which aligns with the immutable Pydantic models used throughout this package.

## Consequences

- JAX is not pre-installed in most environments; the `gpu` extra (`jax[cuda12]`) is optional and the package falls back to NumPy transparently.
- JAX's dynamic shapes (under `jax.experimental`) are still evolving; array shapes must be known at trace time for JIT, which is satisfied because wafer maps are always square power-of-two.
- Mypy stubs for JAX are incomplete; `[[tool.mypy.overrides]] ignore_missing_imports = true` is required.
