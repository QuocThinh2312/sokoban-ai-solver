import functools
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple, Dict, Optional, Set, Deque

import numpy as np
from scipy.optimize import linear_sum_assignment

from .constants import ACTIONS
from .level import Level
from .state import Position, State

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

@functools.lru_cache(maxsize=300000)
def _compute_heuristic_value(boxes: Tuple[Position, ...], goals: Tuple[Position, ...], lvl_id: str) -> int:
    if not boxes:
        return 0

    dist_map = _level_distances[lvl_id]
    n = len(boxes)
    
    max_mask = 1 << n
    dp = [999999] * max_mask
    dp[0] = 0
    
    costs = [[dist_map[g].get(b, 99999) for b in boxes] for g in goals]
    
    for mask in range(max_mask):
        c = dp[mask]
        if c >= 99999:
            continue
            
        k = mask.bit_count()
        if k == n:
            break
            
        goal_costs = costs[k]
        for j in range(n):
            if not (mask & (1 << j)):
                nxt = mask | (1 << j)
                new_cost = c + goal_costs[j]
                if new_cost < dp[nxt]:
                    dp[nxt] = new_cost
                    
    return dp[max_mask - 1]

def heuristic(state: State, level: Level) -> int:
    precompute_distances(level)
    lvl_id = _get_level_id(level)
    
    if lvl_id not in _level_sorted_goals:
        _level_sorted_goals[lvl_id] = tuple(sorted(level.goals))
        
    base_h = _compute_heuristic_value(state.boxes, _level_sorted_goals[lvl_id], lvl_id)
    
    if base_h >= 99999:
        return 999999 
        
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
            
    return base_h + (unsolved_count * 10) + player_dist + penalty


def is_freeze_deadlock(boxes_set: Set[Position], unsolved_boxes: Set[Position], level: Level) -> bool:
    frozen_boxes: Set[Position] = set()
    changed: bool = True
    
    while changed:
        changed = False
        for r, c in boxes_set:
            if (r, c) in frozen_boxes:
                continue
            
            v_blocked: bool = (level.is_wall((r-1, c)) or (r-1, c) in frozen_boxes) or \
                              (level.is_wall((r+1, c)) or (r+1, c) in frozen_boxes)
                            
            h_blocked: bool = (level.is_wall((r, c-1)) or (r, c-1) in frozen_boxes) or \
                              (level.is_wall((r, c+1)) or (r, c+1) in frozen_boxes)
                            
            if v_blocked and h_blocked:
                if (r, c) in unsolved_boxes:
                    return True 
                frozen_boxes.add((r, c))
                changed = True
                
    return False

def is_tunnel_deadlock(boxes_set: Set[Position], unsolved_boxes: Set[Position], level: Level) -> bool:
    for r, c in unsolved_boxes:
        if (r, c+1) in boxes_set:
            if level.is_wall((r-1, c)) and level.is_wall((r+1, c)) and \
               level.is_wall((r-1, c+1)) and level.is_wall((r+1, c+1)):
                return True
                
        if (r+1, c) in boxes_set:
            if level.is_wall((r, c-1)) and level.is_wall((r, c+1)) and \
               level.is_wall((r+1, c-1)) and level.is_wall((r+1, c+1)):
                return True
                
    return False

def has_deadlock(state: State, level: Level) -> bool:
    if any(box in level.deadlocks for box in state.boxes):
        return True
        
    boxes_set = set(state.boxes)
    unsolved_boxes = boxes_set - level.goals
    
    if not unsolved_boxes:
        return False
        
    for r, c in unsolved_boxes:
        if ((r-1, c) in boxes_set or level.is_wall((r-1, c))) and \
           ((r, c-1) in boxes_set or level.is_wall((r, c-1))) and \
           ((r-1, c-1) in boxes_set or level.is_wall((r-1, c-1))):
            return True
            
        if ((r-1, c) in boxes_set or level.is_wall((r-1, c))) and \
           ((r, c+1) in boxes_set or level.is_wall((r, c+1))) and \
           ((r-1, c+1) in boxes_set or level.is_wall((r-1, c+1))):
            return True
            
        if ((r+1, c) in boxes_set or level.is_wall((r+1, c))) and \
           ((r, c-1) in boxes_set or level.is_wall((r, c-1))) and \
           ((r+1, c-1) in boxes_set or level.is_wall((r+1, c-1))):
            return True
            
        if ((r+1, c) in boxes_set or level.is_wall((r+1, c))) and \
           ((r, c+1) in boxes_set or level.is_wall((r, c+1))) and \
           ((r+1, c+1) in boxes_set or level.is_wall((r+1, c+1))):
            return True

    if is_freeze_deadlock(boxes_set, unsolved_boxes, level):
        return True
        
    if is_tunnel_deadlock(boxes_set, unsolved_boxes, level):
        return True

    return False

def get_macro_neighbors(state: State, level: Level) -> Iterable[Tuple[List[str], State]]:
    queue: Deque[Tuple[Position, List[str]]] = deque([(state.player, [])])
    visited_player: Set[Position] = {state.player}
    
    boxes_set = set(state.boxes) 
    
    while queue:
        curr_p, path = queue.popleft()
        
        for action, (dr, dc) in ACTIONS.items():
            target = (curr_p[0] + dr, curr_p[1] + dc)
            
            if target in boxes_set:
                beyond = (target[0] + dr, target[1] + dc)
                
                if not level.is_wall(beyond) and beyond not in boxes_set:
                    
                    new_boxes = tuple(sorted([b for b in state.boxes if b != target] + [beyond]))
                    
                    h_val = state.zobrist_hash
                    h_val ^= level.zobrist_table.player_keys[state.player] 
                    h_val ^= level.zobrist_table.player_keys[target]       
                    h_val ^= level.zobrist_table.box_keys[target]          
                    h_val ^= level.zobrist_table.box_keys[beyond]          
                    
                    yield path + [action], State(target, new_boxes, h_val)
                    
            elif not level.is_wall(target):
                if target not in visited_player:
                    visited_player.add(target)
                    queue.append((target, path + [action]))

def reconstruct_path(parent: Dict[int, Optional[Tuple[int, List[str]]]], curr_key: int) -> List[str]:
    final_path: List[str] = []
    
    while curr_key in parent:
        parent_info = parent[curr_key]
        if parent_info is None:
            break
        curr_key, action_segment = parent_info
        final_path.extend(reversed(action_segment))
        
    final_path.reverse()
    return final_path