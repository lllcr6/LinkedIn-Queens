"""Seeded connected growth and counterexample-guided boundary repair.

Both methods are bounded randomized heuristics, not complete decision procedures.
The stored seed placement remains valid through every growth and repair step.
"""
from time import perf_counter
from ..model import Puzzle, connected, neighbors
from ..core import GENERATORS, Generator, GenerationResult, SearchLimit, SearchCancelled


def seed_placement(n, rng, budget):
    q = []
    def visit(used):
        budget.tick()
        if len(q) == n:
            return tuple(q)
        choices = list(range(n))
        rng.shuffle(choices)
        for c in choices:
            if used >> c & 1 or (q and abs(c - q[-1]) == 1):
                continue
            q.append(c)
            result = visit(used | 1 << c)
            if result is not None:
                return result
            q.pop()
        return None
    return visit(0)


def grow(n, q, rng, budget):
    cells = [{(i, c)} for i, c in enumerate(q)]
    free = {(i, j) for i in range(n) for j in range(n)} - set.union(*cells)
    cap = n * n // 2
    while free:
        budget.tick()
        frontiers = [{v for u in region for v in neighbors(u, n) if v in free}
                     if len(region) < cap else set() for region in cells]
        singletons = [r for r in range(n) if len(cells[r]) == 1]
        if sum(not frontiers[r] for r in singletons) > 1:
            return None
        options = [r for r in range(n) if frontiers[r]]
        if not options:
            return None
        urgent = [r for r in singletons if frontiers[r]] if len(singletons) > 1 else []
        if urgent:
            r = rng.choice(urgent)
        else:
            r = rng.choices(options, weights=[1 / len(cells[r]) for r in options])[0]
        cell = rng.choice(sorted(frontiers[r]))
        cells[r].add(cell)
        free.remove(cell)
    board = [[-1] * n for _ in range(n)]
    for r, region in enumerate(cells):
        for i, j in region:
            board[i][j] = r
    puzzle = Puzzle.from_rows(board)
    return puzzle if puzzle.generation_valid() else None


def repair(puzzle, witness, alternate, rng, budget):
    """Try a single-cell transfer that eliminates this alternate solution."""
    n = puzzle.n
    regions = puzzle.region_cells()
    seeds = {(i, c) for i, c in enumerate(witness)}
    candidates = [(i, c) for i, c in enumerate(alternate) if (i, c) not in seeds]
    rng.shuffle(candidates)
    for cell in candidates:
        budget.tick()
        i, j = cell
        source = puzzle.regions[i][j]
        targets = sorted({puzzle.regions[a][b] for a, b in neighbors(cell, n)} - {source})
        rng.shuffle(targets)
        for target in targets:
            if len(regions[target]) >= n * n // 2:
                continue
            if not connected(regions[source] - {cell}, n):
                continue
            sizes = [len(c) for c in regions]
            sizes[source] -= 1
            sizes[target] += 1
            if sizes.count(1) > 1:
                continue
            board = [list(row) for row in puzzle.regions]
            board[i][j] = target
            changed = Puzzle.from_rows(board)
            if not changed.accepts(alternate):
                return changed
    return None


@GENERATORS.register('growth', 'Random growth + rejection', 'Grows connected regions; retries if uniqueness fails.')
class GrowthGenerator(Generator):
    repair_steps = 0

    def generate(self, n, unique, rng, solver, budget):
        start = perf_counter()
        attempts = repairs = calls = 0
        def result(puzzle=None, witness=None, status='not_found'):
            return GenerationResult(puzzle, witness, bool(puzzle is not None and unique),
                                    attempts, repairs, calls, (perf_counter() - start) * 1000, status)
        # N=1 violates the region cap. N=2,3 have no nonadjacent permutation.
        if n < 4:
            return result(status='infeasible')
        try:
            while budget.max_attempts is None or attempts < budget.max_attempts:
                attempts += 1
                q = seed_placement(n, rng, budget)
                if q is None:
                    return result(status='infeasible')
                puzzle = grow(n, q, rng, budget)
                if puzzle is None:
                    continue
                if not unique:
                    return result(puzzle, q, 'success')
                seen = {puzzle.regions}
                for step in range(self.repair_steps + 1):
                    calls += 1
                    answer = solver.solve(puzzle, budget)
                    if answer.classification == 'unique':
                        return result(puzzle, q, 'success')
                    if not answer.solutions:
                        raise RuntimeError('Generator invariant failed: seed solution was lost.')
                    if step == self.repair_steps:
                        break
                    alternate = next(x for x in answer.solutions if x != q)
                    changed = repair(puzzle, q, alternate, rng, budget)
                    if changed is None or changed.regions in seen:
                        break
                    puzzle = changed
                    seen.add(puzzle.regions)
                    repairs += 1
        except SearchCancelled:
            return result(status='cancelled')
        except SearchLimit:
            pass
        return result()


@GENERATORS.register('repair', 'Growth + counterexample repair', 'Adjusts boundaries to eliminate alternative solutions.')
class RepairGenerator(GrowthGenerator):
    repair_steps = 30
