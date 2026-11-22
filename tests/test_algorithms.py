"""Independent brute-force oracle, generation invariants, and API validation."""
import itertools
import random
import unittest
from queens.model import Puzzle, connected
from queens.core import Budget, SOLVERS, GENERATORS, SearchLimit
from queens.service import dispatch
from queens.generators.growth import grow, seed_placement, repair


def brute(board):
    n = len(board)
    return [q for q in itertools.permutations(range(n))
            if all(abs(q[i] - q[i-1]) != 1 for i in range(1, n))
            and len({board[i][q[i]] for i in range(n)}) == n]


class SolversTest(unittest.TestCase):
    def check_all(self, puzzle):
        expected = brute(puzzle.regions)
        for entry in SOLVERS.describe():
            answer = SOLVERS.create(entry['key']).solve(puzzle, Budget(5))
            self.assertEqual(len(answer.solutions), min(5, len(expected)))
            self.assertEqual(answer.limit_reached, len(expected) >= 5)
            self.assertEqual(len(set(answer.solutions)), len(answer.solutions))
            for q in answer.solutions:
                self.assertIn(q, expected)

    def test_row_and_column_regions(self):
        for n in range(1, 8):
            self.check_all(Puzzle.from_rows([[i]*n for i in range(n)]))
            self.check_all(Puzzle.from_rows([list(range(n)) for _ in range(n)]))

    def test_unique_and_unsatisfiable_region_constraints(self):
        # N-1 singleton seeds force the last queen. This is solver input only.
        q = (1, 3, 0, 2)
        board = [[3]*4 for _ in range(4)]
        for i in range(3):
            board[i][q[i]] = i
        self.assertEqual(len(brute(board)), 1)
        self.check_all(Puzzle.from_rows(board))
        # Two singleton regions force two queens into row zero.
        board = [[3]*4 for _ in range(4)]
        board[0][0], board[0][1], board[3][0] = 0, 1, 2
        self.assertEqual(brute(board), [])
        self.check_all(Puzzle.from_rows(board))

    def test_random_connected_partitions(self):
        rng = random.Random(121)
        for n in (4, 5, 6, 7):
            for _ in range(8):
                q = seed_placement(n, rng, Budget())
                puzzle = grow(n, q, rng, Budget())
                if puzzle:
                    self.assertTrue(puzzle.accepts(q))
                    self.check_all(puzzle)

    def test_limit_is_not_unsat(self):
        puzzle = Puzzle.from_rows([[i]*6 for i in range(6)])
        for entry in SOLVERS.describe():
            with self.assertRaises(SearchLimit):
                SOLVERS.create(entry['key']).solve(puzzle, Budget(max_nodes=0))


class GenerationTest(unittest.TestCase):
    def test_generation_and_reproducibility(self):
        for key in ('growth', 'repair'):
            for unique in (False, True):
                # Rejection has low unique-puzzle yield at larger N; repair is
                # tested at N=6 while the rejection success fixture uses N=5.
                args = dict(n=5 if key == 'growth' else 6, seed=42,
                            unique=unique, generator=key, seconds=10)
                a = dispatch('generate', args)
                b = dispatch('generate', args)
                self.assertEqual(a['status'], 'success')
                self.assertEqual(a['regions'], b['regions'])
                p = Puzzle.from_rows(a['regions'])
                self.assertTrue(p.generation_valid())
                self.assertTrue(p.accepts(a['witness']))
                if unique:
                    self.assertEqual(len(brute(p.regions)), 1)

    def test_repair_preserves_seed_and_eliminates_counterexample(self):
        rng = random.Random(4)
        repaired = 0
        for _ in range(60):
            q = seed_placement(6, rng, Budget())
            p = grow(6, q, rng, Budget())
            if not p:
                continue
            for alternate in brute(p.regions):
                if alternate == q:
                    continue
                changed = repair(p, q, alternate, rng, Budget())
                if changed:
                    self.assertTrue(changed.accepts(q))
                    self.assertFalse(changed.accepts(alternate))
                    self.assertTrue(changed.generation_valid())
                    repaired += 1
                    break
        self.assertGreater(repaired, 0)

    def test_generation_timeout(self):
        a = GENERATORS.create('repair').generate(6, True, random.Random(0), SOLVERS.create('dp'), Budget(max_nodes=0))
        self.assertEqual(a.status, 'not_found')
        self.assertIsNone(a.puzzle)

    def test_rejection_exhaustion_is_not_infeasibility(self):
        a = dispatch('generate', dict(n=6, seed=42, generator='growth', unique=True))
        self.assertEqual(a['status'], 'not_found')
        self.assertIsNone(a['regions'])
        self.assertFalse(a['uniqueness_verified'])

    def test_connectivity_and_invalid_requests(self):
        self.assertFalse(connected({(0,0),(1,1)}, 2))
        for rows in (None, [], [[0,1]], [[0,1],[1,0]], [[True]]):
            with self.assertRaises(ValueError):
                Puzzle.from_rows(rows)
        for data in ({'n':3}, {'n':True}, {'unique':'yes'}, {'seed':-1}, {'solver':'unknown'}):
            with self.assertRaises(ValueError):
                dispatch('generate', data)


if __name__ == '__main__':
    unittest.main()
