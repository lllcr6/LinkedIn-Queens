"""Row-ordered backtracking, with optional forward checking."""
from time import perf_counter
from ..core import SOLVERS, Solver, SolveResult


@SOLVERS.register('backtracking', 'Backtracking', 'Row-by-row search; returns up to five solutions.')
class BacktrackingSolver(Solver):
    forward_check = False

    def solve(self, puzzle, budget):
        start, before = perf_counter(), budget.nodes
        n, board = puzzle.n, puzzle.regions
        solutions, q = [], []
        full = (1 << n) - 1

        def viable(row, cols, regions):
            # Necessary conditions: every remaining row/column/region has a candidate.
            possible_cols = possible_regions = 0
            for i in range(row, n):
                found = False
                for c in range(n):
                    r = board[i][c]
                    if cols >> c & 1 or regions >> r & 1:
                        continue
                    if i == row and q and abs(c - q[-1]) == 1:
                        continue
                    found = True
                    possible_cols |= 1 << c
                    possible_regions |= 1 << r
                if not found:
                    return False
            return (possible_cols | cols) == full and (possible_regions | regions) == full

        def visit(row, cols, regions):
            budget.tick()
            if row == n:
                solutions.append(tuple(q))
                return
            if self.forward_check and not viable(row, cols, regions):
                return
            for c in range(n):
                r = board[row][c]
                if cols >> c & 1 or regions >> r & 1 or (q and abs(c - q[-1]) == 1):
                    continue
                q.append(c)
                visit(row + 1, cols | 1 << c, regions | 1 << r)
                q.pop()
                if len(solutions) == budget.solution_limit:
                    return

        visit(0, 0, 0)
        return SolveResult(solutions, (perf_counter() - start) * 1000, budget.nodes - before,
                           limit_reached=len(solutions) == budget.solution_limit)


@SOLVERS.register('pruned', 'Forward-checking backtracking', 'Bitmasks with forward checking.')
class PrunedBacktrackingSolver(BacktrackingSolver):
    forward_check = True
