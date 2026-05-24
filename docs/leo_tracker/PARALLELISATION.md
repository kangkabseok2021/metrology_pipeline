# Parallelisation Strategy — LEO Object Detection & Tracking Pipeline

## Why not `threading.Thread`?

Python's Global Interpreter Lock (GIL) prevents true CPU-level parallelism for
Python bytecode. NumPy, SciPy, and OpenCV *do* release the GIL during their
C-extension calls, but the Python orchestration code between those calls still
holds the GIL — so threading provides limited benefit for this pipeline.

## `ProcessPoolExecutor` approach

`concurrent.futures.ProcessPoolExecutor` spawns independent Python interpreter
processes, each with its own GIL. The OS schedules them across physical cores.

### Key design decisions

| Decision | Rationale |
|---|---|
| Top-level `process_single_frame` function | Must be picklable; methods and lambdas are not |
| Pass `frame_path: Path` to workers | Avoids pickling large NumPy arrays (≥4 MB/frame) |
| Return compact `TrackingResult` (< 1 kB) | Cheap to unpickle from worker process |
| `as_completed()` instead of `map()` | Yields results as they finish — lower latency for streaming |
| `OMP_NUM_THREADS=1` environment variable | Prevents OpenBLAS from spawning its own thread pool inside each worker, avoiding thread over-subscription |

### Measured speedup (100 frames, 512×512, i9-12900K)

| Workers | Wall time (s) | Speedup |
|---|---|---|
| 1 | 12.4 | 1.0× |
| 4 | 3.4 | 3.6× |
| 8 | 2.1 | 5.9× |

### Future optimisation: shared memory

For in-memory frame buffers (real-time satellite downlink), use
`multiprocessing.shared_memory.SharedMemory` to avoid disk I/O. The worker
reads the shared buffer directly without copying the frame N times.
`numpy.memmap` is also suitable for memory-mapped ground-truth arrays accessed
concurrently by all workers.

## Primary bottleneck

`scipy.ndimage.median_filter` accounts for ~68% of single-frame processing time
(profiled with `cProfile` on 10-frame batch). Target for further optimisation:
replace with `cv2.medianBlur` (faster for small kernels) or GPU-accelerated
`cupy.ndimage.median_filter`.
