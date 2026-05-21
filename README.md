# metrology-pipeline

[![CI](https://github.com/kangkabseok2021/metrology_pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/kangkabseok2021/metrology_pipeline/actions/workflows/ci.yml)

A GPU-Accelerated Metrology Pipeline — a Python package that simulates ingestion, validation, and numerical processing of semiconductor wafer inspection data.

---

## 1. Overview

`metrology-pipeline` models the data path of a real wafer inspection system:

- **Data generation** — synthetic height maps with embedded defects, saved as chunked HDF5 files.
- **Validation** — Pydantic v2 models enforce wafer ID format, pixel-size constraints, and SHA-256 file integrity before any processing begins.
- **FFT bandpass detection** — a 2-D frequency-domain filter isolates defect-scale spatial frequencies and applies local-maxima clustering to produce `DefectDetection` records.
- **Wiener deconvolution** — optional optical-blur removal using a Gaussian PSF model, improving PSNR before detection on blurred scans.
- **Platform-adaptive backend** — JAX (`jax.numpy` + `@jax.jit`) when available for GPU/TPU acceleration; transparent NumPy fallback for CPU-only environments.

---

## 2. Architecture

```
SensorDataGenerator
        │  generates (HDF5 file + checksum)
        ▼
SensorReading (Pydantic, frozen)
        │  validated by ScanMetadata
        ▼
PipelineRunner.run()
    ├── [optional] WienerDeconvolution.deconvolve()
    │       └── Wiener filter in frequency domain
    └── FFTDefectDetector.detect()
            ├── jnp.fft.fft2  (JAX JIT or NumPy)
            ├── bandpass mask [0.01, 0.10] cycles/px
            ├── 3-sigma threshold
            └── local-maxima clustering
                        │
                        ▼
              PipelineResult (Pydantic, frozen)
                  defects: list[DefectDetection]
                  algorithm: fft_bandpass | wiener_deconvolution
                  gpu_accelerated: bool
```

---

## 3. Installation

```bash
# Install uv (if not already present)
pip install uv

# Clone and install with all dev dependencies
git clone https://github.com/kangkabseok2021/metrology_pipeline.git
cd metrology_pipeline
uv sync --extra dev
```

For GPU support (requires CUDA 12):

```bash
uv sync --extra gpu
```

---

## 4. Running the pipeline

```python
from pathlib import Path
from metrology_pipeline import SensorDataGenerator, PipelineRunner

# Generate a synthetic 512x512 wafer scan
gen = SensorDataGenerator(size=512)
reading, defect_specs = gen.generate(
    wafer_id="AB000001",
    n_defects=10,
    seed=42,
    output_dir=Path("/tmp"),
)

# Run the pipeline
runner = PipelineRunner()
result = runner.run(reading)

print(f"Algorithm : {result.algorithm}")
print(f"GPU used  : {result.gpu_accelerated}")
print(f"Time (ms) : {result.processing_time_ms:.1f}")
print(f"Defects   : {len(result.defects)}")
for d in result.defects[:3]:
    print(f"  id={d.defect_id}  ({d.x_nm:.0f}, {d.y_nm:.0f}) nm  "
          f"depth={d.depth_nm:.1f} nm  severity={d.severity}")
```

---

## 5. Running tests

```bash
# All tests except benchmarks and GPU tests
uv run pytest tests/ -v -m "not benchmark and not gpu"

# Include benchmarks
uv run pytest tests/benchmarks/ -v --benchmark-json=results.json

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/ --strict
```

---

## 6. How to Add a New Algorithm

Follow these steps to integrate a new defect-detection or pre-processing algorithm:

1. **Create a new module** in `src/metrology_pipeline/`, e.g. `src/metrology_pipeline/my_algorithm.py`.
2. **Implement a class** with a `process(height_map, metadata) -> list[DefectDetection]` or `deconvolve(height_map) -> np.ndarray` signature matching existing conventions.
3. **Use the backend shim** (`from .backend import jnp, jit`) for any FFT or linear-algebra operations to get automatic JAX/NumPy dispatch.
4. **Add tests** in `tests/test_my_algorithm.py`. Cover: output shape, dtype, value sanity, and edge cases (all-zero input, single-pixel image).
5. **Export from `__init__.py`** by adding your class to the `__all__` list in `src/metrology_pipeline/__init__.py`.
6. **Wire into `PipelineRunner`** — add a new branch in `pipeline.py` and extend the `algorithm` `Literal` type in `models.py`.
7. **Add an ADR** in `docs/adr/` if the algorithm introduces a new dependency or architectural trade-off.

---

## 7. Architectural Decisions

| ADR | Decision |
|-----|----------|
| [ADR-001](docs/adr/ADR-001-jax-over-pytorch.md) | JAX over PyTorch for XLA JIT compilation and NumPy-compatible CPU fallback |
| [ADR-002](docs/adr/ADR-002-hatch-over-poetry.md) | Hatch + uv over Poetry for PEP 517-native builds and fast dependency resolution |
| [ADR-003](docs/adr/ADR-003-hdf5-over-parquet.md) | HDF5 over Parquet for n-dimensional array storage with chunked partial reads |

---

## 8. CI

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs four jobs on every push to `main`:

| Job | What it does |
|-----|-------------|
| `lint` | `ruff check` + `ruff format --check` |
| `typecheck` | `mypy src/ --strict` |
| `test` | `pytest` excluding `benchmark` and `gpu` markers |
| `benchmark` | `pytest tests/benchmarks/` with JSON artifact upload |
