"""Memoized F(used columns, used regions, previous column).

Cache a bounded number of suffix witnesses per state. A shared suffix can be appended to
multiple prefixes, which correctly counts distinct full placements. In addition
to the standard state bound, retaining witnesses adds an O(N) space factor.
"""
from functools import lru_cache
from time import perf_counter
from ..core import SOLVERS, Solver, SolveResult, SearchLimit


@SOLVERS.register('dp', 'Memoized DP', 'Memoizes column, region, and previous-column states.')
class DPSolver(Solver):
    def solve(self, puzzle, budget):
        start, before = perf_counter(), budget.nodes
        n, board = puzzle.n, puzzle.regions
        states = 0

        @lru_cache(maxsize=None)
        def visit(cols, regions, previous):
            nonlocal states
            budget.tick()
            states += 1
            if states > 100_000:
                raise SearchLimit('DP state limit reached.')
            row = bin(cols).count('1')
            if row == n:
                return ((),)
            answers = []
            for c in range(n):
                r = board[row][c]
                if cols >> c & 1 or regions >> r & 1 or (previous >= 0 and abs(c - previous) == 1):
                    continue
                for suffix in visit(cols | 1 << c, regions | 1 << r, c):
                    answers.append((c,) + suffix)
                    if len(answers) == budget.solution_limit:
                        return tuple(answers)
            return tuple(answers)

        try:
            solutions = list(visit(0, 0, -1))
            hits = visit.cache_info().hits
        finally:
            visit.cache_clear()
        return SolveResult(solutions, (perf_counter() - start) * 1000, budget.nodes - before, hits,
                           len(solutions) == budget.solution_limit)
