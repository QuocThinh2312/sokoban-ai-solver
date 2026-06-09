import queue
import threading
from pathlib import Path
from typing import List, Optional

import pygame

from .ui import GameUI
from .solver_utils import SolveResult
from .constants import ALGORITHMS, FPS
from .level import Level, load_levels_from_directory
from .algorithms import solve
from .game import GameSession

KEY_TO_ACTION = {
    pygame.K_UP: "U", pygame.K_w: "U",
    pygame.K_DOWN: "D", pygame.K_s: "D",
    pygame.K_LEFT: "L", pygame.K_a: "L",
    pygame.K_RIGHT: "R", pygame.K_d: "R",
}

KEY_TO_ALGO = {
    pygame.K_1: "BFS",
    pygame.K_2: "DFS",
    pygame.K_3: "UCS",
    pygame.K_4: "Greedy",
    pygame.K_5: "A*",
}

def load_all_levels() -> List[Level]:
    maps_dir = Path(__file__).resolve().parent.parent / "maps"
    if not maps_dir.is_dir():
        raise SystemExit(f"Levels directory not found: {maps_dir}")
    all_levels = load_levels_from_directory(maps_dir)
    if not all_levels:
        raise SystemExit("No level files found in maps/ directory.")
    return all_levels

def ai_solver_thread(algorithm: str, level: Level, result_queue: queue.Queue) -> None:
    result = solve(algorithm, level)
    result_queue.put((algorithm, result))

def main() -> None:
    all_levels = load_all_levels()
    level_names = [m.name for m in all_levels]
    
    ui = GameUI(max(m.width for m in all_levels), max(m.height for m in all_levels))
    clock = pygame.time.Clock()

    level_index = 0
    game_session = GameSession(all_levels[level_index])
    current_algo = ALGORITHMS[0]
    
    results_by_algo: dict[str, SolveResult] = {}
    current_result: Optional[SolveResult] = None
    
    status_text = "Select an algorithm, then press Space or Run AI."
    show_win_popup = False
    ai_steps: List[str] = []
    
    playback_timer = 0
    playback_speed_ms = 80 

    result_queue = queue.Queue()
    is_solving = False

    def reset_level_state(index: int, message: str):
        nonlocal game_session, ai_steps, current_result, show_win_popup, status_text, is_solving
        game_session = GameSession(all_levels[index])
        ai_steps = []
        current_result = None
        results_by_algo.clear()
        show_win_popup = False
        is_solving = False
        status_text = message

    is_running = True
    while is_running:
        dt = clock.tick(FPS)

        if is_solving:
            try:
                algo_name, returned_result = result_queue.get_nowait()
                is_solving = False
                current_result = returned_result
                results_by_algo[algo_name] = returned_result
                
                if returned_result.found:
                    ai_steps = list(returned_result.actions)
                    status_text = f"{algo_name} found a solution in {len(ai_steps)} steps."
                    playback_timer = 0
                else:
                    status_text = returned_result.message or f"{algo_name} failed to find a solution."
            except queue.Empty:
                pass 

        for event in pygame.event.get():
            action_tuple = None  
            
            if event.type == pygame.QUIT:
                is_running = False
                break

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action_tuple = ui.handle_click(event.pos)
                if action_tuple is not None:
                    action_type, action_value = action_tuple

                    if action_type == "select_algo":
                        current_algo = str(action_value)
                        current_result = results_by_algo.get(current_algo)
                        status_text = f"Selected {current_algo}."
                    elif action_type == "restart":
                        game_session.restart()
                        ai_steps.clear()
                        show_win_popup = False
                        status_text = "Restarted the current level."
                    elif action_type == "undo":
                        if game_session.undo():
                            show_win_popup = False
                            status_text = "Reverted to the previous step."
                    elif action_type == "close_win":
                        show_win_popup = False
                    elif action_type == "next_level":
                        level_index = (level_index + 1) % len(all_levels)
                        reset_level_state(level_index, f"Level: {all_levels[level_index].name}")
                    elif action_type == "select_map_item":
                        level_index = int(str(action_value))
                        reset_level_state(level_index, f"Selected level: {all_levels[level_index].name}")

            trigger_ai = (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or \
                           (event.type == pygame.MOUSEBUTTONDOWN and action_tuple is not None and action_tuple[0] == "run_ai")
                           
            if trigger_ai:
                if is_solving or ai_steps:
                    status_text = "Please wait..."
                    continue
                game_session.restart()
                is_solving = True
                current_result = None
                status_text = f"Computing with {current_algo}..."
                threading.Thread(target=ai_solver_thread, args=(current_algo, game_session.level, result_queue), daemon=True).start()
                continue

            if event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_ESCAPE:
                    is_running = False
                elif key in KEY_TO_ALGO:
                    current_algo = KEY_TO_ALGO[key]
                    current_result = results_by_algo.get(current_algo)
                    status_text = f"Selected {current_algo}."
                elif key == pygame.K_r:
                    game_session.restart()
                    ai_steps.clear()
                    show_win_popup = False
                    status_text = "Restarted."
                elif key == pygame.K_u and game_session.undo():
                    show_win_popup = False
                elif key == pygame.K_n:
                    level_index = (level_index + 1) % len(all_levels)
                    reset_level_state(level_index, f"Level: {all_levels[level_index].name}")
                elif key == pygame.K_p:
                    level_index = (level_index - 1) % len(all_levels)
                    reset_level_state(level_index, f"Level: {all_levels[level_index].name}")
                elif key in KEY_TO_ACTION and not ai_steps and not is_solving:
                    if game_session.move(KEY_TO_ACTION[key]):
                        if game_session.has_won():
                            show_win_popup = True
                            status_text = "You completed the level!"

        if ai_steps and not is_solving:
            playback_timer += dt
            if playback_timer >= playback_speed_ms:
                playback_timer = 0
                game_session.move(ai_steps.pop(0))
                if not ai_steps and game_session.has_won():
                    show_win_popup = True
                    status_text = "AI completed the level!"

        ui.draw(
            game_session, current_algo, current_result, level_index, len(all_levels), level_names,
            status_text, is_solving, show_win_popup, results_by_algo
        )

    pygame.quit()

if __name__ == "__main__":
    main()