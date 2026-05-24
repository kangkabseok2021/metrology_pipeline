"""Command-line interface for the LEO tracker pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    """Entry point: leo-tracker CLI."""
    parser = argparse.ArgumentParser(
        prog="leo-tracker",
        description="LEO Object Detection & Tracking Pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen_p = sub.add_parser("generate", help="Generate synthetic sensor frames")
    gen_p.add_argument(
        "--n-frames", type=int, default=10, help="Number of frames to generate"
    )
    gen_p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("frames"),
        help="Output directory",
    )
    gen_p.add_argument("--size", type=int, default=512, help="Frame size in pixels")
    gen_p.add_argument("--seed", type=int, default=42, help="Base random seed")

    proc_p = sub.add_parser("process", help="Process a directory of frames")
    proc_p.add_argument(
        "--input-dir",
        type=Path,
        default=Path("frames"),
        help="Input frame directory",
    )
    proc_p.add_argument(
        "--output",
        type=Path,
        default=Path("results.json"),
        help="Output JSON path",
    )
    proc_p.add_argument(
        "--workers", type=int, default=None, help="Number of worker processes"
    )

    args = parser.parse_args()

    if args.command == "generate":
        _cmd_generate(args)
    elif args.command == "process":
        _cmd_process(args)


def _cmd_generate(args: argparse.Namespace) -> None:
    """Generate synthetic sensor frames."""
    import numpy as np

    from .generator import SyntheticImageGenerator
    from .models import GeneratorConfig

    args.output_dir.mkdir(parents=True, exist_ok=True)
    gen = SyntheticImageGenerator()
    for i in range(args.n_frames):
        cfg = GeneratorConfig(size=args.size, seed=args.seed + i)
        frame, (cx, cy) = gen.generate(cfg)
        path = args.output_dir / f"frame_{i:04d}.npy"
        np.save(path, frame)
        print(f"  {path}  gt_centroid=({cx:.2f}, {cy:.2f})")
    print(f"Generated {args.n_frames} frames in {args.output_dir}/")


def _cmd_process(args: argparse.Namespace) -> None:
    """Process frames from a directory."""
    import json

    from .executor import BatchProcessor

    frame_paths = sorted(args.input_dir.glob("*.npy"))
    if not frame_paths:
        print(f"No .npy frames found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    workers_label = args.workers or "auto"
    print(f"Processing {len(frame_paths)} frames with {workers_label} workers...")
    proc = BatchProcessor()
    batch = proc.run(frame_paths, max_workers=args.workers)
    total_detections = sum(len(r.detections) for r in batch.results)
    output_data = [json.loads(r.model_dump_json()) for r in batch.results]
    args.output.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(
        f"Done: {batch.success_count} ok, {batch.failure_count} failed, "
        f"{total_detections} detections -> {args.output}"
    )


if __name__ == "__main__":
    main()
