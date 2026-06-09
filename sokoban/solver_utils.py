from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

from .constants import ACTIONS
from .level import Level
from .state import Position, State
from .game import apply_action


@dataclass
class SolveResult:
    algorithm: str
    found: bool
    actions: List[str] = field(default_factory=list)
    expanded: int = 0
    elapsed_ms: float = 0.0
    memory_kb: float = 0.0
    message: str = ""

    @property
    def steps(self) -> int:
        return len(self.actions)


def get_neighbors(state: State, level: Level) -> Iterable[Tuple[str, State]]:
    for action in ACTIONS:
        new_state = apply_action(state, action, level)
        if new_state is not None:
            yield action, new_state


def manhattan_distance(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def heuristic(state: State, level: Level) -> int:
    boxes = list(state.boxes)
    goals = list(level.goals)
    n = len(boxes)
    
    if n == 0:
        return 0
        
    cost_matrix = np.zeros((n, n), dtype=int)
    
    for i in range(n):
        for j in range(n):
            cost_matrix[i, j] = manhattan_distance(boxes[i], goals[j])
            
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    return int(cost_matrix[row_ind, col_ind].sum())


def has_deadlock(state: State, level: Level) -> bool:
    return any(box in level.deadlocks for box in state.boxes)


def reconstruct_path(parent: dict, end_key) -> List[str]:
    actions: List[str] = []
    cur = end_key
    while parent[cur] is not None:
        prev_key, action = parent[cur]
        actions.append(action)
        cur = prev_key
    actions.reverse()
    return actions