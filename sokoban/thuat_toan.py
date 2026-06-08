"""5 thuật toán tìm kiếm cho Sokoban: BFS, DFS, UCS, Greedy, A*."""

import heapq
import sys
import time
from collections import deque
from typing import Optional

from .xu_ly_giai import (
    SolveResult,
    co_deadlock,
    dung_lai_nuoc_di,
    heuristic,
    sinh_ke,
)
from .man_choi import Level
from .trang_thai import State, la_dich


def _khong_co_loi_giai(name: str, expanded: int, t0: float, msg: str) -> SolveResult:
    return SolveResult(
        algorithm=name,
        found=False,
        actions=[],
        expanded=expanded,
        elapsed_ms=(time.perf_counter() - t0) * 1000.0,
        memory_kb=0.0,
        message=msg,
    )


def giai_bfs(level: Level, initial: Optional[State] = None) -> SolveResult:
    name = "BFS"
    t0 = time.perf_counter()
    start = initial or level.trang_thai_dau()
    if la_dich(start, level.goals):
        return SolveResult(name, True, [], 0, 0.0, 0.0)

    frontier = deque([start])
    parent = {start.khoa(): None}
    expanded = 0

    while frontier:
        state = frontier.popleft()
        expanded += 1
        for action, nxt in sinh_ke(state, level):
            k = nxt.khoa()
            if k in parent:
                continue
            if co_deadlock(nxt, level):
                continue
            parent[k] = (state.khoa(), action)
            if la_dich(nxt, level.goals):
                actions = dung_lai_nuoc_di(parent, k)
                return SolveResult(
                    algorithm=name,
                    found=True,
                    actions=actions,
                    expanded=expanded,
                    elapsed_ms=(time.perf_counter() - t0) * 1000.0,
                    memory_kb=sys.getsizeof(parent) / 1024.0,
                )
            frontier.append(nxt)

    return _khong_co_loi_giai(name, expanded, t0, "Không tìm được lời giải.")


def giai_dfs(
    level: Level, initial: Optional[State] = None, max_depth: int = 200
) -> SolveResult:
    name = "DFS"
    t0 = time.perf_counter()
    start = initial or level.trang_thai_dau()
    if la_dich(start, level.goals):
        return SolveResult(name, True, [], 0, 0.0, 0.0)

    stack = [(start, 0)]
    parent = {start.khoa(): None}
    expanded = 0

    while stack:
        state, depth = stack.pop()
        expanded += 1
        if depth >= max_depth:
            continue
        for action, nxt in sinh_ke(state, level):
            k = nxt.khoa()
            if k in parent:
                continue
            if co_deadlock(nxt, level):
                continue
            parent[k] = (state.khoa(), action)
            if la_dich(nxt, level.goals):
                actions = dung_lai_nuoc_di(parent, k)
                return SolveResult(
                    algorithm=name,
                    found=True,
                    actions=actions,
                    expanded=expanded,
                    elapsed_ms=(time.perf_counter() - t0) * 1000.0,
                    memory_kb=sys.getsizeof(parent) / 1024.0,
                )
            stack.append((nxt, depth + 1))

    return _khong_co_loi_giai(
        name, expanded, t0, f"Không tìm được lời giải (độ sâu tối đa={max_depth})."
    )


def giai_ucs(level: Level, initial: Optional[State] = None) -> SolveResult:
    name = "UCS"
    t0 = time.perf_counter()
    start = initial or level.trang_thai_dau()
    if la_dich(start, level.goals):
        return SolveResult(name, True, [], 0, 0.0, 0.0)

    counter = 0
    frontier = [(0, counter, start)]
    best_g = {start.khoa(): 0}
    parent = {start.khoa(): None}
    expanded = 0

    while frontier:
        g, _, state = heapq.heappop(frontier)
        if g > best_g[state.khoa()]:
            continue
        if la_dich(state, level.goals):
            actions = dung_lai_nuoc_di(parent, state.khoa())
            return SolveResult(
                algorithm=name,
                found=True,
                actions=actions,
                expanded=expanded,
                elapsed_ms=(time.perf_counter() - t0) * 1000.0,
                memory_kb=sys.getsizeof(parent) / 1024.0,
            )
        expanded += 1
        for action, nxt in sinh_ke(state, level):
            if co_deadlock(nxt, level):
                continue
            ng = g + 1
            k = nxt.khoa()
            if ng < best_g.get(k, 10**9):
                best_g[k] = ng
                parent[k] = (state.khoa(), action)
                counter += 1
                heapq.heappush(frontier, (ng, counter, nxt))

    return _khong_co_loi_giai(name, expanded, t0, "Không tìm được lời giải.")


def giai_greedy(level: Level, initial: Optional[State] = None) -> SolveResult:
    name = "Greedy"
    t0 = time.perf_counter()
    start = initial or level.trang_thai_dau()
    if la_dich(start, level.goals):
        return SolveResult(name, True, [], 0, 0.0, 0.0)

    counter = 0
    frontier = [(heuristic(start, level), counter, start)]
    parent = {start.khoa(): None}
    visited = {start.khoa()}
    expanded = 0

    while frontier:
        _, _, state = heapq.heappop(frontier)
        if la_dich(state, level.goals):
            actions = dung_lai_nuoc_di(parent, state.khoa())
            return SolveResult(
                algorithm=name,
                found=True,
                actions=actions,
                expanded=expanded,
                elapsed_ms=(time.perf_counter() - t0) * 1000.0,
                memory_kb=sys.getsizeof(parent) / 1024.0,
            )
        expanded += 1
        for action, nxt in sinh_ke(state, level):
            k = nxt.khoa()
            if k in visited:
                continue
            if co_deadlock(nxt, level):
                continue
            visited.add(k)
            parent[k] = (state.khoa(), action)
            counter += 1
            heapq.heappush(frontier, (heuristic(nxt, level), counter, nxt))

    return _khong_co_loi_giai(name, expanded, t0, "Không tìm được lời giải.")


def giai_astar(level: Level, initial: Optional[State] = None) -> SolveResult:
    name = "A*"
    t0 = time.perf_counter()
    start = initial or level.trang_thai_dau()
    if la_dich(start, level.goals):
        return SolveResult(name, True, [], 0, 0.0, 0.0)

    counter = 0
    h0 = heuristic(start, level)
    frontier = [(h0, counter, 0, start)]
    best_g = {start.khoa(): 0}
    parent = {start.khoa(): None}
    expanded = 0

    while frontier:
        f, _, g, state = heapq.heappop(frontier)
        if g > best_g[state.khoa()]:
            continue
        if la_dich(state, level.goals):
            actions = dung_lai_nuoc_di(parent, state.khoa())
            return SolveResult(
                algorithm=name,
                found=True,
                actions=actions,
                expanded=expanded,
                elapsed_ms=(time.perf_counter() - t0) * 1000.0,
                memory_kb=sys.getsizeof(parent) / 1024.0,
            )
        expanded += 1
        for action, nxt in sinh_ke(state, level):
            if co_deadlock(nxt, level):
                continue
            ng = g + 1
            k = nxt.khoa()
            if ng < best_g.get(k, 10**9):
                best_g[k] = ng
                parent[k] = (state.khoa(), action)
                counter += 1
                heapq.heappush(
                    frontier, (ng + heuristic(nxt, level), counter, ng, nxt)
                )

    return _khong_co_loi_giai(name, expanded, t0, "Không tìm được lời giải.")


BO_GIAI = {
    "BFS": giai_bfs,
    "DFS": giai_dfs,
    "UCS": giai_ucs,
    "Greedy": giai_greedy,
    "A*": giai_astar,
}


def giai(name: str, level: Level, initial: Optional[State] = None) -> SolveResult:
    ham_giai = BO_GIAI[name]
    return ham_giai(level, initial)
