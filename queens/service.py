"""Application layer shared by HTTP, scripts, and tests."""
import random
from dataclasses import asdict
from . import solvers, generators  # register built-in strategies
from .core import Budget, SOLVERS, GENERATORS, SearchLimit
from .model import Puzzle


def integer(data, key, default, low, high):
    value = data.get(key, default)
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{key} must be an integer between {low} and {high}.')
    return value


def dispatch(action, data, budget=None):
    if not isinstance(data, dict):
        raise ValueError('Request must be a JSON object.')
    if action == 'algorithms':
        return dict(solvers=SOLVERS.describe(), generators=GENERATORS.describe())
    solver = SOLVERS.create(data.get('solver', 'pruned'))
    if budget is None:
        budget = Budget(solution_limit=2 if action == 'generate' else 5)
    if action == 'solve':
        puzzle = Puzzle.from_rows(data.get('regions'))
        try:
            answer = solver.solve(puzzle, budget)
        except SearchLimit:
            return dict(status='limit', message='Search limit reached; classification is unknown.')
        return dict(status='success', classification=answer.classification, **asdict(answer))
    if action == 'generate':
        n = integer(data, 'n', 6, 4, 12)
        seed = integer(data, 'seed', 42, 0, 2**32 - 1)
        unique = data.get('unique', True)
        if type(unique) is not bool:
            raise ValueError('unique must be a Boolean.')
        generator = GENERATORS.create(data.get('generator', 'repair'))
        answer = generator.generate(n, unique, random.Random(seed), solver, budget)
        payload = asdict(answer)
        serialized_puzzle = payload.pop('puzzle')
        payload['regions'] = serialized_puzzle['regions'] if serialized_puzzle else None
        payload['seed'] = seed
        return payload
    raise ValueError('Unknown API action.')
