"""Strategy interfaces, result types, cooperative limits, and registry factory."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from typing import List, Optional
from .model import Placement, Puzzle


class SearchLimit(Exception):
    """The resource limit was reached; this is not evidence of infeasibility."""


class SearchCancelled(SearchLimit):
    """The user explicitly stopped the search."""


class Budget:
    def __init__(self, seconds=None, max_nodes=500_000, cancel_event=None,
                 solution_limit=5, max_attempts=400):
        self.deadline = None if seconds is None else perf_counter() + seconds
        self.cancel_event = cancel_event
        self.solution_limit = solution_limit
        self.max_attempts = max_attempts
        self.max_nodes = max_nodes
        self.nodes = 0

    def tick(self):
        self.nodes += 1
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise SearchCancelled('Generation stopped.')
        if ((self.max_nodes is not None and self.nodes > self.max_nodes)
                or (self.deadline is not None and perf_counter() > self.deadline)):
            raise SearchLimit('Search limit reached.')


@dataclass
class SolveResult:
    solutions: List[Placement]
    elapsed_ms: float
    nodes: int
    cache_hits: int = 0
    limit_reached: bool = False

    @property
    def classification(self):
        return ('none', 'unique', 'multiple')[min(2, len(self.solutions))]


@dataclass
class GenerationResult:
    puzzle: Optional[Puzzle]
    witness: Optional[Placement]
    uniqueness_verified: bool
    attempts: int
    repairs: int
    solver_calls: int
    elapsed_ms: float
    status: str


class Solver(ABC):
    @abstractmethod
    def solve(self, puzzle: Puzzle, budget: Budget) -> SolveResult:
        """Return up to budget.solution_limit solutions; raise SearchLimit if classification is unknown."""


class Generator(ABC):
    @abstractmethod
    def generate(self, n, unique, rng, solver: Solver, budget: Budget) -> GenerationResult:
        """Construct a puzzle under the generation constraints."""


@dataclass
class StrategyInfo:
    key: str
    name: str
    description: str
    factory: type = field(repr=False)


class Registry:
    def __init__(self, interface):
        self.interface = interface
        self._items = {}

    def register(self, key, name, description):
        def decorate(cls):
            if key in self._items:
                raise ValueError('Duplicate strategy: ' + key)
            if not issubclass(cls, self.interface):
                raise TypeError('Strategy does not implement the required interface.')
            self._items[key] = StrategyInfo(key, name, description, cls)
            return cls
        return decorate

    def create(self, key):
        if key not in self._items:
            raise ValueError('Unknown algorithm: ' + str(key))
        return self._items[key].factory()

    def describe(self):
        return [dict(key=x.key, name=x.name, description=x.description) for x in self._items.values()]


SOLVERS = Registry(Solver)
GENERATORS = Registry(Generator)
