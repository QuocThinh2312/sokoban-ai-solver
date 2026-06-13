import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple, Final, Set, Deque

from .constants import (
    BOX,
    BOX_ON_GOAL,
    GOAL,
    PLAYER,
    PLAYER_ON_GOAL,
    WALL,
)
from .state import Position, State

_ZOBRIST_SEED: Final[int] = 42
_PULL_DIRECTIONS: Final[List[Tuple[int, int]]] = [(-1, 0), (1, 0), (0, -1), (0, 1)]

@dataclass(frozen=True, slots=True)
class ZobristTable:
    player_keys: Dict[Position, int]
    box_keys: Dict[Position, int]

    def compute(self, player: Position, boxes: Tuple[Position, ...]) -> int:
        h: int = self.player_keys.get(player, 0)
        for b in boxes:
            h ^= self.box_keys.get(b, 0)
        return h

def generate_zobrist_table(width: int, height: int) -> ZobristTable:
    rng: random.Random = random.Random(_ZOBRIST_SEED) 
    p_keys: Dict[Position, int] = {}
    b_keys: Dict[Position, int] = {}
    for r in range(height):
        for c in range(width):
            pos: Position = (r, c)
            p_keys[pos] = rng.getrandbits(64)
            b_keys[pos] = rng.getrandbits(64)
    return ZobristTable(p_keys, b_keys)

@dataclass(frozen=True, slots=True)
class Level:
    name: str
    width: int
    height: int
    walls: FrozenSet[Position]
    goals: FrozenSet[Position]
    deadlocks: FrozenSet[Position]  
    initial_player: Position
    initial_boxes: Tuple[Position, ...]
    zobrist_table: ZobristTable

    def initial_state(self) -> State:
        h: int = self.zobrist_table.compute(self.initial_player, self.initial_boxes)
        return State(self.initial_player, self.initial_boxes, h)

    def is_wall(self, pos: Position) -> bool:
        return pos in self.walls

def parse_level(text: str, name: str = "level") -> Level:
    lines: List[str] = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise ValueError("Empty level")

    height: int = len(lines)
    width: int = max(len(line) for line in lines)

    walls_list: List[Position] = []
    goals_list: List[Position] = []
    boxes_list: List[Position] = []
    player: Optional[Position] = None

    for r, line in enumerate(lines):
        padded: str = line.ljust(width)
        for c, ch in enumerate(padded):
            pos: Position = (r, c)
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
        
    if len(boxes_list) == 0 or len(goals_list) == 0:
        raise ValueError(f"Level {name} must have at least one box and one goal.")

    walls_set: FrozenSet[Position] = frozenset(walls_list)
    goals_set: FrozenSet[Position] = frozenset(goals_list)
    
    alive_cells: Set[Position] = set(goals_list)
    queue_positions: Deque[Position] = deque(goals_list)

    while queue_positions:
        curr_r: int
        curr_c: int
        curr_r, curr_c = queue_positions.popleft()

        for dr, dc in _PULL_DIRECTIONS:
            prev_box: Position = (curr_r - dr, curr_c - dc)
            prev_player: Position = (curr_r - 2 * dr, curr_c - 2 * dc)

            if (0 <= prev_box[0] < height and 0 <= prev_box[1] < width and
                0 <= prev_player[0] < height and 0 <= prev_player[1] < width):
                
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

    zobrist: ZobristTable = generate_zobrist_table(width, height)

    return Level(
        name=name,
        width=width,
        height=height,
        walls=walls_set,
        goals=goals_set,
        deadlocks=frozenset(deadlocks_list),
        initial_player=player,
        initial_boxes=tuple(sorted(boxes_list)), 
        zobrist_table=zobrist
    )

def load_level_file(path: Path) -> Level:
    text: str = path.read_text(encoding="utf-8")
    return parse_level(text, name=path.stem)

def load_levels_from_directory(directory: Path) -> List[Level]:
    files: List[Path] = sorted(p for p in directory.iterdir() if p.suffix == ".txt")
    return [load_level_file(p) for p in files]