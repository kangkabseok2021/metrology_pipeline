# metrology-pipeline

[![CI](https://github.com/kangkabseok2021/metrology_pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/kangkabseok2021/metrology_pipeline/actions/workflows/ci.yml)

Five projects sharing the theme of **scientific measurement pipelines** — from wafer inspection and satellite tracking to LC-MS metabolomics and automotive analytics:

| Project | Language(s) | Domain |
|---------|-------------|--------|
| [`metrology_pipeline`](#metrology_pipeline) | Python / JAX | GPU-accelerated semiconductor wafer inspection |
| [`leo_tracker`](#leo_tracker) | Python / SciPy | LEO satellite detection and sub-pixel centroiding |
| [`analytics_pipeline_dq_engine`](#analytics_pipeline_dq_engine) | Python / dbt / SQL | ELT data quality pipeline with Great Expectations |
| [`automotive_telemetry_warehouse`](#automotive_telemetry_warehouse) | Python / PySpark / Airflow | Automotive sensor data warehouse (Kimball star schema) |
| [`metabo_pipe`](#metabo_pipe) | Python · R · Java 21 | LC-MS metabolomics feature extraction, annotation & multi-omics integration |

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

## analytics_pipeline_dq_engine

Enterprise ELT pipeline with deliberate data-quality faults and automated remediation gates.

### What it does

- **Synthetic generation** — 25 000 supply-chain rows seeded with 5 % nulls, 2 % negative costs, 3 % duplicates, whitespace typos and mixed date formats.
- **Bronze load** — Pandas + SQLAlchemy 2.0 bulk insert into PostgreSQL `bronze.raw_shipments`.
- **dbt Silver/Gold** — Kimball star schema (`fact_shipments`, `dim_locations`, `dim_dates`, `dim_products`) with surrogate keys from `dbt-utils`; `not_null`, `unique`, `relationships`, `accepted_values` + 2 custom singular tests.
- **Great Expectations Z-score gate** — flags shipping-cost batches where `|Z| = |(x − μ) / σ| > 3`.
- **11 pytest tests** — generator statistics (4), Bronze load (3), Z-score formula correctness, GE suite pass/fail (4).

---

## automotive_telemetry_warehouse

Streaming automotive sensor warehouse that ingests simulated vehicle telemetry and exposes it via a REST API and Airflow DAG.

### What it does

- **Telemetry generation** — configurable-row synthetic vehicle sensor CSV (speed, RPM, fuel, GPS).
- **Schema** — PostgreSQL star schema with BRIN + B-tree indexes benchmarked against a 10 M-row dataset.
- **FastAPI REST** — `/health`, `/metrics/latest`, `/metrics/aggregate` endpoints with pytest-postgresql integration tests.
- **Airflow DAG** — scheduled ingestion and anomaly detection DAG with syntax-validated CI gate.
- **Docker Compose** — full stack (Postgres + FastAPI + Airflow) with `docker compose config` validation in CI.
- **Kubernetes manifests** — Deployment, Service, ConfigMap with pytest YAML schema validation.

---

## metabo_pipe

LC-MS metabolomics pipeline: raw instrument data in, statistically-supported annotated multi-omics feature tables out.

### What it does

**Phase 1 — Python feature extraction** (`metabo_pipe/python/`)

- **`MzmlReader`** — streams MS1 spectra from mzML files via pyteomics without loading full runs into memory; builds extracted-ion chromatograms (EICs) per target m/z within a configurable ppm window.
- **`FeatureDetector`** — centWave-style CWT peak picker (manual Ricker wavelet convolution; `scipy.signal.cwt` removed in SciPy 1.12); refines apex RT and integrates peak area via trapezoidal quadrature.
- **`RTAligner`** — LOESS regression (statsmodels) against a reference run corrects between-run retention-time drift; reports median |ΔRT| before/after.
- **`FeatureMatrixBuilder`** — union-find clustering within (m/z ppm × RT seconds) tolerance windows collapses aligned peaks into a consensus samples × features intensity matrix.

**Phase 2 — Annotation** (`metabo_pipe/python/metabopipe/annotation.py`)

- **`FormulaPredictor`** — enumerates C/H/N/O candidate formulae within ppm tolerance; filters by RDBE ≥ 0 valence rule; sorts by mass error.
- **`IsotopeScorer`** — chi-squared fit of observed M, M+1, M+2 relative intensities against theoretical isotopologue distributions re-ranks formula candidates.
- **`SpectralMatcher`** — cosine similarity against MSP/GNPS reference library with configurable m/z bin width; reports matched-peak count.
- **`assign_schymanski_level`** — assigns confidence levels 1–5 based on available evidence (reference standard → library match → tentative → formula only → unknown).

**Phase 3 — R statistics** (`metabo_pipe/stats/`)

| Script | Analysis |
|--------|----------|
| `pca.R` | `stats::prcomp` on log-transformed autoscaled matrix; score plot + scree plot (ggplot2) |
| `plsda.R` | `mixOmics::plsda` group-discrimination model; VIP scores ranked to `vip_scores.csv` |
| `univariate.R` | Welch `t.test` (2 groups) or `aov` (>2); `p.adjust(method="BH")`; volcano plot + pheatmap of significant features |

**Phase 4 — Java 21 multi-omics integration service** (`metabo_pipe/service/`)

- **Spring Boot 3.3** REST service with Flyway-managed PostgreSQL schema (tidy long format: one row per sample × feature × omics layer).
- **`OmicsImportService`** — idempotent CSV import via `POST /api/import/{metabolomics|transcriptomics|proteomics}`; registers samples and features on first sight.
- **`CorrelationNetworkService`** — pairwise Pearson correlation (Apache Commons Math) between metabolomics and transcriptomics/proteomics features per sample group; t-distribution p-value; persists edges above configurable |r| and p thresholds.
- **`GET /api/network/{sampleGroup}`** — Cytoscape-ready node/edge JSON graph for downstream visualisation.
- **Testcontainers** PostgreSQL JUnit tests for import idempotency and network edge detection.

### Architecture

```
mzML files (LC-MS instrument output)
        │
        ▼
MzmlReader  ──────────────────────────────────────────── pyteomics / psims
        │  stream MS1 spectra → EIC per target m/z
        ▼
FeatureDetector (CWT Ricker)  ────────────────────────── scipy.signal
        │  chromatographic peaks (apex RT, area, intensity)
        ▼
RTAligner (LOESS)  ────────────────────────────────────── statsmodels
        │  drift-corrected peaks aligned to reference run
        ▼
FeatureMatrixBuilder (union-find)  ─────────────────────── pandas / numpy
        │  samples × features intensity matrix  →  feature_matrix.csv
        ├──────────────────────────────────────────────────────────────┐
        ▼                                                              ▼
FormulaPredictor + IsotopeScorer + SpectralMatcher         Rscript run_analysis.R
        │  annotations.csv (formula, ppm, Schymanski)        │  pca_scores.csv
        │                                                     │  vip_scores.csv
        └────────────────────────────────────────────────     │  univariate_results.csv
                                                         ▼    ▼
                                              Spring Boot OmicsImportController
                                                     │  POST /api/import/…
                                                     ▼
                                              PostgreSQL (Flyway schema)
                                              Sample / OmicsFeature / OmicsFeatureValue
                                                     │
                                                     ▼
                                              CorrelationNetworkService
                                              Pearson |r| ≥ 0.7, p < 0.05
                                                     │
                                                     ▼
                                              GET /api/network/{sampleGroup}
                                              → {nodes: […], edges: […]}
```

### Tests

```bash
# Python — 27 pytest
cd metabo_pipe/python
uv sync --group dev
uv run pytest tests/ -v

# R — 9 testthat
Rscript -e 'testthat::test_dir("metabo_pipe/stats/tests")'

# Java — Maven / JUnit (Testcontainers PostgreSQL)
cd metabo_pipe/service
mvn test
```

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

Ten jobs run on every push to `main`:

| Job | What it does |
|-----|-------------|
| `lint` | `ruff check` + `ruff format --check` across `src/` and `tests/` |
| `typecheck` | `mypy src/ --strict` |
| `test` | `pytest` excluding `benchmark` and `gpu` markers |
| `benchmark` | `pytest tests/benchmarks/` — uploads JSON artifact |
| `docker-build` | Multi-stage Docker build + smoke-test `from leo_tracker import PipelineOrchestrator` |
| `dq-pipeline` | Analytics DQ — 7 offline pytest + dbt Star Schema run + Great Expectations Z-score gate (PostgreSQL service container) |
| `telemetry-warehouse` | Automotive warehouse — lint + offline + pytest-postgresql + docker compose config + K8s YAML + Airflow DAG syntax |
| `metabo-pipe-python` | MetaboPipe Python — 27 pytest (mzML reader, CWT peak detection, LOESS alignment, formula prediction, cosine spectral matching) |
| `metabo-pipe-r` | MetaboPipe R — 9 testthat (PCA variance, BH-FDR, volcano plot, injected-signal significance) |
| `metabo-pipe-java` | MetaboPipe Java — Spring Boot 3.3 / JUnit / Testcontainers PostgreSQL (import idempotency, Pearson network edges) |
