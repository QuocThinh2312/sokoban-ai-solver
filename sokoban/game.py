from typing import List, Optional

from .constants import ACTIONS
from .level import Level
from .state import State, is_goal

def apply_action(state: State, action: str, level: Level) -> Optional[State]:
    dr, dc = ACTIONS[action]
    pr, pc = state.player
    target = (pr + dr, pc + dc)

    if level.is_wall(target):
        return None

    if target in state.boxes:
        beyond = (target[0] + dr, target[1] + dc)
        if level.is_wall(beyond) or beyond in state.boxes:
            return None
        
        new_boxes = list(state.boxes)
        new_boxes.remove(target)
        new_boxes.append(beyond)
        new_boxes.sort() 
        
        h = state.zobrist_hash
        h ^= level.zobrist_table.player_keys[state.player]
        h ^= level.zobrist_table.player_keys[target]
        h ^= level.zobrist_table.box_keys[target]
        h ^= level.zobrist_table.box_keys[beyond]
        
        return State(target, tuple(new_boxes), h)

    h = state.zobrist_hash
    h ^= level.zobrist_table.player_keys[state.player]
    h ^= level.zobrist_table.player_keys[target]
    
    return State(target, state.boxes, h)


class GameSession:
    def __init__(self, level: Level):
        self.level = level
        self.state: State = level.initial_state()
        self.history: List[State] = []
        self.steps_count: int = 0

    def restart(self) -> None:
        self.state = self.level.initial_state()
        self.history = []
        self.steps_count = 0

    def move(self, action: str) -> bool:
        new_state = apply_action(self.state, action, self.level)
        if new_state is None:
            return False
        self.history.append(self.state)
        self.state = new_state
        self.steps_count += 1
        return True

    def undo(self) -> bool:
        if not self.history:
            return False
        self.state = self.history.pop()
        self.steps_count = max(0, self.steps_count - 1)
        return True

    def has_won(self) -> bool:
        return is_goal(self.state, self.level.goals)