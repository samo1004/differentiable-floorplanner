"""
Training configuration for the differentiable global placer.

Two built-in strategies:
  - "fixed":      Lock phase keeps overlap weight constant (test2 style).
                  Better HPWL, may leave some overlap.
  - "escalating": Lock phase ramps overlap weight up to 10x (test3 style).
                  More aggressive legalization, sacrifices some HPWL.
"""

from dataclasses import dataclass, field


@dataclass
class TrainingConfig:
    """All hyperparameters for one training run."""

    # General
    iterations: int = 2000 #3000
    lr: float = 1e-2
    seed: int = 42

    # Loss weights
    lambda_overlap_final: float = 500.0
    lambda_boundary: float = 2000.0

    # Phase schedule (iteration boundaries)
    ghost_end: int = 400 #800      # [0, ghost_end)      = Ghost phase
    spread_end: int = 1600 #2200    # [ghost_end, spread_end) = Spread phase
                               # [spread_end, iterations) = Lock phase

    # Ghost phase
    ghost_hpwl_weight: float = 0.1
    ghost_overlap_weight: float = 0.0
    ghost_noise: float = 0.0

    # Spread phase
    spread_hpwl_weight: float = 0.05
    spread_noise_max: float = 5.0   # linearly decays to 0

    # Lock phase
    lock_strategy: str = "fixed"  # "fixed" or "escalating"
    lock_hpwl_weight: float = 0.01
    lock_overlap_multiplier: float = 10.0   # only used when strategy="escalating"

    # Gradient
    grad_clip: float = 1.0


def get_preset(name: str) -> TrainingConfig:
    """Return a preset configuration by name.

    Args:
        name: One of "fixed" (test2-style) or "escalating" (test3-style).
    """
    if name == "fixed":
        return TrainingConfig(
            lock_strategy="fixed",
            lock_hpwl_weight=0.01,
        )
    elif name == "escalating":
        return TrainingConfig(
            lock_strategy="escalating",
            lock_hpwl_weight=0.005,
            lock_overlap_multiplier=10.0,
        )
    else:
        raise ValueError(f"Unknown preset: '{name}'. Use 'fixed' or 'escalating'.")
