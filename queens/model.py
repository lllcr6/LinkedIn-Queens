"""Immutable puzzle representation and independent rule validation.

Internal coordinates and region labels are zero-based. Connectivity is four-way;
queen attacks include only immediate diagonals, not full chess diagonals.
"""
from dataclasses import dataclass
from typing import Tuple

Cell = Tuple[int, int]
Placement = Tuple[int, ...]


def neighbors(cell, n):
    i, j = cell
    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        a, b = i + di, j + dj
        if 0 <= a < n and 0 <= b < n:
            yield a, b


def connected(cells, n):
    if not cells:
        return False
    seen = {next(iter(cells))}
    stack = list(seen)
    while stack:
        for cell in neighbors(stack.pop(), n):
            if cell in cells and cell not in seen:
                seen.add(cell)
                stack.append(cell)
    return len(seen) == len(cells)


@dataclass(frozen=True)
class Puzzle:
    regions: Tuple[Tuple[int, ...], ...]

    def __post_init__(self):
        n = self.n
        if not 1 <= n <= 12 or any(len(row) != n for row in self.regions):
            raise ValueError('Board must be a square of size 1–12.')
        values = [v for row in self.regions for v in row]
        if any(type(v) is not int for v in values) or set(values) != set(range(n)):
            raise ValueError('Use exactly N region labels, numbered 0 through N−1.')
        if any(not connected(cells, n) for cells in self.region_cells()):
            raise ValueError('Every region must be connected horizontally or vertically.')

    @property
    def n(self):
        return len(self.regions)

    @classmethod
    def from_rows(cls, rows):
        if not isinstance(rows, (list, tuple)) or any(not isinstance(r, (list, tuple)) for r in rows):
            raise ValueError('regions must be a two-dimensional array.')
        return cls(tuple(tuple(row) for row in rows))

    def region_cells(self):
        return [{(i, j) for i in range(self.n) for j in range(self.n)
                 if self.regions[i][j] == r} for r in range(self.n)]

    def generation_valid(self):
        sizes = [len(cells) for cells in self.region_cells()]
        return sizes.count(1) <= 1 and max(sizes) <= self.n * self.n // 2

    def accepts(self, q):
        return (len(q) == self.n and all(type(c) is int and 0 <= c < self.n for c in q)
                and len(set(q)) == self.n
                and all(abs(q[i] - q[i - 1]) != 1 for i in range(1, self.n))
                and len({self.regions[i][q[i]] for i in range(self.n)}) == self.n)
