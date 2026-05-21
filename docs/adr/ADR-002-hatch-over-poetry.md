# ADR-002: Hatch over Poetry for build and environment management

**Status:** Accepted  
**Date:** 2026-05-21  
**Deciders:** Core team

## Context

Python packaging tooling choices affect reproducibility, CI speed, and contributor experience. Poetry and Hatch are both popular alternatives to bare setuptools.

## Decision

Use Hatchling as the PEP 517/518 build backend and `uv` as the package installer/resolver.

## Rationale

1. **PEP 517/518 native.** Hatchling implements the standardised build backend interface; any PEP 517-compatible tool can build the package without needing Hatch installed.
2. **No lock file divergence.** `uv` manages `uv.lock` deterministically using a SAT-solver; Poetry's `poetry.lock` is format-specific and has historically had resolution divergence on complex extras.
3. **`uv sync` replaces venv management.** `uv sync --extra dev` installs all development dependencies into an isolated virtual environment in a single command, replacing `poetry install`, `poetry env use`, and `venv` creation.
4. **Speed.** `uv` resolves and installs dependencies 10–100x faster than pip+Poetry due to Rust-based dependency resolution.
5. **Standard `pyproject.toml`.** All configuration lives in a single `[project]` table following PEP 621; no `[tool.poetry.*]` vendor-specific keys.

## Consequences

- Contributors need `uv` installed (`pip install uv` or `brew install uv`).
- `uv.lock` must be committed; the CI uses `--frozen` to enforce reproducibility.
- Hatch's `hatch env` feature is available but not required; `uv` handles environment creation.
