"""
Training loop for the differentiable global placer.

Implements a three-phase schedule:
  1. Ghost   — modules overlap freely; HPWL pulls connected modules together.
  2. Spread  — overlap penalty ramps up quadratically; gradient noise decays.
  3. Lock    — strong overlap penalty drives toward legality.
"""

import torch
import torch.optim as optim
from typing import List, Dict, Any

from .config import TrainingConfig
from .model import NormalizedFloorplanner


def train(
    model: NormalizedFloorplanner,
    config: TrainingConfig,
    device: torch.device,
) -> List[Dict[str, Any]]:
    """Run the three-phase training loop.

    Args:
        model:  The floorplanner model (will be moved to *device*).
        config: Training hyperparameters.
        device: torch device (cpu / cuda).

    Returns:
        history: list of dicts, each containing:
            step, phase, rects (numpy), loss (float).
    """
    model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=config.lr)
    history: List[Dict[str, Any]] = []

    print(f"Training on {device}  |  strategy={config.lock_strategy}  |  "
          f"iters={config.iterations}")
    print(f"  Schedule: Ghost [0, {config.ghost_end})  "
          f"Spread [{config.ghost_end}, {config.spread_end})  "
          f"Lock [{config.spread_end}, {config.iterations})")
    print("-" * 60)

    for i in range(config.iterations):
        optimizer.zero_grad()
        hpwl, overlap, boundary = model()

        # Phase schedule
        if i < config.ghost_end:
            phase = "Ghost"
            cur_hpwl_w = config.ghost_hpwl_weight
            cur_overlap_w = config.ghost_overlap_weight
            noise_level = config.ghost_noise

        elif i < config.spread_end:
            phase = "Spread"
            progress = (i - config.ghost_end) / (config.spread_end - config.ghost_end)
            cur_hpwl_w = config.spread_hpwl_weight
            cur_overlap_w = config.lambda_overlap_final * (progress ** 2)
            noise_level = config.spread_noise_max * (1.0 - progress)

        else:
            phase = "Lock"
            cur_hpwl_w = config.lock_hpwl_weight
            noise_level = 0.0

            if config.lock_strategy == "escalating":
                lock_progress = (i - config.spread_end) / (
                    config.iterations - config.spread_end
                )
                cur_overlap_w = config.lambda_overlap_final * (
                    1 + lock_progress * config.lock_overlap_multiplier
                )
            else:  # "fixed"
                cur_overlap_w = config.lambda_overlap_final

        # Backward
        total_loss = (
            hpwl * cur_hpwl_w
            + cur_overlap_w * overlap
            + config.lambda_boundary * boundary
        )
        total_loss.backward()

        # Gradient noise injection
        if noise_level > 0 and model.soft_pos.grad is not None:
            noise = torch.randn_like(model.soft_pos.grad) * noise_level
            model.soft_pos.grad.add_(noise)

        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=config.grad_clip)
        optimizer.step()

        # Recording
        if i % 20 == 0 or i == config.iterations - 1:
            current_rects = model.get_norm_rects().detach().cpu().numpy().copy()
            history.append({
                'step': i,
                'phase': phase,
                'rects': current_rects,
                'loss': total_loss.item(),
            })

        if i % 500 == 0:
            print(
                f"  iter {i:5d}  [{phase:6s}]  "
                f"loss={total_loss.item():.4f}  "
                f"hpwl={hpwl.item():.4f}  "
                f"overlap={overlap.item():.6f}  "
                f"bound={boundary.item():.6f}"
            )

    print("-" * 60)
    return history
