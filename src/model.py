"""
Differentiable floorplanning model.

The NormalizedFloorplanner is an nn.Module whose trainable parameters are
the (cx, cy) positions and log-aspect-ratios of soft modules. All
coordinates are normalized by the chip's max dimension so that gradients
have a uniform scale.
"""

import math
import torch
import torch.nn as nn
from typing import Dict, List, Tuple


class NormalizedFloorplanner(nn.Module):
    """Differentiable global placer for fixed-outline floorplanning.

    Trainable parameters:
        soft_pos   : (num_soft, 2)  — normalized center (cx, cy)
        soft_log_ar: (num_soft,)    — log aspect-ratio, clamped via tanh

    Buffers (move with model to GPU automatically):
        norm_soft_areas : (num_soft,)
        fixed_params    : (num_fixed, 4)  — (cx, cy, w, h) normalized
        adj_matrix      : (num_total, num_total) — weighted adjacency
    """

    def __init__(
        self,
        chip_w: int,
        chip_h: int,
        soft_mods: Dict[str, int],
        fixed_mods: Dict[str, Tuple[int, int, int, int]],
        nets: List[Tuple[str, str, int]],
    ):
        super().__init__()

        # --- Normalization ---
        self.scale_factor = max(chip_w, chip_h)
        self.norm_chip_w = chip_w / self.scale_factor
        self.norm_chip_h = chip_h / self.scale_factor

        # --- Module indexing ---
        self.mod_names = list(soft_mods.keys()) + list(fixed_mods.keys())
        self.name2id = {name: i for i, name in enumerate(self.mod_names)}
        self.num_soft = len(soft_mods)
        self.num_fixed = len(fixed_mods)
        self.num_total = self.num_soft + self.num_fixed

        # --- Trainable: soft module positions ---
        initial_pos = torch.rand(self.num_soft, 2) * 0.4 + 0.3
        initial_pos[:, 0] *= self.norm_chip_w
        initial_pos[:, 1] *= self.norm_chip_h
        self.soft_pos = nn.Parameter(initial_pos)

        # --- Trainable: soft module aspect ratios (in log space) ---
        self.soft_log_ar = nn.Parameter(torch.zeros(self.num_soft))

        # --- Buffer: normalized soft module areas ---
        raw_areas = torch.tensor(
            [soft_mods[n] for n in self.mod_names[:self.num_soft]],
            dtype=torch.float32,
        )
        self.register_buffer('norm_soft_areas', raw_areas / (self.scale_factor ** 2))

        # --- Buffer: fixed module geometry (cx, cy, w, h) ---
        fixed_tensor = torch.zeros(self.num_fixed, 4)
        for i, name in enumerate(self.mod_names[self.num_soft:]):
            x, y, w, h = fixed_mods[name]
            fixed_tensor[i, 0] = (x + w / 2.0) / self.scale_factor
            fixed_tensor[i, 1] = (y + h / 2.0) / self.scale_factor
            fixed_tensor[i, 2] = w / self.scale_factor
            fixed_tensor[i, 3] = h / self.scale_factor
        self.register_buffer('fixed_params', fixed_tensor)

        # --- Buffer: weighted adjacency matrix ---
        adj = torch.zeros(self.num_total, self.num_total)
        for m1, m2, weight in nets:
            if m1 in self.name2id and m2 in self.name2id:
                i, j = self.name2id[m1], self.name2id[m2]
                adj[i, j] += weight
                adj[j, i] += weight
        self.register_buffer('adj_matrix', adj)

    def get_norm_rects(self) -> torch.Tensor:
        """Compute normalized rectangles for all modules.

        Returns:
            Tensor of shape (num_total, 4): each row is (cx, cy, w, h)
            in normalized coordinates.
        """
        # Clamp aspect ratio to [0.5, 2] via tanh
        clamped_log_ar = torch.tanh(self.soft_log_ar) * math.log(2.0)
        aspect_ratios = torch.exp(clamped_log_ar)

        soft_w = torch.sqrt(self.norm_soft_areas * aspect_ratios)
        soft_h = torch.sqrt(self.norm_soft_areas / aspect_ratios)

        soft_rects = torch.stack(
            [self.soft_pos[:, 0], self.soft_pos[:, 1], soft_w, soft_h],
            dim=1,
        )
        return torch.cat([soft_rects, self.fixed_params], dim=0)

    def forward(self) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Compute all differentiable loss components.

        Returns:
            (hpwl_loss, overlap_loss, boundary_loss) — all scalar tensors.
        """
        rects = self.get_norm_rects()
        cx, cy, w, h = rects[:, 0], rects[:, 1], rects[:, 2], rects[:, 3]

        # --- HPWL loss (weighted Manhattan distance) ---
        dist_x = torch.abs(cx.unsqueeze(0) - cx.unsqueeze(1))
        dist_y = torch.abs(cy.unsqueeze(0) - cy.unsqueeze(1))
        hpwl_loss = torch.sum(self.adj_matrix * (dist_x + dist_y)) / 2.0

        # --- Pairwise overlap loss ---
        w_sum = (w.unsqueeze(0) + w.unsqueeze(1)) / 2.0
        h_sum = (h.unsqueeze(0) + h.unsqueeze(1)) / 2.0
        ov_x = torch.relu(w_sum - dist_x)
        ov_y = torch.relu(h_sum - dist_y)
        overlap_matrix = ov_x * ov_y

        mask = torch.eye(self.num_total, device=rects.device).bool()
        overlap_matrix.masked_fill_(mask, 0)
        overlap_loss = torch.sum(overlap_matrix) / 2.0

        # --- Boundary loss ---
        x_min, x_max = cx - w / 2.0, cx + w / 2.0
        y_min, y_max = cy - h / 2.0, cy + h / 2.0
        bound_loss = (
            torch.sum(torch.relu(-x_min))
            + torch.sum(torch.relu(x_max - self.norm_chip_w))
            + torch.sum(torch.relu(-y_min))
            + torch.sum(torch.relu(y_max - self.norm_chip_h))
        )

        return hpwl_loss, overlap_loss, bound_loss
