import unittest
from threading import Event
from time import monotonic, sleep
from unittest.mock import patch
from queens.core import Budget, SearchCancelled, SOLVERS, GENERATORS
from queens.jobs import GenerationJobs
from queens.model import Puzzle
import random


class CancellationTest(unittest.TestCase):
    def test_cancellation_reaches_all_algorithms(self):
        event = Event()
        event.set()
        puzzle = Puzzle.from_rows([[i] * 6 for i in range(6)])
        for entry in SOLVERS.describe():
            with self.assertRaises(SearchCancelled):
                SOLVERS.create(entry['key']).solve(puzzle, Budget(cancel_event=event))
        for entry in GENERATORS.describe():
            result = GENERATORS.create(entry['key']).generate(
                6, True, random.Random(42), SOLVERS.create('dp'), Budget(cancel_event=event))
            self.assertEqual(result.status, 'cancelled')

    def test_job_stop_and_completion_race(self):
        entered = Event()
        def controlled_dispatch(action, data, budget):
            self.assertIsNone(budget.deadline)
            self.assertIsNone(budget.max_attempts)
            self.assertEqual(budget.solution_limit, 2)
            entered.set()
            budget.cancel_event.wait(2)
            return {'status': 'success'}
        jobs = GenerationJobs()
        with patch('queens.jobs.dispatch', controlled_dispatch):
            key = jobs.start({})['job_id']
            self.assertTrue(entered.wait(1))
            self.assertEqual(jobs.status(key)['status'], 'running')
            self.assertEqual(jobs.cancel(key)['status'], 'stopping')
            deadline = monotonic() + 2
            while jobs.status(key)['status'] == 'running' and monotonic() < deadline:
                sleep(.005)
            result = jobs.status(key)
            self.assertEqual(result['status'], 'cancelled')
            self.assertGreaterEqual(result['elapsed_ms'], 0)
            self.assertEqual(jobs.cancel(key), result)

    def test_background_generation_success(self):
        jobs = GenerationJobs()
        key = jobs.start({'n': 6, 'seed': 42, 'generator': 'repair'})['job_id']
        deadline = monotonic() + 2
        while jobs.status(key)['status'] == 'running' and monotonic() < deadline:
            sleep(.005)
        result = jobs.status(key)
        self.assertEqual(result['status'], 'success')
        self.assertTrue(Puzzle.from_rows(result['regions']).generation_valid())

    def test_invalid_job(self):
        with self.assertRaises(ValueError):
            GenerationJobs().cancel('missing')
