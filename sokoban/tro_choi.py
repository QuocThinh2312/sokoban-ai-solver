"""Logic trò chơi Sokoban: áp dụng nước đi và theo dõi trạng thái chơi."""

from typing import List, Optional

from .hang_so import ACTIONS
from .man_choi import Level
from .trang_thai import State, la_dich


def ap_dung_nuoc_di(state: State, action: str, level: Level) -> Optional[State]:
    """Thử áp dụng một nước đi. Trả về trạng thái mới hoặc None nếu không hợp lệ."""
    dr, dc = ACTIONS[action]
    pr, pc = state.player
    target = (pr + dr, pc + dc)

    if level.la_tuong(target):
        return None

    if target in state.boxes:
        beyond = (target[0] + dr, target[1] + dc)
        if level.la_tuong(beyond) or beyond in state.boxes:
            return None
        new_boxes = set(state.boxes)
        new_boxes.discard(target)
        new_boxes.add(beyond)
        return State(target, frozenset(new_boxes))

    return State(target, state.boxes)


class GameSession:
    """Theo dõi phiên chơi tương tác của người chơi cho một màn."""

    def __init__(self, level: Level):
        self.level = level
        self.state: State = level.trang_thai_dau()
        self.lich_su: List[State] = []
        self.so_nuoc_di: int = 0

    def choi_lai(self) -> None:
        self.state = self.level.trang_thai_dau()
        self.lich_su = []
        self.so_nuoc_di = 0

    def di_chuyen(self, action: str) -> bool:
        new_state = ap_dung_nuoc_di(self.state, action, self.level)
        if new_state is None:
            return False
        self.lich_su.append(self.state)
        self.state = new_state
        self.so_nuoc_di += 1
        return True

    def quay_lai(self) -> bool:
        if not self.lich_su:
            return False
        self.state = self.lich_su.pop()
        self.so_nuoc_di = max(0, self.so_nuoc_di - 1)
        return True

    def da_thang(self) -> bool:
        return la_dich(self.state, self.level.goals)
