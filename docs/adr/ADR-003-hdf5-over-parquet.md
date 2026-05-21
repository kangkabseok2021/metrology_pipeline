# ADR-003: HDF5 over Parquet for wafer scan storage

**Status:** Accepted  
**Date:** 2026-05-21  
**Deciders:** Core team

## Context

Wafer height maps are 2-D (or higher-dimensional) floating-point arrays, potentially 4096×4096 or larger. The storage format must support: efficient random access to sub-regions, multi-dataset files (height map + defect table + metadata), and cross-language interoperability (Python, C++, MATLAB).

## Decision

Use HDF5 (via `h5py`) as the file format for wafer scan data.

## Rationale

1. **N-dimensional array support.** HDF5 natively stores arbitrary n-D typed arrays with named datasets. Parquet is columnar and optimised for 1-D tabular data; representing a 4096×4096 float32 matrix requires either flattening or per-row storage, both of which are inefficient.
2. **Efficient partial reads via chunking.** HDF5 datasets are chunked; a `(256, 256)` chunk layout allows reading a small region of interest without loading the entire file into memory. Parquet supports row-group skipping but not 2-D spatial partitioning.
3. **Scientific computing standard.** HDF5 is the default output format for electron-beam inspection tools (e.g., KLA, Hitachi) and is supported natively by NumPy, SciPy, MATLAB, and LabVIEW with no conversion step.
4. **Compound datasets.** The defect table (integer coords + float depths) is stored as a NumPy structured array in a single `scan/defects` dataset alongside the height map — no separate file or sidecar JSON required.
5. **Built-in GZIP compression.** `h5py` supports transparent GZIP compression per dataset with no serialisation code changes, reducing storage for smooth height maps by 3–5x.

## Consequences

- HDF5 files are binary; diffs are not human-readable. A `hdf5_to_json` utility should be added to the `tools/` directory for debugging.
- `h5py` must be linked against a compatible HDF5 C library. The pip wheel bundles a static HDF5 build, so no system dependency is required.
- Concurrent writes require HDF5 built with MPI support (not needed for this use case).
