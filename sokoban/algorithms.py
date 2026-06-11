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
                return SolveResult("BFS", False, expanded=expanded, message="Timeout (>60s).")
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

def _solve_dfs(level: Level, start_time: float, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult("DFS", True, actions=[])
    stack: List[Tuple[State, int]] = [(start_state, 0)]
    parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {start_exact: None}
    best_depth: Dict[int, int] = {start_key: 0}
    expanded = 0
    while stack:
        curr_state, depth = stack.pop()
        curr_key = curr_state.zobrist_hash
        curr_exact = (curr_state.player, curr_state.boxes)
        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_exact)
            return SolveResult("DFS", True, actions, expanded)
        if depth > best_depth.get(curr_key, INFINITY):
            continue
        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("DFS", False, expanded=expanded, message="Timeout (>60s).")
            if stop_event and stop_event.is_set():
                return SolveResult("DFS", False, expanded=expanded, message="Cancelled by user.")
            if progress_state is not None:
                progress_state[0] = expanded
        for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
            neighbor_key = neighbor_state.zobrist_hash
            neighbor_exact = (neighbor_state.player, neighbor_state.boxes)
            new_depth = depth + len(path_segment)
            if has_deadlock(neighbor_state, level):
                continue
            if new_depth < best_depth.get(neighbor_key, INFINITY):
                best_depth[neighbor_key] = new_depth
                parent[neighbor_exact] = (curr_exact, path_segment)
                stack.append((neighbor_state, new_depth))
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
                return SolveResult("UCS", False, expanded=expanded, message="Timeout (>60s).")
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
                return SolveResult("Greedy", False, expanded=expanded, message="Timeout (>60s).")
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
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult("A*", True, [], 0)
    counter = 0
    start_h = heuristic(start_state, level)
    priority_queue: List[Tuple[int, int, int, State]] = [(start_h, 0, counter, start_state)]
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
            return SolveResult("A*", True, actions, expanded)
        if g > best_g_cost.get(curr_key, INFINITY):
            continue
        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("A*", False, expanded=expanded, message="Timeout (>60s).")
            if stop_event and stop_event.is_set():
                return SolveResult("A*", False, expanded=expanded, message="Cancelled by user.")
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
            new_f = new_g + new_h
            counter += 1
            heapq.heappush(priority_queue, (new_f, -new_g, counter, neighbor_state))
    return SolveResult("A*", False, expanded=expanded, message="No solution found.")

def _solve_weighted_astar(level: Level, start_time: float, weight: float = 2.0, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult(f"Weighted_A* (w={weight})", True, [], 0)
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
            return SolveResult(f"Weighted_A* (w={weight})", True, actions, expanded)
        if g > best_g_cost.get(curr_key, INFINITY):
            continue
        expanded += 1
        if expanded & 1023 == 0:
            if time.perf_counter() - start_time > MAX_TIME:
                return SolveResult("Weighted_A*", False, expanded=expanded, message="Timeout.")
            if stop_event and stop_event.is_set():
                return SolveResult("Weighted_A*", False, expanded=expanded, message="Cancelled by user.")
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
    return SolveResult("Weighted_A*", False, expanded=expanded, message="No solution found.")

def _evaluate_beam_state(state: State, level: Level) -> Tuple[int, int, int]:
    base_h = heuristic(state, level)
    goals = level.goals
    unsolved_boxes = [b for b in state.boxes if b not in goals]
    unsolved_count = len(unsolved_boxes)
    if unsolved_count == 0:
        return (base_h, 0, 0)
    pr, pc = state.player
    player_box_dist = min(abs(pr - br) + abs(pc - bc) for br, bc in unsolved_boxes)
    penalty = 0
    for br, bc in unsolved_boxes:
        v_wall = level.is_wall((br - 1, bc)) or level.is_wall((br + 1, bc))
        h_wall = level.is_wall((br, bc - 1)) or level.is_wall((br, bc + 1))
        if v_wall:
            penalty += 1
        if h_wall:
            penalty += 1
    return (base_h + penalty, unsolved_count, player_box_dist)

def _solve_beam_search(level: Level, start_time: float, beam_width: int = 3000, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult(f"Beam_Search (K={beam_width})", True, actions=[])
    beam: List[Tuple[State, int]] = [(start_state, 0)]
    parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {start_exact: None}
    best_g_cost: Dict[int, int] = {start_key: 0}
    expanded = 0
    best_h_overall = INFINITY
    stagnation_counter = 0
    while beam:
        if time.perf_counter() - start_time > MAX_TIME:
            return SolveResult("Beam_Search", False, expanded=expanded, message="Timeout.")
        candidates: Dict[int, Tuple[float, int, int, State, Tuple[Position, Tuple[Position, ...]], Tuple[int, ...], int]] = {}
        current_best_h_in_beam = INFINITY
        for curr_state, g in beam:
            curr_exact = (curr_state.player, curr_state.boxes)
            expanded += 1
            if expanded & 1023 == 0:
                if stop_event and stop_event.is_set():
                    return SolveResult("Beam_Search", False, expanded=expanded, message="Cancelled by user.")
                if progress_state is not None:
                    progress_state[0] = expanded
            for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
                neighbor_key = neighbor_state.zobrist_hash
                new_g = g + len(path_segment)
                if new_g >= best_g_cost.get(neighbor_key, INFINITY):
                    continue
                if has_deadlock(neighbor_state, level):
                    continue
                base_h, unsolved_count, pbd = _evaluate_beam_state(neighbor_state, level)
                if base_h < current_best_h_in_beam:
                    current_best_h_in_beam = base_h
                f = float(new_g + base_h * 1.5)
                if neighbor_key not in candidates or new_g < candidates[neighbor_key][6]:
                    candidates[neighbor_key] = (f, unsolved_count, pbd, neighbor_state, curr_exact, path_segment, new_g)
        if not candidates:
            break
        if current_best_h_in_beam < best_h_overall:
            best_h_overall = current_best_h_in_beam
            stagnation_counter = 0
        else:
            stagnation_counter += 1
        evaluated_candidates = list(candidates.values())
        if len(evaluated_candidates) > beam_width:
            if stagnation_counter >= 3:
                top_k_target = int(beam_width * 0.95)
                evaluated_candidates.sort(key=lambda x: (x[0], x[1], x[2]))
                chosen = evaluated_candidates[:top_k_target]
                remaining = evaluated_candidates[top_k_target:]
                needed_random = beam_width - len(chosen)
                if needed_random > 0 and remaining:
                    chosen.extend(random.sample(remaining, min(needed_random, len(remaining))))
            else:
                chosen = heapq.nsmallest(beam_width, evaluated_candidates, key=lambda x: (x[0], x[1], x[2]))
        else:
            chosen = evaluated_candidates
        beam = []
        for f, unsolved_count, pbd, neighbor_state, curr_exact, path_segment, new_g in chosen:
            neighbor_key = neighbor_state.zobrist_hash
            neighbor_exact = (neighbor_state.player, neighbor_state.boxes)
            if new_g < best_g_cost.get(neighbor_key, INFINITY):
                best_g_cost[neighbor_key] = new_g
                parent[neighbor_exact] = (curr_exact, path_segment)
                if is_goal(neighbor_state, level.goals):
                    actions = reconstruct_path(parent, neighbor_exact)
                    return SolveResult(f"Beam_Search (K={beam_width})", True, actions, expanded)
                beam.append((neighbor_state, new_g))
    return SolveResult("Beam_Search", False, expanded=expanded, message="No solution found.")

def _solve_idastar(level: Level, start_time: float, stop_event: Optional[threading.Event] = None, progress_state: Optional[List[int]] = None) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.zobrist_hash
    start_exact = (start_state.player, start_state.boxes)
    if is_goal(start_state, level.goals):
        return SolveResult("IDA*", True, [])
    limit = heuristic(start_state, level)
    expanded = 0
    while True:
        if time.perf_counter() - start_time > MAX_TIME:
            return SolveResult("IDA*", False, expanded=expanded, message="Timeout.")
        min_cutoff = INFINITY
        stack: List[Tuple[State, int, Tuple[Position, Tuple[Position, ...]], Tuple[int, ...], bool]] = [(start_state, 0, start_exact, (), False)]
        path_set: Set[int] = set()
        parent: Dict[Tuple[Position, Tuple[Position, ...]], Optional[Tuple[Tuple[Position, Tuple[Position, ...]], Tuple[int, ...]]]] = {}
        visited_cost: Dict[int, int] = {}
        while stack:
            curr_state, g, parent_exact, segment, is_backtrack = stack.pop()
            curr_key = curr_state.zobrist_hash
            curr_exact = (curr_state.player, curr_state.boxes)
            if is_backtrack:
                path_set.remove(curr_key)
                if curr_exact in parent:
                    del parent[curr_exact]
                continue
            if curr_key in visited_cost and visited_cost[curr_key] <= g:
                continue
            visited_cost[curr_key] = g
            if curr_exact != start_exact:
                parent[curr_exact] = (parent_exact, segment)
            if is_goal(curr_state, level.goals):
                actions = reconstruct_path(parent, curr_exact)
                return SolveResult("IDA*", True, actions, expanded)
            path_set.add(curr_key)
            stack.append((curr_state, g, parent_exact, segment, True))
            expanded += 1
            if expanded & 1023 == 0:
                if time.perf_counter() - start_time > MAX_TIME:
                    return SolveResult("IDA*", False, expanded=expanded, message="Timeout.")
                if stop_event and stop_event.is_set():
                    return SolveResult("IDA*", False, expanded=expanded, message="Cancelled by user.")
                if progress_state is not None:
                    progress_state[0] = expanded
            neighbors_list = []
            for path_segment, neighbor_state in get_macro_neighbors(curr_state, level):
                neighbor_key = neighbor_state.zobrist_hash
                if neighbor_key in path_set:
                    continue
                if has_deadlock(neighbor_state, level):
                    continue
                new_g = g + len(path_segment)
                h = heuristic(neighbor_state, level)
                f = new_g + h
                if f > limit:
                    if f < min_cutoff:
                        min_cutoff = f
                else:
                    neighbors_list.append((f, path_segment, neighbor_state, new_g))
            neighbors_list.sort(key=lambda x: x[0], reverse=True)
            for f, path_segment, neighbor_state, new_g in neighbors_list:
                stack.append((neighbor_state, new_g, curr_exact, path_segment, False))
        if min_cutoff == INFINITY:
            return SolveResult("IDA*", False, expanded=expanded, message="No solution found.")
        limit = min_cutoff

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
            result = _solve_weighted_astar(level, start_time, weight=4.0, stop_event=stop_event, progress_state=progress_state)
        elif algorithm == "Beam Search": 
            result = _solve_beam_search(level, start_time, beam_width=1000, stop_event=stop_event, progress_state=progress_state)
        elif algorithm == "IDA*":
            result = _solve_idastar(level, start_time, stop_event, progress_state)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        result = SolveResult(algorithm, False, message=f"Error: {e.__class__.__name__}")
    elapsed_time_ms = (time.perf_counter() - start_time) * 1000.0
    result.elapsed_ms = elapsed_time_ms
    result.memory_kb = 0.0
    return result