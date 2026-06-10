import queue
import threading
import random
from pathlib import Path
from typing import Dict, List, Optional

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
    pygame.K_6: "IDA*",
}

def load_all_levels() -> List[Level]:
    maps_dir = Path(__file__).resolve().parent.parent / "maps"
    if not maps_dir.is_dir():
        raise SystemExit(f"Levels directory not found: {maps_dir}")
    all_levels = load_levels_from_directory(maps_dir)
    if not all_levels:
        raise SystemExit("No level files found in maps/ directory.")
    return all_levels

def ai_solver_thread(algorithm: str, level: Level, result_queue: queue.Queue, task_id: int) -> None:
    try:
        result = solve(algorithm, level)
        result_queue.put((task_id, algorithm, result))
    except Exception as e:
        import traceback
        traceback.print_exc()
        res = SolveResult(algorithm, False, message=f"Error: {e.__class__.__name__}")
        result_queue.put((task_id, algorithm, res))

def main() -> None:
    all_levels = load_all_levels()
    level_names = [m.name for m in all_levels]
    
    ui = GameUI()
    clock = pygame.time.Clock()

    level_index = 0
    game_session = GameSession(all_levels[level_index])
    current_algo = ALGORITHMS[0]
    
    results_by_algo: Dict[str, SolveResult] = {}
    current_result: Optional[SolveResult] = None
    
    status_text = "Select an algorithm, then press Space or Run AI."
    ai_steps: List[str] = []
    
    playback_timer = 0

    result_queue = queue.Queue()
    is_solving = False
    current_task_id = 0

    def reset_level_state(index: int, message: str) -> None:
        nonlocal game_session, ai_steps, current_result, status_text, is_solving, current_task_id
        game_session = GameSession(all_levels[index])
        ai_steps = []
        current_result = None
        results_by_algo.clear()
        is_solving = False
        status_text = message
        current_task_id += 1  
        while not result_queue.empty():
            try:
                result_queue.get_nowait()
            except queue.Empty:
                break

    is_running = True
    while is_running:
        dt = clock.tick(FPS)

        if is_solving:
            try:
                task_id, algo_name, returned_result = result_queue.get_nowait()
                if task_id == current_task_id:
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

            if event.type == pygame.MOUSEWHEEL:
                if ui.show_map_list:
                    ui.map_scroll_y -= event.y * 30
            
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
                        status_text = "Restarted the current level."
                    elif action_type == "pause" and not ui.is_paused:
                        ui.is_paused = True
                        status_text = "AI Paused."
                    elif action_type == "continue" and ui.is_paused:
                        ui.is_paused = False
                        status_text = "AI Resumed."
                    elif action_type == "select_map":
                        ui.show_map_list = True
                        ui.temp_selected_map_index = level_index 
                    elif action_type == "cancel_map":
                        ui.show_map_list = False
                    elif action_type == "confirm_map":
                        ui.show_map_list = False
                        level_index = ui.temp_selected_map_index
                        reset_level_state(level_index, f"Selected level: {all_levels[level_index].name}")
                    elif action_type == "random_map":
                        level_index = random.randint(0, len(all_levels) - 1)
                        reset_level_state(level_index, f"Random level: {all_levels[level_index].name}")
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
                current_task_id += 1
                status_text = f"Computing with {current_algo}..."
                threading.Thread(target=ai_solver_thread, args=(current_algo, game_session.level, result_queue, current_task_id), daemon=True).start()
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
                    status_text = "Restarted."
                elif key == pygame.K_u and game_session.undo():
                    pass
                elif key == pygame.K_n:
                    level_index = (level_index + 1) % len(all_levels)
                    reset_level_state(level_index, f"Level: {all_levels[level_index].name}")
                elif key == pygame.K_p:
                    level_index = (level_index - 1) % len(all_levels)
                    reset_level_state(level_index, f"Level: {all_levels[level_index].name}")
                elif key in KEY_TO_ACTION and not ai_steps and not is_solving:
                    if game_session.move(KEY_TO_ACTION[key]):
                        if game_session.has_won():
                            status_text = "You completed the level!"

        playback_speed_ms = ui.speed_ms
        is_ai_playing = bool(ai_steps and not is_solving)

        if is_ai_playing and not ui.is_paused:
            playback_timer += dt
            if playback_timer >= playback_speed_ms:
                playback_timer = 0
                game_session.move(ai_steps.pop(0))
                if not ai_steps and game_session.has_won():
                    status_text = "AI completed the level!"

        ui.draw(
            game_session=game_session, 
            current_algo=current_algo, 
            current_result=current_result, 
            level_index=level_index, 
            total_levels=len(all_levels), 
            level_names=level_names,
            status_text=status_text, 
            is_solving=is_solving, 
            is_ai_playing=is_ai_playing, 
            results_by_algo=results_by_algo, 
            dt=dt
        )

    pygame.quit()

if __name__ == "__main__":
    main()