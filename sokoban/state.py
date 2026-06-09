from dataclasses import dataclass
from typing import FrozenSet, Tuple

Position = Tuple[int, int]

@dataclass(frozen=True)
class State:
    player: Position
    boxes: Tuple[Position, ...] 

    def get_key(self) -> Tuple[Position, Tuple[Position, ...]]:
        return (self.player, self.boxes)

    def __hash__(self) -> int:
        return hash(self.get_key())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, State):
            return NotImplemented
        return self.get_key() == other.get_key()

def is_goal(state: State, goals: FrozenSet[Position]) -> bool:
    return len(state.boxes) == len(goals) and all(b in goals for b in state.boxes)