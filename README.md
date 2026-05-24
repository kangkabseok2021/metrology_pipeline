# metrology-pipeline

[![CI](https://github.com/kangkabseok2021/metrology_pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/kangkabseok2021/metrology_pipeline/actions/workflows/ci.yml)

Two production-style Python packages in one repo:

| Package | Domain |
|---------|--------|
| [`metrology_pipeline`](#metrology_pipeline) | GPU-accelerated semiconductor wafer inspection |
| [`leo_tracker`](#leo_tracker) | LEO satellite detection and tracking in sensor imagery |

---

## metrology_pipeline

Models the data path of a real wafer inspection system.

### What it does

- **Data generation** — synthetic height maps with embedded defects saved as chunked HDF5 files.
- **Validation** — Pydantic v2 models enforce wafer ID format, pixel-size constraints, and SHA-256 file integrity before any processing begins.
- **FFT bandpass detection** — a 2-D frequency-domain filter isolates defect-scale spatial frequencies and applies local-maxima clustering to produce `DefectDetection` records.
- **Wiener deconvolution** — optional optical-blur removal using a Gaussian PSF model, improving PSNR before detection on blurred scans.
- **Platform-adaptive backend** — JAX (`jax.numpy` + `@jax.jit`) when available for GPU/TPU acceleration; transparent NumPy fallback for CPU-only environments.

### Architecture

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

### Usage

```python
from pathlib import Path
from metrology_pipeline import SensorDataGenerator, PipelineRunner

gen = SensorDataGenerator(size=512)
reading, _ = gen.generate(wafer_id="AB000001", n_defects=10, seed=42, output_dir=Path("/tmp"))

runner = PipelineRunner()
result = runner.run(reading)

print(f"Algorithm : {result.algorithm}")
print(f"GPU used  : {result.gpu_accelerated}")
print(f"Defects   : {len(result.defects)}")
```

### Architectural decisions

| ADR | Decision |
|-----|----------|
| [ADR-001](docs/adr/ADR-001-jax-over-pytorch.md) | JAX over PyTorch for XLA JIT and NumPy-compatible CPU fallback |
| [ADR-002](docs/adr/ADR-002-hatch-over-poetry.md) | Hatch + uv over Poetry for PEP 517-native builds |
| [ADR-003](docs/adr/ADR-003-hdf5-over-parquet.md) | HDF5 over Parquet for n-dimensional chunked array storage |

---

## leo_tracker

Detects and tracks low-Earth-orbit satellites in synthetic sensor imagery using a
morphological image processing chain and sub-pixel centroiding.

### What it does

- **Synthetic frame generation** — Poisson-noise sky background with injected Gaussian stars and satellite streaks at configurable SNR.
- **Background subtraction** — large-kernel `scipy.ndimage.median_filter` removes the extended sky gradient; `white_tophat` morphological transform enhances compact sources.
- **Morphological detection chain** — `GaussianBlur` → MAD-threshold → `MORPH_OPEN` → `connectedComponentsWithStats` → per-blob bounding boxes.
- **Sub-pixel centroiding** — weighted centre-of-mass via 1-D marginal sums (O(N)):

  `Cx = Σ x·I(x,y) / Σ I(x,y)`

- **Cramer-Rao uncertainty** — `σ_c = σ_PSF / SNR` per detection.
- **Parallel batch processing** — `ProcessPoolExecutor` for GIL bypass; `OMP_NUM_THREADS=1` prevents OpenBLAS thread over-subscription inside workers.
- **SOLID design** — `AbstractDetector` ABC + `IFrameLoader`/`IFrameWriter` Protocols; concrete classes injected at construction time.
- **Alternate detector** — `FFTDetector` for frames with periodic background patterns.

### Architecture

```
SyntheticImageGenerator
        │  .npy frames (float32, 512×512)
        ▼
PipelineOrchestrator
    │  IFrameLoader.load()
    ▼
MorphologicalDetector.detect()
    ├── _validate_frame()          — dtype, ndim, finiteness
    ├── BackgroundSubtractor       — median_filter + white_tophat
    ├── ImageProcessor.blur()      — GaussianBlur (hot-pixel rejection)
    ├── threshold_and_label()      — MAD threshold + connectedComponents
    └── CentroidExtractor.extract()
            ├── weighted CoM (1-D marginal sums)
            └── uncertainty = psf_sigma / SNR
                        │
                        ▼
              TrackingResult (Pydantic, frozen)
                  detections: list[CentroidResult]
                  processing_time_ms: float
                  background_level_adu: float

BatchProcessor  ─── ProcessPoolExecutor ──► process_single_frame() × N workers
```

See [`docs/leo_tracker/PARALLELISATION.md`](docs/leo_tracker/PARALLELISATION.md)
for the measured speedup table and the rationale behind each design decision.

### CLI

```bash
# Generate 20 synthetic 512×512 frames
leo-tracker generate --n-frames 20 --output-dir frames/ --size 512 --seed 42

# Process frames in parallel (auto worker count)
leo-tracker process --input-dir frames/ --output results.json --workers 4
```

### Docker

```bash
# Build
docker build -t leo-tracker .

# Generate frames inside the container
docker run --rm -v $(pwd)/frames:/app/frames leo-tracker \
  generate --n-frames 10 --output-dir /app/frames

# Smoke-test the import
docker run --rm --entrypoint python leo-tracker \
  -c 'from leo_tracker import PipelineOrchestrator; print("ok")'
```

### Parallelisation benchmark (100 frames, 512×512, i9-12900K)

| Workers | Wall time (s) | Speedup |
|---------|--------------|---------|
| 1 | 12.4 | 1.0× |
| 4 | 3.4 | 3.6× |
| 8 | 2.1 | 5.9× |

Primary bottleneck: `scipy.ndimage.median_filter` (~68 % of single-frame time).
Mitigation path: `cv2.medianBlur` for small kernels or `cupy.ndimage.median_filter` on GPU.

---

## Installation

```bash
pip install uv
git clone https://github.com/kangkabseok2021/metrology_pipeline.git
cd metrology_pipeline
uv sync --extra dev
```

For GPU support (requires CUDA 12, enables JAX acceleration):

```bash
uv sync --extra gpu
```

---

## Tests

```bash
# All unit tests (excludes benchmark and gpu markers)
uv run pytest tests/ -v -m "not benchmark and not gpu"

# Benchmarks with JSON output
uv run pytest tests/benchmarks/ -v --benchmark-json=results.json

# Lint
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type check
uv run mypy src/ --strict
```

---

## CI

Five jobs run on every push to `main`:

| Job | What it does |
|-----|-------------|
| `lint` | `ruff check` + `ruff format --check` across `src/` and `tests/` |
| `typecheck` | `mypy src/ --strict` |
| `test` | `pytest` excluding `benchmark` and `gpu` markers |
| `benchmark` | `pytest tests/benchmarks/` — uploads JSON artifact |
| `docker-build` | Multi-stage Docker build + smoke-test `from leo_tracker import PipelineOrchestrator` |
