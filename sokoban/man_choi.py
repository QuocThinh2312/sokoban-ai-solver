"""Tải và phân tích màn chơi cho Sokoban."""

from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, List, Optional

from .hang_so import (
    BOX,
    BOX_ON_GOAL,
    GOAL,
    PLAYER,
    PLAYER_ON_GOAL,
    WALL,
)
from .trang_thai import Position, State


@dataclass(frozen=True)
class Level:
    name: str
    width: int
    height: int
    walls: FrozenSet[Position]
    goals: FrozenSet[Position]
    initial_player: Position
    initial_boxes: FrozenSet[Position]

    def trang_thai_dau(self) -> State:
        return State(self.initial_player, self.initial_boxes)

    def la_tuong(self, pos: Position) -> bool:
        return pos in self.walls


def phan_tich_man(text: str, name: str = "level") -> Level:
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise ValueError("Màn chơi rỗng")

    height = len(lines)
    width = max(len(line) for line in lines)

    walls: List[Position] = []
    goals: List[Position] = []
    boxes: List[Position] = []
    player: Optional[Position] = None

    for r, line in enumerate(lines):
        padded = line.ljust(width)
        for c, ch in enumerate(padded):
            pos = (r, c)
            if ch == WALL:
                walls.append(pos)
            elif ch == GOAL:
                goals.append(pos)
            elif ch == BOX:
                boxes.append(pos)
            elif ch == BOX_ON_GOAL:
                boxes.append(pos)
                goals.append(pos)
            elif ch == PLAYER:
                if player is not None:
                    raise ValueError("Có nhiều hơn một người chơi trong màn")
                player = pos
            elif ch == PLAYER_ON_GOAL:
                if player is not None:
                    raise ValueError("Có nhiều hơn một người chơi trong màn")
                player = pos
                goals.append(pos)

    if player is None:
        raise ValueError(f"Không có người chơi ('@' hoặc '+') trong màn {name}")
    if len(boxes) != len(goals):
        raise ValueError(
            f"Màn {name}: số thùng ({len(boxes)}) "
            f"khác số đích ({len(goals)})"
        )

    return Level(
        name=name,
        width=width,
        height=height,
        walls=frozenset(walls),
        goals=frozenset(goals),
        initial_player=player,
        initial_boxes=frozenset(boxes),
    )


def tai_file_man(path: Path) -> Level:
    text = path.read_text(encoding="utf-8")
    return phan_tich_man(text, name=path.stem)


def tai_man_tu_thu_muc(directory: Path) -> List[Level]:
    files = sorted(p for p in directory.iterdir() if p.suffix == ".txt")
    return [tai_file_man(p) for p in files]
