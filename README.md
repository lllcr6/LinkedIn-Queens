# Queens Lab

A Python project for queen puzzle algorithms with a local web interface. It requires Python 3.9+ and uses only the standard library; no pip or npm installation is needed.

## Getting started

Run this command from the project directory:

```bash
python3 -m queens.server
```

Open <http://127.0.0.1:8000> in your browser. If the port is in use, pass `--port 8001`. Press Ctrl+C to stop the server.

Choose a size, seed, generation strategy, and solver, then click “Generate Board” followed by “Solve Current Board.” You can show or hide answers, switch between up to five witness solutions when multiple solutions exist, or export JSON. Imports accept either a complete exported object or a standalone `regions` array. Region labels range from **0 to N−1**, and coordinates are also zero-based. Row and column hints in the interface are one-based.

## Code structure and extensions

```text
queens/
  model.py               Board model, connectivity, and independent validity checks
  core.py                Strategy interfaces, registry/factory, budgets, and results
  solvers/
    backtracking.py      Basic backtracking and forward checking
    dp.py                Memoized state-compression DP
  generators/
    growth.py            Connected region growth, filtering, and second-solution boundary repair
  service.py             Algorithm selection, request validation, and unified application entry point
  jobs.py                Background generation jobs, status queries, and cooperative cancellation
  server.py              Localhost-only HTTP server
  web/                   Vanilla HTML / CSS / JS frontend
tests/
  test_algorithms.py     Independent permutation oracle and generation invariant tests
```

The project uses **Strategy + Registry/Factory**: solvers implement `Solver.solve(puzzle, budget)`, and generators implement `Generator.generate(n, unique, rng, solver, budget)`. Generators receive a solver through its interface and do not depend on a particular algorithm.

Example of a new solver:

```python
from queens.core import Solver, SOLVERS

@SOLVERS.register('new_solver', 'New solver', 'Algorithm description')
class NewSolver(Solver):
    def solve(self, puzzle, budget):
        # Call budget.tick() in the search loop and return a SolveResult.
        # Exhaust the search before returning fewer than the limit; return as
        # soon as budget.solution_limit solutions have been found.
        # Raise SearchLimit if classification cannot be completed; do not
        # report the puzzle as unsolvable.
        ...
```

Import the new module in `queens/solvers/__init__.py`. The frontend reads the registry from `/api/algorithms` and adds the option automatically. New generators follow the same pattern, with an import in `generators/__init__.py`.

## Algorithms and rules

- Basic backtracking enumerates columns row by row and tracks used columns and regions with bitmasks. It finds up to five solutions; uniqueness checks during generation need only find two.
- Pruned backtracking adds forward checking: every remaining row, column, and region must have at least one candidate cell. These are necessary conditions only; they do not assume that distinct candidates can all be satisfied simultaneously.
- DP caches `(used_columns, used_regions, previous_column)`. The row is determined by the number of used columns. Each state stores up to `budget.solution_limit` suffix witnesses, which are joined with prefixes to recover concrete solutions. The theoretical state bound is `O(N 4^N)`, and the bound for scanning transitions is `O(N² 4^N)`. Storing suffix witnesses gives a space bound of `O(N² 4^N)`, rather than the bound for storing counts alone. The implementation also limits each call to 100,000 states. These bounds exclude Python big-integer operations and hashing costs.
- Growth randomly searches for a seed solution, prioritizes expanding single-cell regions, and then favors smaller regions. It only claims adjacent unassigned cells. It restarts on failure or when multiple solutions are found and uniqueness is required.
- Repair builds on Growth by moving non-seed boundary cells to eliminate a second solution. Each step checks source-region connectivity, size limits, and the number of single-cell regions, then calls the solver again. It detects repeated boards to avoid cycles and restarts after at most 30 repair steps.

Generated boards have at most one single-cell region, each region contains at most `floor(N*N/2)` cells, and all regions are connected through orthogonal adjacency. Seed queens stay fixed, so every generated or repaired board remains solvable. A board is declared unique only after the solver completes a uniqueness check. Solvers accept imported boards that do not satisfy the generation size limits, but still validate connectivity and labels.

The frontend supports generation for N=4–12; the solve interface supports N=1–12. N=1 cannot be generated under the half-board size limit, and N=2 and N=3 have no permutations satisfying the adjacency restriction. Random generation is not a complete algorithm. Web generation has no time limit or cumulative node/attempt limit; it continues until it succeeds, reaches the DP memory protection limit, or the user clicks **Stop generation**. The frontend shows **Generation time** in real time and retains the backend timing after completion or cancellation. Cancellation passes an Event to the generator and solver to stop the search, rather than merely cancelling the frontend request. Closing the page also attempts to send a cancellation request.

Synchronous Python/API generation defaults to 400 attempts and 500,000 nodes. Ordinary solving defaults to 500,000 nodes, and DP is limited to 100,000 states per call. None has a default time limit. Reaching a resource limit must not be interpreted as proof that a puzzle has no solution. A random seed reproduces the board with the same implementation when resource limits are not reached.

Solving returns at most five distinct solutions. If the limit is reached, `limit_reached=true` and the interface displays “At least 5 solutions found. Showing 5.” without claiming that five is the total. `found` indicates the solutions found; results are written to a file only when JSON is exported. Uniqueness checks during generation still search for at most two solutions.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests compare each solver's solution-count classification against an independent exhaustive permutation oracle. They cover unsolvable, unique, and multiple-solution cases, timeouts, random connected boards, generation constraints, and repair invariants.

## Python usage

```python
from queens.service import dispatch

puzzle = dispatch('generate', {'n': 6, 'seed': 42, 'unique': True,
                              'generator': 'repair', 'solver': 'pruned'})
if puzzle['status'] == 'success':
    answer = dispatch('solve', {'regions': puzzle['regions'], 'solver': 'dp'})
    print(answer)
```

HTTP API: `GET /api/algorithms`, `POST /api/generate`, and `POST /api/solve`. POST parameters match the example above. Web generation uses `POST /api/generation/start` to return a `job_id`, then sends `{ "job_id": "..." }` to `/api/generation/status` or `/api/generation/cancel` to query or cancel the job. This is a local course demonstration service, not a production server.
