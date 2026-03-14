"""
Benchmark script for Differentiable Global Placer.

Runs case01-06 with both strategies (fixed, escalating),
10 random seeds each. Reports top-5 averages per (case, strategy).

Usage:
    python benchmark.py                     # Full benchmark
    python benchmark.py --gif               # Also generate case06 GIF
    python benchmark.py --cases 1 6         # Only case01 and case06
    python benchmark.py --seeds 5           # Use 5 seeds instead of 10
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import torch

from src.config import get_preset
from src.metrics import (
    calculate_boundary_violation,
    calculate_hpwl,
    calculate_total_overlap,
    check_aspect_ratios,
)
from src.model import NormalizedFloorplanner
from src.parser import parse_file
from src.trainer import train
from src.visualizer import save_video


def run_single(
    case_path: str,
    strategy: str,
    seed: int,
    iterations: int,
    device: torch.device,
    quiet: bool = True,
):
    """Run a single (case, strategy, seed) and return metrics dict."""
    data = parse_file(case_path)
    config = get_preset(strategy)
    config.iterations = iterations
    config.seed = seed

    torch.manual_seed(seed)
    model = NormalizedFloorplanner(
        data.chip_w,
        data.chip_h,
        data.soft_modules,
        data.fixed_modules,
        data.nets,
    )

    if quiet:
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            t0 = time.time()
            history = train(model, config, device)
            elapsed = time.time() - t0
    else:
        t0 = time.time()
        history = train(model, config, device)
        elapsed = time.time() - t0

    hpwl = calculate_hpwl(model, data.nets)
    overlap = calculate_total_overlap(model)
    boundary = calculate_boundary_violation(model)
    ar_results = check_aspect_ratios(model)
    ar_viols = sum(1 for r in ar_results if not r["valid"])

    chip_area = data.chip_w * data.chip_h
    overlap_ratio = overlap / chip_area * 100

    return {
        "hpwl": hpwl,
        "overlap": overlap,
        "overlap_ratio": overlap_ratio,
        "boundary_total": boundary["total"],
        "boundary_max": boundary["max"],
        "ar_violations": ar_viols,
        "elapsed": elapsed,
        "history": history,
        "model": model,
        "data": data,
    }


def select_top_k(results: list, k: int = 5) -> list:
    """Select top-k runs by lowest HPWL (among legal solutions first)."""
    ranked = sorted(results, key=lambda r: (r["overlap"] >= 1.0, r["hpwl"]))
    return ranked[:k]


def average_metrics(results: list) -> dict:
    """Compute average metrics from a list of run results."""
    keys = [
        "hpwl",
        "overlap",
        "overlap_ratio",
        "boundary_total",
        "ar_violations",
        "elapsed",
    ]
    avg = {}
    for key in keys:
        avg[key] = np.mean([r[key] for r in results])
    avg["best_hpwl"] = min(r["hpwl"] for r in results)
    avg["legal_count"] = sum(1 for r in results if r["overlap"] < 1.0)
    avg["total_count"] = len(results)
    return avg


def main():
    parser = argparse.ArgumentParser(description="Benchmark all cases")
    parser.add_argument(
        "--cases",
        nargs="+",
        type=int,
        default=[1, 2, 3, 4, 5, 6],
        help="Case numbers to run (default: 1 2 3 4 5 6)",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["escalating", "fixed"],
        help="Strategies to benchmark (default: escalating fixed)",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=10,
        help="Number of random seeds (default: 10)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Keep top-k results for averaging (default: 5)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=2000,
        help="Training iterations (default: 2000)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cpu", "cuda"],
        help="Force device (default: auto)",
    )
    parser.add_argument(
        "--gif",
        action="store_true",
        help="Generate case06 GIF (saved to assets/case06_demo.gif)",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Save raw results to JSON file",
    )
    args = parser.parse_args()

    if args.device:
        device = torch.device(args.device)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    seed_list = list(range(42, 42 + args.seeds))

    print("=" * 62)
    print("  Differentiable Global Placer - Benchmark")
    print("=" * 62)
    print(f"  Cases      : {args.cases}")
    print(f"  Strategies : {args.strategies}")
    print(f"  Seeds      : {args.seeds} (top {args.top_k} averaged)")
    print(f"  Iterations : {args.iterations}")
    print(f"  Device     : {device}")
    print("=" * 62)
    print()

    all_summaries = []
    best_case06 = None

    for case_num in args.cases:
        case_path = f"data/case{case_num:02d}-input.txt"
        if not os.path.exists(case_path):
            print(f"  [SKIP] {case_path} not found")
            continue

        for strategy in args.strategies:
            print(f"-- case{case_num:02d} / {strategy} --")
            results = []
            for si, seed in enumerate(seed_list):
                sys.stdout.write(f"\r  Running seed {si + 1}/{args.seeds} (seed={seed}) ...")
                sys.stdout.flush()
                result = run_single(case_path, strategy, seed, args.iterations, device)
                results.append(result)
            print()

            top = select_top_k(results, args.top_k)
            avg = average_metrics(top)
            avg["case"] = f"case{case_num:02d}"
            avg["strategy"] = strategy
            all_summaries.append(avg)

            if case_num == 6 and strategy == "fixed" and args.gif:
                best_run = top[0]
                if best_case06 is None or best_run["hpwl"] < best_case06["hpwl"]:
                    best_case06 = best_run

            print(
                f"  Top-{args.top_k} avg HPWL: {avg['hpwl']:,.0f}  |  "
                f"Overlap: {avg['overlap']:.1f} ({avg['overlap_ratio']:.3f}%)  |  "
                f"Time: {avg['elapsed']:.2f}s  |  "
                f"Legal: {avg['legal_count']}/{avg['total_count']}"
            )
            print()

    # Output Markdown table

    print()
    print("=" * 80)
    print("  MARKDOWN TABLE  (copy-paste into README.md)")
    print("=" * 80)
    print()
    print(
        "| Case | Strategy | Avg HPWL | Best HPWL | Overlap Ratio | "
        "Boundary Viol | AR Viols | Avg Time (s) | Legal |"
    )
    print(
        "|------|----------|----------|-----------|---------------|"
        "--------------|----------|--------------|-------|"
    )
    for summary in all_summaries:
        legal_str = f"{summary['legal_count']}/{summary['total_count']}"
        print(
            f"| {summary['case']} | {summary['strategy']:10s} "
            f"| {summary['hpwl']:>10,.0f} "
            f"| {summary['best_hpwl']:>10,.0f} "
            f"| {summary['overlap_ratio']:>12.4f}% "
            f"| {summary['boundary_total']:>12.1f} "
            f"| {summary['ar_violations']:>8.1f} "
            f"| {summary['elapsed']:>12.2f} "
            f"| {legal_str:>5s} |"
        )
    print()

    # Generate GIF

    if args.gif and best_case06 is not None:
        os.makedirs("assets", exist_ok=True)
        gif_path = "assets/case06_demo.gif"
        print(f"Generating GIF from best case06 run -> {gif_path}")
        save_video(
            best_case06["history"],
            best_case06["model"],
            best_case06["data"].chip_w,
            best_case06["data"].chip_h,
            best_case06["data"].nets,
            filepath=gif_path,
            fps=15,
        )
        print(f"GIF saved to {gif_path}")

    if args.json:
        json_data = []
        for summary in all_summaries:
            json_data.append(
                {
                    "case": summary["case"],
                    "strategy": summary["strategy"],
                    "avg_hpwl": summary["hpwl"],
                    "best_hpwl": summary["best_hpwl"],
                    "avg_overlap_ratio": summary["overlap_ratio"],
                    "avg_boundary": summary["boundary_total"],
                    "avg_ar_violations": summary["ar_violations"],
                    "avg_elapsed": summary["elapsed"],
                    "legal_count": summary["legal_count"],
                    "total_count": summary["total_count"],
                }
            )
        with open(args.json, "w") as f:
            json.dump(json_data, f, indent=2)
        print(f"Raw results saved to {args.json}")

    print("\nDone!")


if __name__ == "__main__":
    main()
