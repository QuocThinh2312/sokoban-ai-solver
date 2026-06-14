from dataclasses import dataclass
from typing import FrozenSet, Tuple, TypeAlias

Position: TypeAlias = Tuple[int, int]

@dataclass(frozen=True, slots=True)
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
        return (
            self.zobrist_hash == other.zobrist_hash
            and self.player == other.player
            and self.boxes == other.boxes
        )

def is_goal(state: State, goals: FrozenSet[Position]) -> bool:
    return all(b in goals for b in state.boxes)