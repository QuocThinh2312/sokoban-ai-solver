import heapq
import time
import random
import threading
import traceback
from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Deque, Final, TypeAlias, FrozenSet

from .level import Level
from .state import State, is_goal, Position
from .solver_utils import (
    SolveResult, has_deadlock, reconstruct_path, heuristic, 
    get_macro_neighbors, greedy_heuristic, _INT_TO_ACTION, _INFINITY
)

MAX_TIME: Final[float] = 60.0
INFINITY: Final[int] = _INFINITY

StateKey: TypeAlias = Tuple[Position, Tuple[Position, ...]]
PathSegment: TypeAlias = Tuple[int, ...]
ParentMap: TypeAlias = Dict[StateKey, Optional[Tuple[StateKey, PathSegment]]]

def _solve_bfs(
    level: Level, 
    start_time: float, 
    stop_event: Optional[threading.Event] = None, 
    progress_state: Optional[List[int]] = None
) -> SolveResult:
    start_state: State = level.initial_state()
    start_key: int = start_state.zobrist_hash
    start_exact: StateKey = (start_state.player, start_state.boxes)
    
    if is_goal(start_state, level.goals):
        return SolveResult("BFS", True, actions=[])
        
    queue: Deque[State] = deque([start_state])
    parent: ParentMap = {start_exact: None}
    visited: Set[int] = {start_key}
    expanded: int = 0
    
    while queue:
        curr_state: State = queue.popleft()
        expanded += 1
        curr_exact: StateKey = (curr_state.player, curr_state.boxes)
        
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("BFS", False, expanded=expanded, message="Timeout.")
            if stop_event and stop_event.is_set():
                return SolveResult("BFS", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded
                
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            neighbor_key: int = neighbor_state.zobrist_hash
            neighbor_exact: StateKey = (neighbor_state.player, neighbor_state.boxes)
            
            if neighbor_key in visited:
                continue
            if has_deadlock(neighbor_state, level):
                continue
                
            parent[neighbor_exact] = (curr_exact, path_segment)
            if is_goal(neighbor_state, level.goals):
                actions: List[str] = reconstruct_path(parent, neighbor_exact)
                return SolveResult("BFS", True, actions, expanded)
                
            visited.add(neighbor_key)
            queue.append(neighbor_state)
            
    return SolveResult("BFS", False, expanded=expanded, message="No solution found.")

def _dfs_evaluate(state: State, level: Level) -> Tuple[int, int]:
    h_val: int = heuristic(state, level)
    unsolved_count: int = sum(1 for b in state.boxes if b not in level.goals)
    return (unsolved_count, h_val)

def _solve_dfs(
    level: Level, 
    start_time: float, 
    stop_event: Optional[threading.Event] = None, 
    progress_state: Optional[List[int]] = None
) -> SolveResult:
    start_state: State = level.initial_state()
    if is_goal(start_state, level.goals):
        return SolveResult("DFS", True, actions=[])

    stack: List[Tuple[State, PathSegment]] = [(start_state, ())]
    visited: Set[int] = {start_state.zobrist_hash}
    expanded: int = 0

    while stack:
        curr_state: State
        path: PathSegment
        curr_state, path = stack.pop()
        
        if is_goal(curr_state, level.goals):
            actions: List[str] = [_INT_TO_ACTION[act] for act in path]
            return SolveResult("DFS", True, actions, expanded)

        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("DFS", False, expanded=expanded, message="Time out.")
            if stop_event and stop_event.is_set():
                return SolveResult("DFS", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded

        neighbors: List[Tuple[Tuple[int, int], int, State, PathSegment]] = []
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            n_key: int = neighbor_state.zobrist_hash
            if n_key in visited:
                continue
            if has_deadlock(neighbor_state, level):
                continue
            
            score: Tuple[int, int] = _dfs_evaluate(neighbor_state, level)
            neighbors.append((score, n_key, neighbor_state, path + path_segment))

        neighbors.sort(key=lambda x: x[0], reverse=True)

        for _, n_key, n_state, n_path in neighbors:
            visited.add(n_key)
            stack.append((n_state, n_path))

    return SolveResult("DFS", False, expanded=expanded, message="No solution found.")

def _solve_ucs(
    level: Level, 
    start_time: float, 
    stop_event: Optional[threading.Event] = None, 
    progress_state: Optional[List[int]] = None
) -> SolveResult:
    start_state: State = level.initial_state()
    start_key: int = start_state.zobrist_hash
    start_exact: StateKey = (start_state.player, start_state.boxes)
    counter: int = 0
    priority_queue: List[Tuple[int, int, State]] = [(0, counter, start_state)]
    parent: ParentMap = {start_exact: None}
    best_cost: Dict[int, int] = {start_key: 0}
    expanded: int = 0
    
    while priority_queue:
        g: int
        curr_state: State
        g, _, curr_state = heapq.heappop(priority_queue)
        curr_key = curr_state.zobrist_hash
        curr_exact = (curr_state.player, curr_state.boxes)
        
        if is_goal(curr_state, level.goals):
            actions: List[str] = reconstruct_path(parent, curr_exact)
            return SolveResult("UCS", True, actions, expanded)
            
        if g > best_cost.get(curr_key, INFINITY):
            continue
            
        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("UCS", False, expanded=expanded, message="Time out.")
            if stop_event and stop_event.is_set():
                return SolveResult("UCS", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded
                
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            neighbor_key: int = neighbor_state.zobrist_hash
            neighbor_exact: StateKey = (neighbor_state.player, neighbor_state.boxes)
            new_g: int = g + len(path_segment)
            
            if has_deadlock(neighbor_state, level):
                continue
                
            if new_g < best_cost.get(neighbor_key, INFINITY):
                best_cost[neighbor_key] = new_g
                parent[neighbor_exact] = (curr_exact, path_segment)
                counter += 1
                heapq.heappush(priority_queue, (new_g, counter, neighbor_state))
                
    return SolveResult("UCS", False, expanded=expanded, message="No solution found.")

def _evaluate_greedy_state(state: State, level: Level) -> Tuple[float, int, int]:
    total_score: float = greedy_heuristic(state, level) 
    goals: FrozenSet[Position] = level.goals
    unsolved_boxes: List[Position] = [b for b in state.boxes if b not in goals]
    unsolved_count: int = len(unsolved_boxes)
    
    if unsolved_count == 0:
        return (total_score, 0, 0)
        
    pr: int
    pc: int
    pr, pc = state.player
    player_box_dist: int = min(abs(pr - br) + abs(pc - bc) for br, bc in unsolved_boxes)
    
    return (total_score, unsolved_count, player_box_dist)

def _solve_greedy(
    level: Level, 
    start_time: float, 
    stop_event: Optional[threading.Event] = None, 
    progress_state: Optional[List[int]] = None
) -> SolveResult:
    start_state: State = level.initial_state()
    start_key: int = start_state.zobrist_hash
    start_exact: StateKey = (start_state.player, start_state.boxes)
    counter: int = 0
    
    start_score: float
    start_unsolved: int
    start_pbd: int
    start_score, start_unsolved, start_pbd = _evaluate_greedy_state(start_state, level)
    
    priority_queue: List[Tuple[float, int, int, int, State]] = [
        (start_score, start_unsolved, start_pbd, counter, start_state)
    ]
    parent: ParentMap = {start_exact: None}
    best_g_cost: Dict[int, int] = {start_key: 0}
    expanded: int = 0
    
    while priority_queue:
        curr_state: State
        _, _, _, _, curr_state = heapq.heappop(priority_queue)
        curr_key: int = curr_state.zobrist_hash
        curr_exact: StateKey = (curr_state.player, curr_state.boxes)
        curr_g: int = best_g_cost.get(curr_key, 0)
        
        if is_goal(curr_state, level.goals):
            actions: List[str] = reconstruct_path(parent, curr_exact)
            return SolveResult("Greedy", True, actions, expanded)
            
        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("Greedy", False, expanded=expanded, message="Time out.")
            if stop_event and stop_event.is_set():
                return SolveResult("Greedy", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded
                
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            neighbor_key: int = neighbor_state.zobrist_hash
            neighbor_exact: StateKey = (neighbor_state.player, neighbor_state.boxes)
            new_g: int = curr_g + len(path_segment)
            
            if new_g >= best_g_cost.get(neighbor_key, INFINITY):
                continue
            if has_deadlock(neighbor_state, level):
                continue
                
            parent[neighbor_exact] = (curr_exact, path_segment)
            best_g_cost[neighbor_key] = new_g
            
            score: float
            unsolved_count: int
            pbd: int
            score, unsolved_count, pbd = _evaluate_greedy_state(neighbor_state, level)
            counter += 1
            heapq.heappush(priority_queue, (score, unsolved_count, pbd, counter, neighbor_state))
            
    return SolveResult("Greedy", False, expanded=expanded, message="No solution found.")

def _solve_astar(
    level: Level, 
    start_time: float, 
    stop_event: Optional[threading.Event] = None, 
    progress_state: Optional[List[int]] = None
) -> SolveResult:
    start_state: State = level.initial_state()
    start_exact: StateKey = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult("A*", True, [], 0)
        
    counter: int = 0
    start_h: int = heuristic(start_state, level)
    priority_queue: List[Tuple[int, int, int, State]] = [(start_h, 0, counter, start_state)]
    parent: ParentMap = {start_exact: None}
    best_g_cost: Dict[StateKey, int] = {start_exact: 0}
    expanded: int = 0
    
    while priority_queue:
        neg_g: int
        curr_state: State
        _, neg_g, _, curr_state = heapq.heappop(priority_queue)
        g: int = -neg_g
        curr_exact: StateKey = (curr_state.player, curr_state.boxes)
        
        if is_goal(curr_state, level.goals):
            actions: List[str] = reconstruct_path(parent, curr_exact)
            return SolveResult("A*", True, actions, expanded)
            
        if g > best_g_cost.get(curr_exact, INFINITY):
            continue
            
        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("A*", False, expanded=expanded, message="Time out.")
            if stop_event and stop_event.is_set():
                return SolveResult("A*", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded
                
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            neighbor_exact: StateKey = (neighbor_state.player, neighbor_state.boxes)
            new_g: int = g + len(path_segment)
            
            if new_g >= best_g_cost.get(neighbor_exact, INFINITY):
                continue
            if has_deadlock(neighbor_state, level):
                continue
                
            best_g_cost[neighbor_exact] = new_g
            parent[neighbor_exact] = (curr_exact, path_segment)
            new_h: int = heuristic(neighbor_state, level)
            new_f: int = new_g + new_h
            counter += 1
            heapq.heappush(priority_queue, (new_f, -new_g, counter, neighbor_state))
            
    return SolveResult("A*", False, expanded=expanded, message="No solution found.")

def _solve_weighted_astar(
    level: Level, 
    start_time: float, 
    weight: float = 2.0, 
    stop_event: Optional[threading.Event] = None, 
    progress_state: Optional[List[int]] = None
) -> SolveResult:
    start_state: State = level.initial_state()
    start_key: int = start_state.zobrist_hash
    start_exact: StateKey = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult(f"Weighted A* (w={weight})", True, [], 0)
        
    counter: int = 0
    start_h: int = heuristic(start_state, level)
    priority_queue: List[Tuple[float, int, int, State]] = [(float(weight * start_h), 0, counter, start_state)]
    parent: ParentMap = {start_exact: None}
    best_g_cost: Dict[int, int] = {start_key: 0}
    expanded: int = 0
    
    while priority_queue:
        neg_g: int
        curr_state: State
        _, neg_g, _, curr_state = heapq.heappop(priority_queue)
        g: int = -neg_g
        curr_key: int = curr_state.zobrist_hash
        curr_exact: StateKey = (curr_state.player, curr_state.boxes)
        
        if is_goal(curr_state, level.goals):
            actions: List[str] = reconstruct_path(parent, curr_exact)
            return SolveResult(f"Weighted A* (w={weight})", True, actions, expanded)
            
        if g > best_g_cost.get(curr_key, INFINITY):
            continue
            
        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("Weighted A*", False, expanded=expanded, message="Timeout.")
            if stop_event and stop_event.is_set():
                return SolveResult("Weighted A*", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded
                
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            neighbor_key: int = neighbor_state.zobrist_hash
            neighbor_exact: StateKey = (neighbor_state.player, neighbor_state.boxes)
            new_g: int = g + len(path_segment)
            
            if new_g >= best_g_cost.get(neighbor_key, INFINITY):
                continue
            if has_deadlock(neighbor_state, level):
                continue
                
            best_g_cost[neighbor_key] = new_g
            parent[neighbor_exact] = (curr_exact, path_segment)
            new_h: int = heuristic(neighbor_state, level)
            new_f: float = float(new_g + weight * new_h)
            counter += 1
            heapq.heappush(priority_queue, (new_f, -new_g, counter, neighbor_state))
            
    return SolveResult("Weighted A*", False, expanded=expanded, message="No solution found.")

def _solve_beam_search(
    level: Level, 
    start_time: float, 
    beam_width: int = 1500, 
    stop_event: Optional[threading.Event] = None, 
    progress_state: Optional[List[int]] = None
) -> SolveResult:
    start_state: State = level.initial_state()
    if is_goal(start_state, level.goals):
        return SolveResult(f"Beam Search (K={beam_width})", True, actions=[])
    
    expanded: int = 0
    current_limit: int = beam_width
    
    while time.perf_counter() - start_time < MAX_TIME:
        start_key: int = start_state.zobrist_hash
        start_exact: StateKey = (start_state.player, start_state.boxes)
        counter: int = 0
        base_h: int = heuristic(start_state, level)
        
        priority_queue: List[Tuple[float, int, int, int, State]] = [
            (float(base_h * 2.0), base_h, counter, 0, start_state)
        ]
        parent: ParentMap = {start_exact: None}
        best_g_cost: Dict[int, int] = {start_key: 0}
        
        while priority_queue:
            g: int
            curr_state: State
            _, _, _, g, curr_state = heapq.heappop(priority_queue)
            curr_key: int = curr_state.zobrist_hash
            
            if g > best_g_cost.get(curr_key, INFINITY):
                continue
                
            curr_exact: StateKey = (curr_state.player, curr_state.boxes)
            if is_goal(curr_state, level.goals):
                actions: List[str] = reconstruct_path(parent, curr_exact)
                return SolveResult(f"Beam Search (K={current_limit})", True, actions, expanded)
                
            expanded += 1
            if expanded & 1023 == 0:
                if time.perf_counter() - start_time > MAX_TIME:
                    return SolveResult("Beam Search", False, expanded=expanded, message="Timeout.")
                if stop_event and stop_event.is_set():
                    return SolveResult("Beam Search", False, expanded=expanded, message="Cancelled by user.")
                if progress_state is not None:
                    progress_state[0] = expanded
                    
            for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
                neighbor_key: int = neighbor_state.zobrist_hash
                neighbor_exact: StateKey = (neighbor_state.player, neighbor_state.boxes)
                new_g: int = g + len(path_segment)
                
                if new_g >= best_g_cost.get(neighbor_key, INFINITY):
                    continue
                if has_deadlock(neighbor_state, level):
                    continue
                    
                best_g_cost[neighbor_key] = new_g
                parent[neighbor_exact] = (curr_exact, path_segment)
                
                h: int = heuristic(neighbor_state, level)
                new_f: float = float(new_g + h * 2.0) + random.uniform(0.0, 0.05)
                counter += 1
                heapq.heappush(priority_queue, (new_f, h, counter, new_g, neighbor_state))
                
            if len(priority_queue) > current_limit * 2:
                priority_queue = heapq.nsmallest(current_limit, priority_queue, key=lambda x: x[0])
                heapq.heapify(priority_queue)
                
        current_limit = int(current_limit * 2.5)
        
    return SolveResult("Beam Search", False, expanded=expanded, message="Timeout.")

def solve(
    algorithm: str, 
    level: Level, 
    stop_event: Optional[threading.Event] = None, 
    progress_state: Optional[List[int]] = None
) -> SolveResult:
    start_time: float = time.perf_counter()
    result: SolveResult
    try:
        if algorithm == "BFS":
            result = _solve_bfs(level, start_time, stop_event, progress_state)
        elif algorithm == "DFS":
            result = _solve_dfs(level, start_time, stop_event, progress_state)
        elif algorithm == "UCS":
            result = _solve_ucs(level, start_time, stop_event, progress_state)
        elif algorithm == "Greedy":
            result = _solve_greedy(level, start_time, stop_event, progress_state)
        elif algorithm == "A*":
            result = _solve_astar(level, start_time, stop_event, progress_state)
        elif algorithm == "Weighted A*": 
            result = _solve_weighted_astar(level, start_time, weight=1.0, stop_event=stop_event, progress_state=progress_state)
        elif algorithm == "Beam Search": 
            result = _solve_beam_search(level, start_time, beam_width=1000, stop_event=stop_event, progress_state=progress_state)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    except Exception as e:
        traceback.print_exc()
        result = SolveResult(algorithm, False, message=f"Error: {e.__class__.__name__}")
        
    elapsed_time_ms: float = (time.perf_counter() - start_time) * 1000.0
    result.elapsed_ms = elapsed_time_ms
    return result