import random
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple, Dict, Optional, Set, Deque, Final, TypeAlias, Mapping

from .constants import ACTIONS
from .level import Level
from .state import Position, State

_ACTION_TO_INT: Final[Dict[str, int]] = {act: i for i, act in enumerate(ACTIONS.keys())}
_INT_TO_ACTION: Final[Dict[int, str]] = {i: act for i, act in enumerate(ACTIONS.keys())}

_INFINITY: Final[int] = 999999
_SUB_INFINITY: Final[int] = 99999

StateKey: TypeAlias = Tuple[Position, Tuple[Position, ...]]
PathSegment: TypeAlias = Tuple[int, ...]
ParentMap: TypeAlias = Dict[StateKey, Optional[Tuple[StateKey, PathSegment]]]

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
    lvl_id: str = _get_level_id(level)
    if lvl_id in _level_distances:
        return _level_distances[lvl_id]
        
    dist_map: Dict[Position, Dict[Position, int]] = {}
    action_vectors: List[Tuple[int, int]] = list(ACTIONS.values())
    
    for goal in level.goals:
        goal_distances: Dict[Position, int] = {}
        dist_map[goal] = goal_distances
        
        state_cost: Dict[Tuple[Position, Position], int] = {}
        queue: Deque[Tuple[Position, Position]] = deque()
        
        gr: int
        gc: int
        gr, gc = goal
        for dr, dc in action_vectors:
            p_pos: Position = (gr + dr, gc + dc)
            if not level.is_wall(p_pos):
                state_tup: Tuple[Position, Position] = (goal, p_pos)
                state_cost[state_tup] = 0
                queue.append(state_tup)
        
        while queue:
            b_pos: Position
            p_pos: Position
            b_pos, p_pos = queue.popleft()
            cost: int = state_cost[(b_pos, p_pos)]
            
            if b_pos not in goal_distances or cost < goal_distances[b_pos]:
                goal_distances[b_pos] = cost
            
            pr: int
            pc: int
            pr, pc = p_pos
            for dr, dc in action_vectors:
                new_p: Position = (pr + dr, pc + dc)
                if new_p != b_pos and not level.is_wall(new_p):
                    new_state: Tuple[Position, Position] = (b_pos, new_p)
                    new_cost: int = cost + 1
                    if new_state not in state_cost or new_cost < state_cost[new_state]:
                        state_cost[new_state] = new_cost
                        queue.append(new_state) 
                        
            br: int
            bc: int
            br, bc = b_pos
            db_r: int = br - pr
            db_c: int = bc - pc
            if abs(db_r) + abs(db_c) == 1:
                new_b: Position = p_pos
                new_p_push: Position = (pr - db_r, pc - db_c)
                if not level.is_wall(new_p_push):
                    new_state_push: Tuple[Position, Position] = (new_b, new_p_push)
                    new_cost_push: int = cost + 1
                    if new_state_push not in state_cost or new_cost_push < state_cost[new_state_push]:
                        state_cost[new_state_push] = new_cost_push
                        queue.append(new_state_push) 
                        
    _level_distances[lvl_id] = dist_map
    return dist_map

_heuristic_cache: Dict[Tuple[str, Tuple[Position, ...]], int] = {}
_deadlock_cache: Dict[Tuple[str, Tuple[Position, ...]], bool] = {}

def _compute_heuristic_value(boxes: Tuple[Position, ...], goals: Tuple[Position, ...], lvl_id: str) -> int:
    if not boxes:
        return 0
    dist_map: Mapping[Position, Mapping[Position, int]] = _level_distances[lvl_id]
    n: int = len(boxes)
    memo: Dict[Tuple[int, int], int] = {}

    def dfs(b_idx: int, g_mask: int) -> int:
        if b_idx == n:
            return 0
        state_key: Tuple[int, int] = (b_idx, g_mask)
        if state_key in memo:
            return memo[state_key]
            
        res: int = _INFINITY
        b: Position = boxes[b_idx]
        for g_idx in range(n):
            if not (g_mask & (1 << g_idx)):
                d: int = dist_map[goals[g_idx]].get(b, _SUB_INFINITY)
                if d < _SUB_INFINITY:
                    cost: int = d + dfs(b_idx + 1, g_mask | (1 << g_idx))
                    if cost < res:
                        res = cost
        memo[state_key] = res
        return res

    val: int = dfs(0, 0)
    return val if val < _INFINITY else _INFINITY

def heuristic(state: State, level: Level) -> int:
    precompute_distances(level)
    lvl_id: str = _get_level_id(level)
    sorted_boxes: Tuple[Position, ...] = tuple(sorted(state.boxes))
    cache_key: Tuple[str, Tuple[Position, ...]] = (lvl_id, sorted_boxes)
    
    base_h: int
    if cache_key in _heuristic_cache:
        base_h = _heuristic_cache[cache_key]
    else:
        if lvl_id not in _level_sorted_goals:
            _level_sorted_goals[lvl_id] = tuple(sorted(level.goals))
        base_h = _compute_heuristic_value(sorted_boxes, _level_sorted_goals[lvl_id], lvl_id)
        _heuristic_cache[cache_key] = base_h
        
    if base_h >= _INFINITY:
        return _INFINITY
        
    unsolved: List[Position] = [b for b in state.boxes if b not in level.goals]
    if unsolved:
        pr: int
        pc: int
        pr, pc = state.player
        return base_h + min(abs(pr - b[0]) + abs(pc - b[1]) for b in unsolved)
        
    return base_h

def greedy_heuristic(state: State, level: Level) -> float:
    base_h: int = heuristic(state, level)
    
    if base_h >= _SUB_INFINITY:
        return float(_INFINITY)

    boxes_set: Set[Position] = set(state.boxes)
    unsolved_boxes: Set[Position] = boxes_set - level.goals
    unsolved_count: int = len(unsolved_boxes)

    player_dist: int = 0
    if unsolved_boxes:
        pr: int
        pc: int
        pr, pc = state.player
        player_dist = min(abs(pr - b[0]) + abs(pc - b[1]) for b in unsolved_boxes)

    penalty: int = 0
    for br, bc in unsolved_boxes:
        v_wall: bool = level.is_wall((br - 1, bc)) or level.is_wall((br + 1, bc))
        h_wall: bool = level.is_wall((br, bc - 1)) or level.is_wall((br, bc + 1))
        
        if v_wall and h_wall:
            penalty += 6
        elif v_wall or h_wall:
            penalty += 2

    jitter: float = random.uniform(0.0, 0.5)
    
    return float(base_h + (unsolved_count * 10) + player_dist + penalty + jitter)

def is_freeze_deadlock(boxes_set: Set[Position], level: Level) -> bool:
    frozen_boxes: Set[Position] = set()
    changed: bool = True
    
    while changed:
        changed = False
        for box in boxes_set:
            if box in frozen_boxes:
                continue
            
            r: int
            c: int
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
    lvl_id: str = _get_level_id(level)
    cache_key: Tuple[str, Tuple[Position, ...]] = (lvl_id, state.boxes)
    if cache_key in _deadlock_cache:
        return _deadlock_cache[cache_key]

    if any(box in level.deadlocks for box in state.boxes):
        _deadlock_cache[cache_key] = True
        return True
        
    boxes_set: Set[Position] = set(state.boxes)
    _DEADLOCK_OFFSETS: Final[List[Tuple[int, int]]] = [(-1, -1), (-1, 0), (0, -1), (0, 0)]
    
    for r, c in state.boxes:
        for dr, dc in _DEADLOCK_OFFSETS:
            tl_r: int = r + dr
            tl_c: int = c + dc
            is_solid: bool = True
            boxes_in_2x2: List[Position] = []
            
            for i in range(2):
                for j in range(2):
                    curr_r: int = tl_r + i
                    curr_c: int = tl_c + j
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

def get_macro_neighbors(state: State, level: Level) -> Iterable[Tuple[PathSegment, State]]:
    queue: Deque[Tuple[Position, PathSegment]] = deque([(state.player, ())])
    visited_player: Set[Position] = {state.player}
    boxes_set: Set[Position] = set(state.boxes)
    zt = level.zobrist_table
    
    while queue:
        curr_p: Position
        path: PathSegment
        curr_p, path = queue.popleft()
        
        for action, (dr, dc) in ACTIONS.items():
            target: Position = (curr_p[0] + dr, curr_p[1] + dc)
            
            if target in boxes_set:
                beyond: Position = (target[0] + dr, target[1] + dc)
                
                if not level.is_wall(beyond) and beyond not in boxes_set:
                    act_int: int = _ACTION_TO_INT[action]
                    new_boxes: Tuple[Position, ...] = tuple(sorted(b if b != target else beyond for b in state.boxes))
                    
                    h_val: int = zt.player_keys[target]
                    for b in new_boxes:
                        h_val ^= zt.box_keys[b]
                        
                    yield path + (act_int,), State(target, new_boxes, h_val)
                    
            elif not level.is_wall(target):
                if target not in visited_player:
                    visited_player.add(target)
                    act_int = _ACTION_TO_INT[action]
                    queue.append((target, path + (act_int,)))

def reconstruct_path(parent: ParentMap, curr_key: StateKey) -> List[str]:
    final_path: List[str] = []
    
    while curr_key in parent:
        parent_info: Optional[Tuple[StateKey, PathSegment]] = parent[curr_key]
        if parent_info is None:
            break
            
        next_key: StateKey
        action_segment: PathSegment
        next_key, action_segment = parent_info
        
        final_path.extend(reversed([_INT_TO_ACTION[act_int] for act_int in action_segment]))
        curr_key = next_key
        
    final_path.reverse()
    return final_path