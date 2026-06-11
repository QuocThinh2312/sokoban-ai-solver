import random
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple, Dict, Optional, Set, Deque

from .constants import ACTIONS
from .level import Level
from .state import Position, State

_ACTION_TO_INT = {act: i for i, act in enumerate(ACTIONS.keys())}
_INT_TO_ACTION = {i: act for i, act in enumerate(ACTIONS.keys())}

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

def _get_level_id(level: Level) -> str:
    return f"{level.name}_{hash(frozenset(level.walls))}_{hash(frozenset(level.goals))}"

_level_distances: Dict[str, Dict[Position, Dict[Position, int]]] = {}
_level_sorted_goals: Dict[str, Tuple[Position, ...]] = {}

def precompute_distances(level: Level) -> Dict[Position, Dict[Position, int]]:
    lvl_id = _get_level_id(level)
    if lvl_id in _level_distances:
        return _level_distances[lvl_id]
        
    dist_map: Dict[Position, Dict[Position, int]] = {}
    action_vectors = list(ACTIONS.values())
    
    for goal in level.goals:
        goal_distances: Dict[Position, int] = {}
        dist_map[goal] = goal_distances
        
        state_cost: Dict[Tuple[Position, Position], int] = {}
        queue: Deque[Tuple[Position, Position]] = deque()
        
        gr, gc = goal
        for dr, dc in action_vectors:
            p_pos = (gr + dr, gc + dc)
            if not level.is_wall(p_pos):
                state = (goal, p_pos)
                state_cost[state] = 0
                queue.append(state)
        
        while queue:
            b_pos, p_pos = queue.popleft()
            cost = state_cost[(b_pos, p_pos)]
            
            if b_pos not in goal_distances:
                goal_distances[b_pos] = cost
            
            pr, pc = p_pos
            for dr, dc in action_vectors:
                new_p = (pr + dr, pc + dc)
                if new_p != b_pos and not level.is_wall(new_p):
                    new_state = (b_pos, new_p)
                    if new_state not in state_cost or cost < state_cost[new_state]:
                        state_cost[new_state] = cost
                        queue.appendleft(new_state) 
                        
            br, bc = b_pos
            dr, dc = br - pr, bc - pc
            if abs(dr) + abs(dc) == 1:
                new_b = p_pos
                new_p = (pr - dr, pc - dc)
                if not level.is_wall(new_p):
                    new_state = (new_b, new_p)
                    new_cost = cost + 1
                    if new_state not in state_cost or new_cost < state_cost[new_state]:
                        state_cost[new_state] = new_cost
                        queue.append(new_state) 
                        
    _level_distances[lvl_id] = dist_map
    return dist_map

_heuristic_cache: Dict[Tuple[str, Tuple[Position, ...]], int] = {}
_deadlock_cache: Dict[Tuple[str, Tuple[Position, ...]], bool] = {}

def _compute_heuristic_value(boxes: Tuple[Position, ...], goals: Tuple[Position, ...], lvl_id: str) -> int:
    if not boxes:
        return 0
    dist_map = _level_distances[lvl_id]
    total_cost = 0
    
    for b in boxes:
        min_dist = min(dist_map[g].get(b, 99999) for g in goals)
        if min_dist >= 99999:
            return 999999 
        total_cost += min_dist
        
    return total_cost

def heuristic(state: State, level: Level) -> int:
    precompute_distances(level)
    lvl_id = _get_level_id(level)
    
    cache_key = (lvl_id, state.boxes)
    if cache_key in _heuristic_cache:
        return _heuristic_cache[cache_key]
    
    if lvl_id not in _level_sorted_goals:
        _level_sorted_goals[lvl_id] = tuple(sorted(level.goals))
        
    base_h = _compute_heuristic_value(state.boxes, _level_sorted_goals[lvl_id], lvl_id)
    
    if base_h >= 99999:
        base_h = 999999
        
    _heuristic_cache[cache_key] = base_h
    return base_h

def greedy_heuristic(state: State, level: Level) -> float:
    base_h = heuristic(state, level)
    
    if base_h >= 99999:
        return 999999.0

    boxes_set = set(state.boxes)
    unsolved_boxes = boxes_set - level.goals
    unsolved_count = len(unsolved_boxes)

    player_dist = 0
    if unsolved_boxes:
        pr, pc = state.player
        player_dist = min(abs(pr - br) + abs(pc - bc) for br, bc in unsolved_boxes)

    penalty = 0
    for br, bc in unsolved_boxes:
        v_wall = level.is_wall((br - 1, bc)) or level.is_wall((br + 1, bc))
        h_wall = level.is_wall((br, bc - 1)) or level.is_wall((br, bc + 1))
        
        if v_wall and h_wall:
            penalty += 6
        elif v_wall or h_wall:
            penalty += 2

    jitter = random.uniform(0.0, 0.5)
    
    return float(base_h + (unsolved_count * 10) + player_dist + penalty + jitter)

def is_freeze_deadlock(boxes_set: Set[Position], level: Level) -> bool:
    frozen_boxes: Set[Position] = set()
    changed: bool = True
    
    while changed:
        changed = False
        for box in boxes_set:
            if box in frozen_boxes:
                continue
            
            r, c = box
            
            v_blocked: bool = (level.is_wall((r-1, c)) or (r-1, c) in frozen_boxes) or \
                              (level.is_wall((r+1, c)) or (r+1, c) in frozen_boxes)
                           
            h_blocked: bool = (level.is_wall((r, c-1)) or (r, c-1) in frozen_boxes) or \
                              (level.is_wall((r, c+1)) or (r, c+1) in frozen_boxes)
                           
            if v_blocked and h_blocked:
                frozen_boxes.add(box)
                changed = True
                
                if box not in level.goals:
                    return True
                    
    return False


def has_deadlock(state: State, level: Level) -> bool:
    lvl_id = _get_level_id(level)
    cache_key = (lvl_id, state.boxes)
    if cache_key in _deadlock_cache:
        return _deadlock_cache[cache_key]

    if any(box in level.deadlocks for box in state.boxes):
        _deadlock_cache[cache_key] = True
        return True
        
    boxes_set = set(state.boxes)
    
    for r, c in state.boxes:
        for dr, dc in [(-1, -1), (-1, 0), (0, -1), (0, 0)]:
            tl_r, tl_c = r + dr, c + dc
            is_solid = True
            boxes_in_2x2 = []
            
            for i in range(2):
                for j in range(2):
                    curr_r, curr_c = tl_r + i, tl_c + j
                    if (curr_r, curr_c) in boxes_set:
                        boxes_in_2x2.append((curr_r, curr_c))
                    elif not level.is_wall((curr_r, curr_c)):
                        is_solid = False
                        break
                if not is_solid:
                    break
                    
            if is_solid:
                if any(b not in level.goals for b in boxes_in_2x2):
                    _deadlock_cache[cache_key] = True
                    return True

    if is_freeze_deadlock(boxes_set, level):
        _deadlock_cache[cache_key] = True
        return True

    _deadlock_cache[cache_key] = False
    return False

_canonical_cache: Dict[Tuple[Position, Tuple[Position, ...]], Position] = {}

def _get_canonical_player(start_pos: Position, boxes_set: Set[Position], level: Level) -> Position:
    boxes_tup = tuple(sorted(boxes_set))
    cache_key = (start_pos, boxes_tup)
    
    if cache_key in _canonical_cache:
        return _canonical_cache[cache_key]

    queue = [start_pos]
    visited = {start_pos}
    min_pos = start_pos
    is_wall = level.is_wall
    
    for r, c in queue:
        if (r, c) < min_pos:
            min_pos = (r, c)
        for nr, nc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):
            nxt = (nr, nc)
            if nxt not in visited and nxt not in boxes_set and not is_wall(nxt):
                visited.add(nxt)
                queue.append(nxt)
                
    for v in visited:
        _canonical_cache[(v, boxes_tup)] = min_pos
        
    return min_pos

def get_macro_neighbors(state: State, level: Level) -> Iterable[Tuple[Tuple[int, ...], State]]:
    queue: Deque[Tuple[Position, Tuple[int, ...]]] = deque([(state.player, ())])
    visited_player: Set[Position] = {state.player}
    
    boxes_set = set(state.boxes) 
    
    while queue:
        curr_p, path = queue.popleft()
        
        for action, (dr, dc) in ACTIONS.items():
            target = (curr_p[0] + dr, curr_p[1] + dc)
            
            if target in boxes_set:
                beyond = (target[0] + dr, target[1] + dc)
                
                if not level.is_wall(beyond) and beyond not in boxes_set:
                    act_int = _ACTION_TO_INT[action]
                    
                    new_boxes = tuple(sorted(b if b != target else beyond for b in state.boxes))
                    new_boxes_set = set(new_boxes)
                    
                    canonical_p = _get_canonical_player(target, new_boxes_set, level)
                    
                    h_val = level.zobrist_table.player_keys[canonical_p]
                    for b in new_boxes:
                        h_val ^= level.zobrist_table.box_keys[b]
                        
                    yield path + (act_int,), State(target, new_boxes, h_val)
                    
            elif not level.is_wall(target):
                if target not in visited_player:
                    visited_player.add(target)
                    act_int = _ACTION_TO_INT[action]
                    queue.append((target, path + (act_int,)))

def reconstruct_path(parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]], curr_key: Tuple[Position, Tuple[Position, ...]]) -> List[str]:
    final_path: List[str] = []
    
    while curr_key in parent:
        parent_info = parent[curr_key]
        if parent_info is None:
            break
        curr_key, action_segment = parent_info
        final_path.extend(reversed([_INT_TO_ACTION[act_int] for act_int in action_segment]))
        
    final_path.reverse()
    return final_path