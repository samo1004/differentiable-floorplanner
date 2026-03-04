"""
Input file parser for ICCAD 2023 Problem D floorplanning.

Supports the standard input format:
    CHIP <width> <height>
    SOFTMODULE <count>
    <name> <min_area>
    ...
    FIXEDMODULE <count>
    <name> <x> <y> <w> <h>
    ...
    CONNECTION <count>
    <module1> <module2> <weight>
    ...
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class SoftModule:
    """A soft (deformable) module with a minimum area requirement."""
    name: str
    min_area: int


@dataclass
class FixedModule:
    """A fixed module with known position and dimensions."""
    name: str
    x: int
    y: int
    w: int
    h: int


@dataclass
class Net:
    """A two-pin net connecting two modules with a weight."""
    module1: str
    module2: str
    weight: int


@dataclass
class FloorplanInput:
    """Complete parsed input for one floorplan case."""
    chip_w: int
    chip_h: int
    soft_modules: Dict[str, int]     # name -> min_area
    fixed_modules: Dict[str, Tuple[int, int, int, int]]  # name -> (x, y, w, h)
    nets: List[Tuple[str, str, int]]  # [(m1, m2, weight), ...]


def parse_file(filepath: str) -> FloorplanInput:
    """Parse a floorplan input file and return structured data.

    Args:
        filepath: Path to the input file.

    Returns:
        FloorplanInput with all parsed data.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is invalid.
    """
    with open(filepath, 'r') as f:
        data_str = f.read()
    return parse_string(data_str)


def parse_string(data_str: str) -> FloorplanInput:
    """Parse a floorplan input string and return structured data.

    Args:
        data_str: Raw input string in the standard format.

    Returns:
        FloorplanInput with all parsed data.
    """
    tokens = data_str.split()
    it = iter(tokens)

    # CHIP <width> <height>
    token = next(it)
    if token != 'CHIP':
        raise ValueError(f"Expected 'CHIP', got '{token}'")
    chip_w = int(next(it))
    chip_h = int(next(it))

    soft_modules = {}
    fixed_modules = {}
    nets = []

    while True:
        try:
            token = next(it)
        except StopIteration:
            break

        if token == 'SOFTMODULE':
            count = int(next(it))
            for _ in range(count):
                name = next(it)
                area = int(next(it))
                soft_modules[name] = area

        elif token == 'FIXEDMODULE':
            count = int(next(it))
            for _ in range(count):
                name = next(it)
                x, y, w, h = int(next(it)), int(next(it)), int(next(it)), int(next(it))
                fixed_modules[name] = (x, y, w, h)

        elif token == 'CONNECTION':
            count = int(next(it))
            for _ in range(count):
                m1, m2 = next(it), next(it)
                weight = int(next(it))
                nets.append((m1, m2, weight))

    return FloorplanInput(
        chip_w=chip_w,
        chip_h=chip_h,
        soft_modules=soft_modules,
        fixed_modules=fixed_modules,
        nets=nets,
    )
