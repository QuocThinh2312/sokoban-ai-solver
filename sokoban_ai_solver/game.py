from typing import List, Optional, Tuple

from .constants import ACTIONS
from .level import Level
from .state import Position, State, is_goal

def apply_action(state: State, action: str, level: Level) -> Optional[State]:
    dr: int
    dc: int
    dr, dc = ACTIONS[action]
    
    pr: int
    pc: int
    pr, pc = state.player
    
    target: Position = (pr + dr, pc + dc)

    if level.is_wall(target):
        return None

    if target in state.boxes:
        beyond: Position = (target[0] + dr, target[1] + dc)
        if level.is_wall(beyond) or beyond in state.boxes:
            return None
        
        new_boxes: Tuple[Position, ...] = tuple(sorted(b if b != target else beyond for b in state.boxes))
        
        h: int = state.zobrist_hash
        h ^= level.zobrist_table.player_keys[state.player]
        h ^= level.zobrist_table.player_keys[target]
        h ^= level.zobrist_table.box_keys[target]
        h ^= level.zobrist_table.box_keys[beyond]
        
        return State(target, new_boxes, h)

    h_move: int = state.zobrist_hash
    h_move ^= level.zobrist_table.player_keys[state.player]
    h_move ^= level.zobrist_table.player_keys[target]
    
    return State(target, state.boxes, h_move)


class GameSession:
    def __init__(self, level: Level) -> None:
        self.level: Level = level
        self.state: State = level.initial_state()
        self.history: List[State] = []
        self.steps_count: int = 0

    def restart(self) -> None:
        self.state = self.level.initial_state()
        self.history.clear()
        self.steps_count = 0

    def move(self, action: str) -> bool:
        new_state: Optional[State] = apply_action(self.state, action, self.level)
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