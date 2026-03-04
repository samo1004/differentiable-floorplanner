"""
Differentiable Global Placer — CLI Entry Point

Usage:
    python main.py --case data/case01-input.txt
    python main.py --case data/case01-input.txt --strategy escalating
    python main.py --case data/case06-input.txt --strategy fixed --no-animation
    python main.py --case data/case01-input.txt --save-video result.gif
    python main.py --case data/case01-input.txt --iterations 5000 --seed 123
"""

import argparse
import time
import torch

from src.parser import parse_file
from src.config import get_preset, TrainingConfig
from src.model import NormalizedFloorplanner
from src.trainer import train
from src.metrics import print_report
from src.visualizer import create_animation, save_static_plot, save_video


def main():
    parser = argparse.ArgumentParser(
        description="Differentiable Global Placer for ICCAD 2023 Problem D",
    )
    parser.add_argument(
        "--case", type=str, required=True,
        help="Path to input file (e.g. data/case01-input.txt)",
    )
    parser.add_argument(
        "--strategy", type=str, default="escalating",
        choices=["fixed", "escalating"],
        help="Lock-phase strategy: 'fixed' (test2) or 'escalating' (test3, default)",
    )
    parser.add_argument(
        "--iterations", type=int, default=2000,
        help="Number of training iterations (default: 2000)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--no-animation", action="store_true",
        help="Skip interactive animation; only print report",
    )
    parser.add_argument(
        "--save-plot", type=str, default=None,
        help="Save final layout to this PNG path (e.g. result.png)",
    )
    parser.add_argument(
        "--save-video", type=str, default=None,
        help="Save training animation to file (.mp4 requires ffmpeg, .gif requires Pillow)",
    )
    parser.add_argument(
        "--device", type=str, default=None, choices=["cpu", "cuda"],
        help="Force device (default: auto-detect CUDA)",
    )
    args = parser.parse_args()

    # Seed
    torch.manual_seed(args.seed)

    # Device
    if args.device:
        device = torch.device(args.device)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Parse input
    data = parse_file(args.case)
    print(f"Case: {args.case}")
    print(f"  Chip: {data.chip_w} × {data.chip_h}")
    print(f"  Soft modules: {len(data.soft_modules)}  |  "
          f"Fixed modules: {len(data.fixed_modules)}  |  "
          f"Nets: {len(data.nets)}")
    print()

    # Config
    config = get_preset(args.strategy)
    config.iterations = args.iterations
    config.seed = args.seed

    # Model
    model = NormalizedFloorplanner(
        data.chip_w, data.chip_h,
        data.soft_modules, data.fixed_modules, data.nets,
    )

    # Train
    t0 = time.time()
    history = train(model, config, device)
    elapsed = time.time() - t0

    # Report
    print()
    metrics = print_report(model, data.nets, elapsed_sec=elapsed)

    # Save static plot
    if args.save_plot:
        save_static_plot(model, data.chip_w, data.chip_h, data.nets, args.save_plot)

    # Save video
    if args.save_video:
        save_video(history, model, data.chip_w, data.chip_h, data.nets, args.save_video)

    # Animation
    if not args.no_animation:
        create_animation(history, model, data.chip_w, data.chip_h, data.nets)


if __name__ == "__main__":
    main()
