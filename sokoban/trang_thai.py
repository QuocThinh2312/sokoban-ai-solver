"""Biểu diễn trạng thái cho thuật toán tìm kiếm Sokoban."""

from dataclasses import dataclass
from typing import FrozenSet, Tuple

Position = Tuple[int, int]


@dataclass(frozen=True)
class State:
    player: Position
    boxes: FrozenSet[Position]

    def khoa(self) -> Tuple[Position, Tuple[Position, ...]]:
        """Khóa băm dùng để so sánh và lưu trong tập đã thăm."""
        return (self.player, tuple(sorted(self.boxes)))

    def __hash__(self) -> int:
        return hash(self.khoa())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, State):
            return NotImplemented
        return self.khoa() == other.khoa()


def la_dich(state: State, goals: FrozenSet[Position]) -> bool:
    """Trả về True nếu mọi thùng đều nằm đúng ở đích."""
    return state.boxes == goals
