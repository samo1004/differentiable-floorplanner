"""
Evaluation metrics for floorplan quality.

All functions operate on a trained NormalizedFloorplanner model and
report results in real (un-normalized) coordinates.
"""

import numpy as np
from typing import Dict, List, Tuple

from .model import NormalizedFloorplanner


def _get_real_rects(model: NormalizedFloorplanner) -> np.ndarray:
    """Return (num_total, 4) array of (cx, cy, w, h) in real coordinates."""
    rects = model.get_norm_rects().detach().cpu().numpy()
    rects *= model.scale_factor
    return rects


def calculate_hpwl(
    model: NormalizedFloorplanner,
    nets: List[Tuple[str, str, int]],
) -> float:
    """Compute total weighted HPWL (Half-Perimeter Wirelength).

    HPWL = sum(weight_i * manhattan_distance(center_i, center_j))
    """
    rects = _get_real_rects(model)
    name2id = model.name2id
    total = 0.0
    for m1, m2, weight in nets:
        if m1 in name2id and m2 in name2id:
            p1 = rects[name2id[m1], :2]
            p2 = rects[name2id[m2], :2]
            total += weight * (abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]))
    return total


def calculate_total_overlap(model: NormalizedFloorplanner) -> float:
    """Compute total pairwise overlap area (real coordinates)."""
    rects = _get_real_rects(model)
    n = rects.shape[0]
    total = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            cx_i, cy_i, w_i, h_i = rects[i]
            cx_j, cy_j, w_j, h_j = rects[j]
            dx = abs(cx_i - cx_j)
            dy = abs(cy_i - cy_j)
            ov_x = max(0, (w_i + w_j) / 2 - dx)
            ov_y = max(0, (h_i + h_j) / 2 - dy)
            total += ov_x * ov_y
    return total


def calculate_boundary_violation(model: NormalizedFloorplanner) -> Dict[str, float]:
    """Check how much each soft module exceeds the chip boundary.

    Returns:
        Dict with keys 'total' and 'max', both in real coordinates.
    """
    rects = _get_real_rects(model)
    chip_w = model.norm_chip_w * model.scale_factor
    chip_h = model.norm_chip_h * model.scale_factor

    total_viol = 0.0
    max_viol = 0.0
    for i in range(model.num_soft):
        cx, cy, w, h = rects[i]
        viol = 0.0
        viol += max(0, -(cx - w / 2))
        viol += max(0, (cx + w / 2) - chip_w)
        viol += max(0, -(cy - h / 2))
        viol += max(0, (cy + h / 2) - chip_h)
        total_viol += viol
        max_viol = max(max_viol, viol)

    return {"total": total_viol, "max": max_viol}


def check_aspect_ratios(model: NormalizedFloorplanner) -> List[Dict]:
    """Check aspect ratio constraint (should be in [0.5, 2.0]) for soft modules.

    Returns:
        List of dicts with 'name', 'aspect_ratio', 'valid' for each soft module.
    """
    rects = _get_real_rects(model)
    results = []
    for i in range(model.num_soft):
        _, _, w, h = rects[i]
        ar = h / w if w > 0 else float("inf")
        results.append(
            {
                "name": model.mod_names[i],
                "aspect_ratio": ar,
                "valid": 0.5 <= ar <= 2.0,
            }
        )
    return results


def check_rectangle_ratios(model: NormalizedFloorplanner) -> List[Dict]:
    """Check rectangle ratio constraint (should be in [0.8, 1.0]).

    Rectangle ratio = actual_area / bounding_rect_area.
    Since our model places axis-aligned rectangles, this is always 1.0.
    This function is a placeholder for rectilinear polygon extensions.

    Returns:
        List of dicts with 'name', 'rect_ratio', 'valid' for each soft module.
    """
    rects = _get_real_rects(model)
    results = []
    for i in range(model.num_soft):
        _, _, w, h = rects[i]
        actual_area = w * h
        bounding_area = w * h
        ratio = actual_area / bounding_area if bounding_area > 0 else 0
        results.append(
            {
                "name": model.mod_names[i],
                "rect_ratio": ratio,
                "valid": 0.8 <= ratio <= 1.0,
            }
        )
    return results


def print_report(
    model: NormalizedFloorplanner,
    nets: List[Tuple[str, str, int]],
    elapsed_sec: float = 0.0,
) -> Dict:
    """Print a comprehensive evaluation report and return metrics dict."""
    hpwl = calculate_hpwl(model, nets)
    overlap = calculate_total_overlap(model)
    boundary = calculate_boundary_violation(model)
    ar_results = check_aspect_ratios(model)

    ar_violations = [r for r in ar_results if not r["valid"]]
    chip_area = model.norm_chip_w * model.norm_chip_h * (model.scale_factor ** 2)

    print("=" * 60)
    print("            EVALUATION  REPORT")
    print("=" * 60)
    print(f"  Total Weighted HPWL :  {hpwl:>15,.0f}")
    print(f"  Total Overlap Area  :  {overlap:>15,.0f}  {'LEGAL' if overlap < 1.0 else 'OVERLAP'}")
    print(
        f"  Boundary Violation  :  {boundary['total']:>15,.1f}"
        f"  (max single = {boundary['max']:,.1f})"
    )
    print(f"  Aspect Ratio Viols  :  {len(ar_violations):>15d} / {model.num_soft}")
    if elapsed_sec > 0:
        print(f"  Elapsed Time        :  {elapsed_sec:>15.2f} sec")
    print(f"  Chip Utilization    :  {chip_area:>15,.0f}")
    print("=" * 60)

    if ar_violations:
        print("  AR violations:")
        for violation in ar_violations:
            print(f"    {violation['name']:>10s}  AR={violation['aspect_ratio']:.3f}")
        print()

    return {
        "hpwl": hpwl,
        "overlap": overlap,
        "boundary": boundary,
        "ar_violations": len(ar_violations),
        "elapsed_sec": elapsed_sec,
    }
