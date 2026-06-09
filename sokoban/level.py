from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, List, Optional, Tuple

from .constants import (
    BOX,
    BOX_ON_GOAL,
    GOAL,
    PLAYER,
    PLAYER_ON_GOAL,
    WALL,
)
from .state import Position, State


@dataclass(frozen=True)
class Level:
    name: str
    width: int
    height: int
    walls: FrozenSet[Position]
    goals: FrozenSet[Position]
    deadlocks: FrozenSet[Position]  
    initial_player: Position
    initial_boxes: Tuple[Position, ...]

    def initial_state(self) -> State:
        return State(self.initial_player, self.initial_boxes)

    def is_wall(self, pos: Position) -> bool:
        return pos in self.walls


def parse_level(text: str, name: str = "level") -> Level:
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise ValueError("Empty level")

    height = len(lines)
    width = max(len(line) for line in lines)

    walls_list: List[Position] = []
    goals_list: List[Position] = []
    boxes_list: List[Position] = []
    player: Optional[Position] = None

    for r, line in enumerate(lines):
        padded = line.ljust(width)
        for c, ch in enumerate(padded):
            pos = (r, c)
            if ch == WALL:
                walls_list.append(pos)
            elif ch == GOAL:
                goals_list.append(pos)
            elif ch == BOX:
                boxes_list.append(pos)
            elif ch == BOX_ON_GOAL:
                boxes_list.append(pos)
                goals_list.append(pos)
            elif ch == PLAYER:
                if player is not None:
                    raise ValueError("More than one player in the level")
                player = pos
            elif ch == PLAYER_ON_GOAL:
                if player is not None:
                    raise ValueError("More than one player in the level")
                player = pos
                goals_list.append(pos)

    if player is None:
        raise ValueError(f"No player in level {name}")
    if len(boxes_list) != len(goals_list):
        raise ValueError(f"Level {name}: number of boxes ({len(boxes_list)}) does not match number of goals ({len(goals_list)})")

    walls_set = frozenset(walls_list)
    goals_set = frozenset(goals_list)
    
    alive_cells = set(goals_list)
    queue_positions = deque(goals_list)

    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    while queue_positions:
        curr_r, curr_c = queue_positions.popleft()

        for dr, dc in directions:
            prev_box = (curr_r - dr, curr_c - dc)
            prev_player = (curr_r - 2 * dr, curr_c - 2 * dc)

            if prev_box not in walls_set and prev_player not in walls_set:
                if prev_box not in alive_cells:
                    alive_cells.add(prev_box)
                    queue_positions.append(prev_box)

    deadlocks_list: List[Position] = []
    for r in range(height):
        for c in range(width):
            pos = (r, c)
            if pos not in walls_set and pos not in alive_cells:
                deadlocks_list.append(pos)

    return Level(
        name=name,
        width=width,
        height=height,
        walls=walls_set,
        goals=goals_set,
        deadlocks=frozenset(deadlocks_list),
        initial_player=player,
        initial_boxes=tuple(sorted(boxes_list)), 
    )

def load_level_file(path: Path) -> Level:
    text = path.read_text(encoding="utf-8")
    return parse_level(text, name=path.stem)

def load_levels_from_directory(directory: Path) -> List[Level]:
    files = sorted(p for p in directory.iterdir() if p.suffix == ".txt")
    return [load_level_file(p) for p in files]