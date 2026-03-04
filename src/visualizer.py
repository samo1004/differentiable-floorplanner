"""
Visualization utilities for the differentiable global placer.

Provides:
  - create_animation(): interactive matplotlib animation of training.
  - save_static_plot(): save the final layout as a PNG image.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
from typing import List, Dict, Any, Tuple

from .model import NormalizedFloorplanner


def create_animation(
    history: List[Dict[str, Any]],
    model: NormalizedFloorplanner,
    chip_w: int,
    chip_h: int,
    nets: List[Tuple[str, str, int]],
) -> None:
    """Play a matplotlib animation of the training process."""
    print("Generating animation...")

    fig, ax = plt.subplots(figsize=(10, 10))
    scale = model.scale_factor
    mod_names = model.mod_names
    name2idx = {name: i for i, name in enumerate(mod_names)}
    colors = ['#5da5da'] * model.num_soft + ['#b0b0b0'] * model.num_fixed

    def update(frame_idx):
        ax.clear()
        ax.set_xlim(-chip_w * 0.05, chip_w * 1.05)
        ax.set_ylim(-chip_h * 0.05, chip_h * 1.05)
        ax.set_aspect('equal')

        data = history[frame_idx]
        step, phase, rects, loss = data['step'], data['phase'], data['rects'], data['loss']
        ax.set_title(f"Step: {step}  |  Phase: {phase}\nLoss: {loss:.2f}", fontsize=13)

        # Chip outline
        chip_rect = patches.Rectangle(
            (0, 0), chip_w, chip_h,
            linewidth=2, edgecolor='red', facecolor='none', linestyle='--',
        )
        ax.add_patch(chip_rect)

        # Nets
        for m1, m2, weight in nets:
            if m1 in name2idx and m2 in name2idx:
                p1 = rects[name2idx[m1], :2] * scale
                p2 = rects[name2idx[m2], :2] * scale
                ax.plot(
                    [p1[0], p2[0]], [p1[1], p2[1]],
                    color='green', linewidth=0.5, alpha=0.2,
                )

        # Modules
        for i, (ncx, ncy, nw, nh) in enumerate(rects):
            real_cx, real_cy = ncx * scale, ncy * scale
            real_w, real_h = nw * scale, nh * scale
            lx = real_cx - real_w / 2.0
            ly = real_cy - real_h / 2.0
            alpha = 0.4 if phase == "Ghost" else 0.85
            rect = patches.Rectangle(
                (lx, ly), real_w, real_h,
                linewidth=1, edgecolor='black', facecolor=colors[i], alpha=alpha,
            )
            ax.add_patch(rect)
            ax.text(
                real_cx, real_cy, mod_names[i],
                ha='center', va='center', fontsize=7, clip_on=True,
            )

    ani = animation.FuncAnimation(
        fig, update, frames=len(history), interval=50, repeat=False,
    )
    plt.tight_layout()
    plt.show()


def save_video(
    history: List[Dict[str, Any]],
    model: NormalizedFloorplanner,
    chip_w: int,
    chip_h: int,
    nets: List[Tuple[str, str, int]],
    filepath: str = "floorplan_animation.mp4",
    fps: int = 20,
) -> None:
    """Save the training animation as a video file (.mp4 or .gif).

    For .mp4: requires ffmpeg installed on the system.
    For .gif: requires Pillow (pip install Pillow).

    Args:
        filepath: Output path. Extension determines format (.mp4 or .gif).
        fps: Frames per second (default: 20).
    """
    import os
    print(f"Rendering video ({len(history)} frames) → {filepath} ...")

    fig, ax = plt.subplots(figsize=(10, 10))
    scale = model.scale_factor
    mod_names = model.mod_names
    name2idx = {name: i for i, name in enumerate(mod_names)}
    colors = ['#5da5da'] * model.num_soft + ['#b0b0b0'] * model.num_fixed

    def update(frame_idx):
        ax.clear()
        ax.set_xlim(-chip_w * 0.05, chip_w * 1.05)
        ax.set_ylim(-chip_h * 0.05, chip_h * 1.05)
        ax.set_aspect('equal')

        data = history[frame_idx]
        step, phase, rects, loss = data['step'], data['phase'], data['rects'], data['loss']
        ax.set_title(f"Step: {step}  |  Phase: {phase}\nLoss: {loss:.2f}", fontsize=13)

        chip_rect = patches.Rectangle(
            (0, 0), chip_w, chip_h,
            linewidth=2, edgecolor='red', facecolor='none', linestyle='--',
        )
        ax.add_patch(chip_rect)

        for m1, m2, weight in nets:
            if m1 in name2idx and m2 in name2idx:
                p1 = rects[name2idx[m1], :2] * scale
                p2 = rects[name2idx[m2], :2] * scale
                ax.plot(
                    [p1[0], p2[0]], [p1[1], p2[1]],
                    color='green', linewidth=0.5, alpha=0.2,
                )

        for i, (ncx, ncy, nw, nh) in enumerate(rects):
            real_cx, real_cy = ncx * scale, ncy * scale
            real_w, real_h = nw * scale, nh * scale
            lx = real_cx - real_w / 2.0
            ly = real_cy - real_h / 2.0
            alpha = 0.4 if phase == "Ghost" else 0.85
            rect = patches.Rectangle(
                (lx, ly), real_w, real_h,
                linewidth=1, edgecolor='black', facecolor=colors[i], alpha=alpha,
            )
            ax.add_patch(rect)
            ax.text(
                real_cx, real_cy, mod_names[i],
                ha='center', va='center', fontsize=7, clip_on=True,
            )

    ani = animation.FuncAnimation(
        fig, update, frames=len(history), interval=1000 // fps, repeat=False,
    )
    plt.tight_layout()

    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.gif':
        ani.save(filepath, writer='pillow', fps=fps)
    else:
        ani.save(filepath, writer='ffmpeg', fps=fps)

    plt.close(fig)
    print(f"Saved video → {filepath}")


def save_static_plot(
    model: NormalizedFloorplanner,
    chip_w: int,
    chip_h: int,
    nets: List[Tuple[str, str, int]],
    filepath: str = "floorplan_result.png",
) -> None:
    """Save the final floorplan layout as a PNG image."""
    fig, ax = plt.subplots(figsize=(10, 10))
    scale = model.scale_factor
    rects = model.get_norm_rects().detach().cpu().numpy()
    mod_names = model.mod_names
    name2idx = {name: i for i, name in enumerate(mod_names)}

    ax.set_xlim(-chip_w * 0.05, chip_w * 1.05)
    ax.set_ylim(-chip_h * 0.05, chip_h * 1.05)
    ax.set_aspect('equal')
    ax.set_title("Final Floorplan Layout", fontsize=14)

    # Chip outline
    chip_rect = patches.Rectangle(
        (0, 0), chip_w, chip_h,
        linewidth=2, edgecolor='red', facecolor='none', linestyle='--',
    )
    ax.add_patch(chip_rect)

    # Nets
    for m1, m2, weight in nets:
        if m1 in name2idx and m2 in name2idx:
            p1 = rects[name2idx[m1], :2] * scale
            p2 = rects[name2idx[m2], :2] * scale
            ax.plot(
                [p1[0], p2[0]], [p1[1], p2[1]],
                color='green', linewidth=0.5, alpha=0.15,
            )

    # Modules
    colors = ['#5da5da'] * model.num_soft + ['#b0b0b0'] * model.num_fixed
    for i, (ncx, ncy, nw, nh) in enumerate(rects):
        real_cx, real_cy = ncx * scale, ncy * scale
        real_w, real_h = nw * scale, nh * scale
        lx = real_cx - real_w / 2.0
        ly = real_cy - real_h / 2.0
        rect = patches.Rectangle(
            (lx, ly), real_w, real_h,
            linewidth=1, edgecolor='black', facecolor=colors[i], alpha=0.85,
        )
        ax.add_patch(rect)
        ax.text(
            real_cx, real_cy, mod_names[i],
            ha='center', va='center', fontsize=7, clip_on=True,
        )

    plt.tight_layout()
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved static plot → {filepath}")
