"""Lõi bộ giải: sinh trạng thái kề, tính heuristic, phát hiện kẹt góc."""

from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

from .hang_so import ACTIONS
from .man_choi import Level
from .trang_thai import Position, State
from .tro_choi import ap_dung_nuoc_di


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


def sinh_ke(state: State, level: Level) -> Iterable[Tuple[str, State]]:
    """Sinh các trạng thái kề từ một trạng thái."""
    for action in ACTIONS:
        new_state = ap_dung_nuoc_di(state, action, level)
        if new_state is not None:
            yield action, new_state


def khoang_cach_manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def heuristic(state: State, level: Level) -> int:
    """Tổng khoảng cách Manhattan nhỏ nhất từ mỗi thùng tới một đích."""
    goals = level.goals
    total = 0
    for box in state.boxes:
        if box in goals:
            continue
        total += min(khoang_cach_manhattan(box, g) for g in goals)
    return total


def la_deadlock_goc(box: Position, level: Level) -> bool:
    """Thùng không ở đích và bị kẹt vào góc tường thì không thể đẩy được nữa."""
    if box in level.goals:
        return False
    r, c = box
    up = (r - 1, c) in level.walls
    down = (r + 1, c) in level.walls
    left = (r, c - 1) in level.walls
    right = (r, c + 1) in level.walls
    return (up and left) or (up and right) or (down and left) or (down and right)


def co_deadlock(state: State, level: Level) -> bool:
    for box in state.boxes:
        if la_deadlock_goc(box, level):
            return True
    return False


def dung_lai_nuoc_di(parent: dict, end_key) -> List[str]:
    """Lần ngược bảng cha để lấy danh sách nước đi từ đầu tới đích."""
    actions: List[str] = []
    cur = end_key
    while parent[cur] is not None:
        prev_key, action = parent[cur]
        actions.append(action)
        cur = prev_key
    actions.reverse()
    return actions
