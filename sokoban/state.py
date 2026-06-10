from dataclasses import dataclass
from typing import FrozenSet, Tuple

Position = Tuple[int, int]

@dataclass(frozen=True)
class State:
    player: Position
    boxes: Tuple[Position, ...]
    zobrist_hash: int

    def get_key(self) -> Tuple[Position, Tuple[Position, ...]]:
        return (self.player, self.boxes)

    def __hash__(self) -> int:
        return self.zobrist_hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, State):
            return NotImplemented
        return self.zobrist_hash == other.zobrist_hash and self.get_key() == other.get_key()

def is_goal(state: State, goals: FrozenSet[Position]) -> bool:
    return all(b in goals for b in state.boxes)