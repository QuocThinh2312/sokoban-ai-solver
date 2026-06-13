import heapq
import time
import random
import threading
from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Deque

from .level import Level
from .state import State, is_goal, Position
from .solver_utils import SolveResult, has_deadlock, reconstruct_path, heuristic, get_macro_neighbors, greedy_heuristic

MAX_TIME = 60.0
INFINITY = 999999999 

def _solve_bfs(level: Level, start_time: float, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult("BFS", True, actions=[])
    queue: Deque[State] = deque([start_state])
    parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {start_exact: None}
    visited: Set[int] = {start_key}
    expanded = 0
    while queue:
        curr_state = queue.popleft()
        expanded += 1
        curr_exact = (curr_state.player, curr_state.boxes)
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("BFS", False, expanded=expanded, message="Timeout.")
            if stop_event and stop_event.is_set():
                return SolveResult("BFS", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            neighbor_key = neighbor_state.zobrist_hash
            neighbor_exact = (neighbor_state.player, neighbor_state.boxes)
            if neighbor_key in visited:
                continue
            if has_deadlock(neighbor_state, level):
                continue
            parent[neighbor_exact] = (curr_exact, path_segment)
            if is_goal(neighbor_state, level.goals):
                actions = reconstruct_path(parent, neighbor_exact)
                return SolveResult("BFS", True, actions, expanded)
            visited.add(neighbor_key)
            queue.append(neighbor_state)
    return SolveResult("BFS", False, expanded=expanded, message="No solution found.")

def _dfs_evaluate(state: State, level: Level) -> Tuple[int, int]:
    h_val = heuristic(state, level)
    unsolved_count = 0
    for b in state.boxes:
        if b not in level.goals:
            unsolved_count += 1
    return (unsolved_count, h_val)

def _solve_dfs(level: Level, start_time: float, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    from .solver_utils import _INT_TO_ACTION
    start_state = level.initial_state()
    if is_goal(start_state, level.goals):
        return SolveResult("DFS", True, actions=[])

    stack: List[Tuple[State, Tuple[int, ...]]] = [(start_state, ())]
    visited: Set[int] = {start_state.zobrist_hash}
    expanded = 0

    while stack:
        curr_state, path = stack.pop()
        
        if is_goal(curr_state, level.goals):
            actions = [_INT_TO_ACTION[act] for act in path]
            return SolveResult("DFS", True, actions, expanded)

        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("DFS", False, expanded=expanded, message="Time out.")
            if stop_event and stop_event.is_set():
                return SolveResult("DFS", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded

        neighbors: List[Tuple[Tuple[int, int], int, State, Tuple[int, ...]]] = []
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            n_key = neighbor_state.zobrist_hash
            if n_key in visited:
                continue
            if has_deadlock(neighbor_state, level):
                continue
            
            score = _dfs_evaluate(neighbor_state, level)
            neighbors.append((score, n_key, neighbor_state, path + path_segment))

        neighbors.sort(key=lambda x: x[0], reverse=True)

        for _, n_key, n_state, n_path in neighbors:
            visited.add(n_key)
            stack.append((n_state, n_path))

    return SolveResult("DFS", False, expanded=expanded, message="No solution found.")

def _solve_ucs(level: Level, start_time: float, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    counter = 0
    priority_queue: List[Tuple[int, int, State]] = [(0, counter, start_state)]
    parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {start_exact: None}
    best_cost: Dict[int, int] = {start_key: 0}
    expanded = 0
    while priority_queue:
        g, _, curr_state = heapq.heappop(priority_queue)
        curr_key = curr_state.zobrist_hash
        curr_exact = (curr_state.player, curr_state.boxes)
        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_exact)
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
            neighbor_key = neighbor_state.zobrist_hash
            neighbor_exact = (neighbor_state.player, neighbor_state.boxes)
            new_g = g + len(path_segment)
            if has_deadlock(neighbor_state, level):
                continue
            if new_g < best_cost.get(neighbor_key, INFINITY):
                best_cost[neighbor_key] = new_g
                parent[neighbor_exact] = (curr_exact, path_segment)
                counter += 1
                heapq.heappush(priority_queue, (new_g, counter, neighbor_state))
    return SolveResult("UCS", False, expanded=expanded, message="No solution found.")

def _evaluate_greedy_state(state: State, level: Level) -> Tuple[float, int, int]:
    total_score = greedy_heuristic(state, level) 
    goals = level.goals
    unsolved_boxes = [b for b in state.boxes if b not in goals]
    unsolved_count = len(unsolved_boxes)
    if unsolved_count == 0:
        return (total_score, 0, 0)
    pr, pc = state.player
    player_box_dist = min(abs(pr - br) + abs(pc - bc) for br, bc in unsolved_boxes)
    return (total_score, unsolved_count, player_box_dist)

def _solve_greedy(level: Level, start_time: float, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    counter = 0
    start_score, start_unsolved, start_pbd = _evaluate_greedy_state(start_state, level)
    priority_queue: List[Tuple[float, int, int, int, State]] = [
        (start_score, start_unsolved, start_pbd, counter, start_state)
    ]
    parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {start_exact: None}
    best_g_cost: Dict[int, int] = {start_key: 0}
    expanded = 0
    while priority_queue:
        _, _, _, _, curr_state = heapq.heappop(priority_queue)
        curr_key = curr_state.zobrist_hash
        curr_exact = (curr_state.player, curr_state.boxes)
        curr_g = best_g_cost.get(curr_key, 0)
        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_exact)
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
            neighbor_key = neighbor_state.zobrist_hash
            neighbor_exact = (neighbor_state.player, neighbor_state.boxes)
            new_g = curr_g + len(path_segment)
            if new_g >= best_g_cost.get(neighbor_key, INFINITY):
                continue
            if has_deadlock(neighbor_state, level):
                continue
            parent[neighbor_exact] = (curr_exact, path_segment)
            best_g_cost[neighbor_key] = new_g
            score, unsolved_count, pbd = _evaluate_greedy_state(neighbor_state, level)
            counter += 1
            heapq.heappush(priority_queue, (score, unsolved_count, pbd, counter, neighbor_state))
    return SolveResult("Greedy", False, expanded=expanded, message="No solution found.")

def _solve_astar(level: Level, start_time: float, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_exact = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult("A*", True, [], 0)
    counter = 0
    start_h = heuristic(start_state, level)
    priority_queue: List[Tuple[int, int, int, State]] = [(start_h, 0, counter, start_state)]
    parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {start_exact: None}
    best_g_cost: Dict[Tuple[Position, Tuple[Position, ...]], int] = {start_exact: 0}
    expanded = 0
    while priority_queue:
        _, neg_g, _, curr_state = heapq.heappop(priority_queue)
        g = -neg_g
        curr_exact = (curr_state.player, curr_state.boxes)
        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_exact)
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
            neighbor_exact = (neighbor_state.player, neighbor_state.boxes)
            new_g = g + len(path_segment)
            if new_g >= best_g_cost.get(neighbor_exact, INFINITY):
                continue
            if has_deadlock(neighbor_state, level):
                continue
            best_g_cost[neighbor_exact] = new_g
            parent[neighbor_exact] = (curr_exact, path_segment)
            new_h = heuristic(neighbor_state, level)
            new_f = new_g + new_h
            counter += 1
            heapq.heappush(priority_queue, (new_f, -new_g, counter, neighbor_state))
    return SolveResult("A*", False, expanded=expanded, message="No solution found.")

def _solve_weighted_astar(level: Level, start_time: float, weight: float = 2.0, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult(f"Weighted A* (w={weight})", True, [], 0)
    counter = 0
    start_h = heuristic(start_state, level)
    priority_queue: List[Tuple[float, int, int, State]] = [(float(weight * start_h), 0, counter, start_state)]
    parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {start_exact: None}
    best_g_cost: Dict[int, int] = {start_key: 0}
    expanded = 0
    while priority_queue:
        _, neg_g, _, curr_state = heapq.heappop(priority_queue)
        g = -neg_g
        curr_key = curr_state.zobrist_hash
        curr_exact = (curr_state.player, curr_state.boxes)
        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_exact)
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
            neighbor_key = neighbor_state.zobrist_hash
            neighbor_exact = (neighbor_state.player, neighbor_state.boxes)
            new_g = g + len(path_segment)
            if new_g >= best_g_cost.get(neighbor_key, INFINITY):
                continue
            if has_deadlock(neighbor_state, level):
                continue
            best_g_cost[neighbor_key] = new_g
            parent[neighbor_exact] = (curr_exact, path_segment)
            new_h = heuristic(neighbor_state, level)
            new_f = float(new_g + weight * new_h)
            counter += 1
            heapq.heappush(priority_queue, (new_f, -new_g, counter, neighbor_state))
    return SolveResult("Weighted A*", False, expanded=expanded, message="No solution found.")

def _solve_beam_search(level: Level, start_time: float, beam_width: int = 1500, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    if is_goal(start_state, level.goals):
        return SolveResult(f"Beam Search (K={beam_width})", True, actions=[])
    
    expanded = 0
    current_limit = beam_width
    
    while time.perf_counter() - start_time < MAX_TIME:
        start_key = start_state.zobrist_hash
        start_exact = (start_state.player, start_state.boxes)
        counter = 0
        base_h = heuristic(start_state, level)
        
        priority_queue: List[Tuple[float, int, int, int, State]] = [
            (float(base_h * 2.0), base_h, counter, 0, start_state)
        ]
        parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {start_exact: None}
        best_g_cost: Dict[int, int] = {start_key: 0}
        
        while priority_queue:
            _, _, _, g, curr_state = heapq.heappop(priority_queue)
            curr_key = curr_state.zobrist_hash
            
            if g > best_g_cost.get(curr_key, INFINITY):
                continue
                
            curr_exact = (curr_state.player, curr_state.boxes)
            if is_goal(curr_state, level.goals):
                actions = reconstruct_path(parent, curr_exact)
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
                neighbor_key = neighbor_state.zobrist_hash
                neighbor_exact = (neighbor_state.player, neighbor_state.boxes)
                new_g = g + len(path_segment)
                
                if new_g >= best_g_cost.get(neighbor_key, INFINITY):
                    continue
                if has_deadlock(neighbor_state, level):
                    continue
                    
                best_g_cost[neighbor_key] = new_g
                parent[neighbor_exact] = (curr_exact, path_segment)
                
                h = heuristic(neighbor_state, level)
                new_f = float(new_g + h * 2.0) + random.uniform(0.0, 0.05)
                counter += 1
                heapq.heappush(priority_queue, (new_f, h, counter, new_g, neighbor_state))
                
            if len(priority_queue) > current_limit * 2:
                priority_queue = heapq.nsmallest(current_limit, priority_queue, key=lambda x: x[0])
                heapq.heapify(priority_queue)
                
        current_limit = int(current_limit * 2.5)
        
    return SolveResult("Beam Search", False, expanded=expanded, message="Timeout.")

def solve(algorithm: str, level: Level, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_time = time.perf_counter()
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
        import traceback
        traceback.print_exc()
        result = SolveResult(algorithm, False, message=f"Error: {e.__class__.__name__}")
    elapsed_time_ms = (time.perf_counter() - start_time) * 1000.0
    result.elapsed_ms = elapsed_time_ms
    return result