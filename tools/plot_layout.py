#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0


def overlap_rect(a: Rect, b: Rect) -> Rect | None:
    """Return intersection rect if positive-area overlap exists."""
    ix1 = max(a.x, b.x)
    iy1 = max(a.y, b.y)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    iw = ix2 - ix1
    ih = iy2 - iy1
    if iw > 0 and ih > 0:
        return Rect(ix1, iy1, iw, ih)
    return None


def parse_case_input(path: str):
    """
    Format (from your parser.cpp):
      CHIP W H
      SOFTMODULE n
        name min_area
      FIXEDMODULE m
        name x y w h
      CONNECTION k
        a b w
    """
    p = Path(path)
    toks = p.read_text(encoding="utf-8").split()

    it = iter(toks)
    def next_tok():
        try:
            return next(it)
        except StopIteration:
            raise RuntimeError(f"ParseError: unexpected EOF in {path}")

    tag = next_tok()
    if tag != "CHIP":
        raise RuntimeError(f"ParseError: expected CHIP but got {tag}")
    chip_w = int(next_tok())
    chip_h = int(next_tok())

    tag = next_tok()
    if tag != "SOFTMODULE":
        raise RuntimeError(f"ParseError: expected SOFTMODULE but got {tag}")
    n_soft = int(next_tok())
    soft_names: List[str] = []
    soft_min_area: Dict[str, int] = {}
    for _ in range(n_soft):
        name = next_tok()
        area = int(next_tok())
        soft_names.append(name)
        soft_min_area[name] = area

    tag = next_tok()
    if tag != "FIXEDMODULE":
        raise RuntimeError(f"ParseError: expected FIXEDMODULE but got {tag}")
    n_fixed = int(next_tok())
    fixed_rects: Dict[str, Rect] = {}
    for _ in range(n_fixed):
        name = next_tok()
        x = int(next_tok()); y = int(next_tok()); w = int(next_tok()); h = int(next_tok())
        fixed_rects[name] = Rect(x, y, w, h)

    tag = next_tok()
    if tag != "CONNECTION":
        raise RuntimeError(f"ParseError: expected CONNECTION but got {tag}")
    k = int(next_tok())

    edges: List[Tuple[str, str, int]] = []
    for _ in range(k):
        a = next_tok()
        b = next_tok()
        w = int(next_tok())
        if a != b:
            edges.append((a, b, w))

    return chip_w, chip_h, soft_names, fixed_rects, edges


def parse_output(out_path: str):
    """
    Output format (your writer):
      HPWL <value>
      SOFTMODULE <n>
      <soft_name> <num_corners>
      x y
      x y
      ...
    We'll treat modules as rectangles using min/max of corners.
    """
    p = Path(out_path)
    toks = p.read_text(encoding="utf-8").split()
    it = iter(toks)

    def next_tok():
        try:
            return next(it)
        except StopIteration:
            raise RuntimeError(f"ParseError: unexpected EOF in {out_path}")

    tag = next_tok()
    if tag != "HPWL":
        raise RuntimeError(f"ParseError: expected HPWL but got {tag}")
    hpwl = float(next_tok())

    tag = next_tok()
    if tag != "SOFTMODULE":
        raise RuntimeError(f"ParseError: expected SOFTMODULE but got {tag}")
    n = int(next_tok())

    soft_rects: Dict[str, Rect] = {}

    for _ in range(n):
        name = next_tok()
        nc = int(next_tok())
        xs, ys = [], []
        for _ in range(nc):
            x = int(next_tok()); y = int(next_tok())
            xs.append(x); ys.append(y)
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        soft_rects[name] = Rect(x1, y1, x2 - x1, y2 - y1)

    return hpwl, soft_rects


def choose_grid_step(w: int, h: int) -> int:
    # Aim for ~20 grids each axis
    base = max(w, h) / 20.0
    if base <= 0:
        return 1
    # Round to a "nice" step
    nice = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
    for s in nice:
        if s >= base:
            return s
    return nice[-1]


def plot_layout(case_path: str, out_path: str, save_path: str | None,
                max_edges: int, show_labels: bool, show: bool, grid_step: int | None):
    chip_w, chip_h, soft_names, fixed_rects, edges = parse_case_input(case_path)
    hpwl, soft_rects = parse_output(out_path)

    # Combine for drawing nets (fixed + soft)
    all_rects: Dict[str, Rect] = {}
    all_rects.update(fixed_rects)
    all_rects.update(soft_rects)

    fig, ax = plt.subplots(figsize=(10, 9))

    # Chip boundary
    ax.add_patch(Rectangle((0, 0), chip_w, chip_h, fill=False, linewidth=2.0))
    ax.set_title(f"Layout view | HPWL={hpwl:.1f}\ncase={Path(case_path).name}, out={Path(out_path).name}")

    # Draw fixed (blue)
    for name, r in fixed_rects.items():
        ax.add_patch(Rectangle((r.x, r.y), r.w, r.h, alpha=0.35, linewidth=1.0))
        if show_labels:
            ax.text(r.cx, r.cy, name, ha="center", va="center", fontsize=7)

    # Draw soft (red)
    for name, r in soft_rects.items():
        ax.add_patch(Rectangle((r.x, r.y), r.w, r.h, alpha=0.35, linewidth=1.0))
        if show_labels:
            ax.text(r.cx, r.cy, name, ha="center", va="center", fontsize=7)

    # Overlaps: soft-soft + soft-fixed (black)
    overlaps: List[Rect] = []
    soft_list = list(soft_rects.items())
    fixed_list = list(fixed_rects.items())

    # soft-soft
    for i in range(len(soft_list)):
        a_name, a = soft_list[i]
        for j in range(i + 1, len(soft_list)):
            b_name, b = soft_list[j]
            inter = overlap_rect(a, b)
            if inter:
                overlaps.append(inter)

    # soft-fixed
    for s_name, s in soft_list:
        for f_name, f in fixed_list:
            inter = overlap_rect(s, f)
            if inter:
                overlaps.append(inter)

    for r in overlaps:
        ax.add_patch(Rectangle((r.x, r.y), r.w, r.h, alpha=0.9, linewidth=0))

    if overlaps:
        ax.text(0.02, 0.98, f"OVERLAP DETECTED: {len(overlaps)}",
                transform=ax.transAxes, ha="left", va="top", fontsize=10)

    # Edges (connections)
    # Keep only edges whose endpoints exist in all_rects
    valid_edges = []
    for a, b, w in edges:
        if a in all_rects and b in all_rects:
            valid_edges.append((a, b, w))

    # Sort by weight, draw top-K (avoid clutter)
    valid_edges.sort(key=lambda x: x[2], reverse=True)
    if max_edges > 0:
        valid_edges = valid_edges[:max_edges]

    if valid_edges:
        w_max = max(w for _, _, w in valid_edges)
        for a, b, w in valid_edges:
            ra = all_rects[a]
            rb = all_rects[b]
            # linewidth scaling: 0.2 ~ 3.0
            lw = 0.2 + 2.8 * (math.sqrt(w) / math.sqrt(w_max))
            ax.plot([ra.cx, rb.cx], [ra.cy, rb.cy], linewidth=lw, alpha=0.6)

    # Grid
    if grid_step is None:
        grid_step = choose_grid_step(chip_w, chip_h)

    ax.set_xlim(0, chip_w)
    ax.set_ylim(0, chip_h)
    ax.set_aspect("equal", adjustable="box")

    ax.set_xticks(list(range(0, chip_w + 1, grid_step)))
    ax.set_yticks(list(range(0, chip_h + 1, grid_step)))
    ax.grid(True, linewidth=0.5, alpha=0.4)

    ax.set_xlabel("x")
    ax.set_ylabel("y")

    if save_path:
        out_png = Path(save_path)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_png, dpi=200, bbox_inches="tight")
        print(f"[OK] saved plot: {out_png}")

    if show:
        plt.show()

    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="caseXX-input.txt")
    ap.add_argument("--out", required=True, help="out.txt produced by placer.exe")
    ap.add_argument("--save", default="", help="save path, e.g. vis/case01.png (optional)")
    ap.add_argument("--max_edges", type=int, default=120, help="draw only top-K weighted edges")
    ap.add_argument("--labels", action="store_true", help="show module names")
    ap.add_argument("--show", action="store_true", help="interactive display")
    ap.add_argument("--grid", type=int, default=0, help="grid step; 0 = auto")
    args = ap.parse_args()

    save_path = args.save.strip() or None
    grid_step = None if args.grid == 0 else args.grid

    plot_layout(
        case_path=args.case,
        out_path=args.out,
        save_path=save_path,
        max_edges=args.max_edges,
        show_labels=args.labels,
        show=args.show,
        grid_step=grid_step,
    )


if __name__ == "__main__":
    main()
