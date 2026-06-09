import heapq
import time
import tracemalloc
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from .level import Level
from .state import State, is_goal
from .solver_utils import SolveResult, has_deadlock, reconstruct_path, heuristic, get_neighbors


def _solve_bfs(level: Level) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.get_key()

    if is_goal(start_state, level.goals):
        return SolveResult("BFS", True, actions=[])

    queue = deque([start_state])
    parent: Dict[object, Optional[Tuple[object, str]]] = {start_key: None}
    visited: Set[object] = {start_key}
    expanded = 0

    while queue:
        curr_state = queue.popleft()
        expanded += 1

        curr_key = curr_state.get_key()

        for action, neighbor_state in get_neighbors(curr_state, level):
            neighbor_key = neighbor_state.get_key()

            if neighbor_key in visited:
                continue

            if has_deadlock(neighbor_state, level):
                continue

            parent[neighbor_key] = (curr_key, action)

            if is_goal(neighbor_state, level.goals):
                actions = reconstruct_path(parent, neighbor_key)
                return SolveResult("BFS", True, actions, expanded)

            visited.add(neighbor_key)
            queue.append(neighbor_state)

    return SolveResult("BFS", False, expanded=expanded, message="No solution found.")


def _solve_dfs(level: Level) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.get_key()

    if is_goal(start_state, level.goals):
        return SolveResult("DFS", True, actions=[])

    stack = [(start_state, 0)]
    parent: Dict[object, Optional[Tuple[object, str]]] = {start_key: None}
    
    best_depth: Dict[object, int] = {start_key: 0}
    expanded = 0

    while stack:
        curr_state, depth = stack.pop()
        curr_key = curr_state.get_key()

        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_key)
            return SolveResult("DFS", True, actions, expanded)

        if depth > best_depth.get(curr_key, float('inf')):
            continue

        expanded += 1

        for action, neighbor_state in get_neighbors(curr_state, level):
            neighbor_key = neighbor_state.get_key()
            new_depth = depth + 1

            if has_deadlock(neighbor_state, level):
                continue

            if new_depth < best_depth.get(neighbor_key, float('inf')):
                best_depth[neighbor_key] = new_depth
                parent[neighbor_key] = (curr_key, action)
                stack.append((neighbor_state, new_depth))

    return SolveResult("DFS", False, expanded=expanded, message="No solution found.")


def _solve_ucs(level: Level) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.get_key()

    counter = 0
    priority_queue = [(0, counter, start_state)]
    
    parent: Dict[object, Optional[Tuple[object, str]]] = {start_key: None}
    best_cost: Dict[object, int] = {start_key: 0}
    expanded = 0

    while priority_queue:
        g, _, curr_state = heapq.heappop(priority_queue)
        curr_key = curr_state.get_key()

        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_key)
            return SolveResult("UCS", True, actions, expanded)

        if g > best_cost.get(curr_key, float('inf')):
            continue

        expanded += 1

        for action, neighbor_state in get_neighbors(curr_state, level):
            neighbor_key = neighbor_state.get_key()
            new_g = g + 1  

            if has_deadlock(neighbor_state, level):
                continue

            if new_g < best_cost.get(neighbor_key, float('inf')):
                best_cost[neighbor_key] = new_g
                parent[neighbor_key] = (curr_key, action)
                counter += 1
                heapq.heappush(priority_queue, (new_g, counter, neighbor_state))

    return SolveResult("UCS", False, expanded=expanded, message="No solution found.")


def _solve_greedy(level: Level) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.get_key()

    counter = 0
    priority_queue = [(heuristic(start_state, level), counter, start_state)]
    
    parent: Dict[object, Optional[Tuple[object, str]]] = {start_key: None}
    visited: Set[object] = {start_key}
    expanded = 0

    while priority_queue:
        _, _, curr_state = heapq.heappop(priority_queue)
        curr_key = curr_state.get_key()
        expanded += 1

        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_key)
            return SolveResult("Greedy", True, actions, expanded)

        for action, neighbor_state in get_neighbors(curr_state, level):
            neighbor_key = neighbor_state.get_key()

            if neighbor_key in visited:
                continue

            if has_deadlock(neighbor_state, level):
                continue

            parent[neighbor_key] = (curr_key, action)
            visited.add(neighbor_key)
            new_h = heuristic(neighbor_state, level)
            counter += 1
            heapq.heappush(priority_queue, (new_h, counter, neighbor_state))

    return SolveResult("Greedy", False, expanded=expanded, message="No solution found.")


def _solve_astar(level: Level) -> SolveResult:
    start_state = level.initial_state()
    start_key = start_state.get_key()

    counter = 0
    start_h = heuristic(start_state, level)
    priority_queue = [(start_h, counter, 0, start_state)]
    
    parent: Dict[object, Optional[Tuple[object, str]]] = {start_key: None}
    best_g_cost: Dict[object, int] = {start_key: 0}
    expanded = 0

    while priority_queue:
        f, _, g, curr_state = heapq.heappop(priority_queue)
        curr_key = curr_state.get_key()

        if is_goal(curr_state, level.goals):
            actions = reconstruct_path(parent, curr_key)
            return SolveResult("A*", True, actions, expanded)

        if g > best_g_cost.get(curr_key, float('inf')):
            continue

        expanded += 1

        for action, neighbor_state in get_neighbors(curr_state, level):
            neighbor_key = neighbor_state.get_key()
            new_g = g + 1

            if has_deadlock(neighbor_state, level):
                continue

            if new_g < best_g_cost.get(neighbor_key, float('inf')):
                best_g_cost[neighbor_key] = new_g
                parent[neighbor_key] = (curr_key, action)
                
                new_h = heuristic(neighbor_state, level)
                new_f = new_g + new_h
                counter += 1
                heapq.heappush(priority_queue, (new_f, counter, new_g, neighbor_state))

    return SolveResult("A*", False, expanded=expanded, message="No solution found.")


def solve(algorithm: str, level: Level) -> SolveResult:
    tracemalloc.start()
    start_time = time.perf_counter()

    if algorithm == "BFS":
        result = _solve_bfs(level)
    elif algorithm == "DFS":
        result = _solve_dfs(level)
    elif algorithm == "UCS":
        result = _solve_ucs(level)
    elif algorithm == "Greedy":
        result = _solve_greedy(level)
    elif algorithm == "A*":
        result = _solve_astar(level)
    else:
        tracemalloc.stop()
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    elapsed_time_ms = (time.perf_counter() - start_time) * 1000.0
    _, peak_memory_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result.elapsed_ms = elapsed_time_ms
    result.memory_kb = peak_memory_bytes / 1024.0

    return result