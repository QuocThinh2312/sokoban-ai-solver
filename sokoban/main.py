import queue
import threading
import random
import time
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
}

def load_all_levels() -> List[Level]:
    maps_dir = Path(__file__).resolve().parent.parent / "maps"
    if not maps_dir.is_dir():
        raise SystemExit(f"Levels directory not found: {maps_dir}")
    all_levels = load_levels_from_directory(maps_dir)
    if not all_levels:
        raise SystemExit("No level files found in maps/ directory.")
    return all_levels

def ai_solver_thread(algorithm: str, level: Level, result_queue: queue.Queue, task_id: int, stop_event: threading.Event, progress_state: List[int]) -> None:
    try:
        result = solve(algorithm, level, stop_event, progress_state)
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
    history_ai_steps: List[str] = []
    playback_timer = 0

    manual_move_queue: List[str] = []
    undo_queue = 0       
    map_popup_timer = 0
    popup_close_timer = 0         
    popup_close_action = None

    result_queue = queue.Queue()
    is_solving = False
    current_task_id = 0
    
    stop_event = threading.Event()
    progress_state = [0]
    solve_start_time = 0.0

    def reset_level_state(index: int, message: str) -> None:
        nonlocal game_session, ai_steps, current_result, status_text, is_solving, current_task_id
        
        if is_solving:
            stop_event.set() 
            
        game_session = GameSession(all_levels[index])
        ai_steps = []
        history_ai_steps = []
        ui.is_paused = False
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
                    
                    if not returned_result.found and stop_event.is_set():
                        returned_result.message = "Canceled by user"
                    
                    current_result = returned_result
                    results_by_algo[algo_name] = returned_result
                    
                    if returned_result.found:
                        ai_steps = list(returned_result.actions)
                        history_ai_steps.clear()
                        status_text = f"{algo_name} found a solution in {len(ai_steps)} steps."
                        playback_timer = 0
                    else:
                        status_text = returned_result.message or f"{algo_name} failed to find a solution."
            except queue.Empty:
                pass 

        is_ai_playing = bool(ai_steps and not is_solving)

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
                    ui.register_click(action_type)

                    if action_type in ("select_algo", "temp_select_map"):
                        ui.play_sound("select")
                    else:
                        ui.play_sound("click")

                    if action_type == "select_algo":
                        current_algo = str(action_value)
                        current_result = results_by_algo.get(current_algo)
                        status_text = f"Selected {current_algo}."
                    elif action_type == "restart":
                        game_session.restart()
                        ai_steps.clear()
                        ui.is_paused = False
                        manual_move_queue.clear()
                        undo_queue = 0
                        status_text = "Restarted the current level."
                    elif action_type == "pause" and not ui.is_paused:
                        ui.is_paused = True
                        status_text = "AI Paused."
                    elif action_type == "continue" and ui.is_paused:
                        ui.is_paused = False
                        status_text = "AI Resumed."
                    elif action_type == "undo":
                        ui.register_click("undo")
                        if is_ai_playing or ai_steps or history_ai_steps:
                            ui.is_paused = True
                        undo_queue += 1 
                        manual_move_queue.clear()
                        status_text = f"Queued undo ({undo_queue})."
                    elif action_type == "select_map":
                        ui.register_click("select_map")
                        map_popup_timer = pygame.time.get_ticks() + 150
                    elif action_type == "cancel_map":
                        popup_close_timer = pygame.time.get_ticks() + 150
                        popup_close_action = "cancel_map"
                    elif action_type == "confirm_map":
                        popup_close_timer = pygame.time.get_ticks() + 150
                        popup_close_action = "confirm_map"
                    elif action_type == "random_map":
                        level_index = random.randint(0, len(all_levels) - 1)
                        reset_level_state(level_index, f"Random level: {all_levels[level_index].name}")
                    elif action_type == "cancel_ai": 
                        if is_solving:
                            stop_event.set()
                            status_text = "Cancelling AI..."

            trigger_ai = (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or \
                         (event.type == pygame.MOUSEBUTTONDOWN and action_tuple is not None and action_tuple[0] == "run_ai")
                           
            if trigger_ai:
                ui.register_click("run_ai")
                if is_solving or ai_steps:
                    status_text = "Please wait..."
                    continue
                ui.play_sound("click")
                game_session.restart()
                undo_queue = 0
                ui.is_paused = False
                is_solving = True
                current_result = None
                current_task_id += 1
                
                stop_event.clear()
                progress_state[0] = 0
                solve_start_time = time.perf_counter()
                
                status_text = f"Computing with {current_algo}..."
                threading.Thread(target=ai_solver_thread, args=(current_algo, game_session.level, result_queue, current_task_id, stop_event, progress_state), daemon=True).start()
                continue

            if event.type == pygame.KEYDOWN:
                key = event.key
                
                if key == pygame.K_ESCAPE or key == pygame.K_q:
                    ui.register_click("quit_game")
                    ui.play_sound("click")
                    is_running = False
                
                elif key in KEY_TO_ALGO:
                    ui.play_sound("select")
                    current_algo = KEY_TO_ALGO[key]
                    current_result = results_by_algo.get(current_algo)
                    status_text = f"Selected {current_algo}."
                
                elif key == pygame.K_r:
                    ui.register_click("restart")
                    ui.play_sound("click")
                    game_session.restart()
                    ai_steps.clear()
                    ui.is_paused = False
                    manual_move_queue.clear()
                    undo_queue = 0
                    status_text = "Restarted."
                
                elif key == pygame.K_u:
                    if game_session.history:  
                        ui.register_click("undo")
                        ui.play_sound("click")
                        if is_ai_playing or ai_steps or history_ai_steps:
                            ui.is_paused = True
                        undo_queue += 1 
                        manual_move_queue.clear()
                        status_text = f"Queued undo ({undo_queue})."
                
                elif key == pygame.K_p:
                    if not ui.is_paused and (is_ai_playing or ai_steps):
                        ui.register_click("pause")
                        ui.play_sound("click")
                        ui.is_paused = True
                        status_text = "AI Paused."
                
                elif key == pygame.K_c:
                    if ui.is_paused and (is_ai_playing or ai_steps):
                        ui.register_click("continue")
                        ui.play_sound("click")
                        ui.is_paused = False
                        status_text = "AI Resumed."

                elif key == pygame.K_m:
                    ui.register_click("select_map")
                    ui.play_sound("click")
                    map_popup_timer = pygame.time.get_ticks() + 150

                elif key == pygame.K_n:
                    ui.play_sound("click")
                    level_index = (level_index + 1) % len(all_levels)
                    reset_level_state(level_index, f"Level: {all_levels[level_index].name}")
                    
                elif key in KEY_TO_ACTION and not ai_steps and not is_solving:
                    if len(manual_move_queue) < 3:
                        manual_move_queue.append(KEY_TO_ACTION[key])

        if map_popup_timer > 0 and pygame.time.get_ticks() >= map_popup_timer:
            ui.show_map_list = True
            ui.temp_selected_map_index = level_index
            map_popup_timer = 0

        if popup_close_timer > 0 and pygame.time.get_ticks() >= popup_close_timer:
            ui.show_map_list = False
            if popup_close_action == "confirm_map":
                level_index = ui.temp_selected_map_index
                reset_level_state(level_index, f"Selected level: {all_levels[level_index].name}")
            popup_close_timer = 0
            popup_close_action = None

        is_animating = ui._is_animating(game_session.state.player, game_session.state.boxes)
        
        if undo_queue > 0 and not is_animating and not is_solving:
            if game_session.undo():
                if history_ai_steps:
                    ai_steps.insert(0, history_ai_steps.pop())
            undo_queue -= 1
            
        elif manual_move_queue and not is_animating and not is_solving and undo_queue == 0:
            current_move = manual_move_queue.pop(0) 
            
            if game_session.move(current_move):
                ui.play_sound("move")
                if game_session.has_won():
                    status_text = "AI solved puzzel!"
                    manual_move_queue.clear() 
            else:
                manual_move_queue.clear()
        
        playback_speed_ms = ui.speed_ms

        if is_ai_playing and not ui.is_paused:
            playback_timer += dt
            if playback_timer >= playback_speed_ms:
                playback_timer = 0
                
                current_action = ai_steps.pop(0)
                if game_session.move(current_action):
                    ui.play_sound("move")
                    history_ai_steps.append(current_action)
                    
                    if not ai_steps and game_session.has_won():
                        status_text = "AI solved the puzzle!"

        compute_time = time.perf_counter() - solve_start_time if is_solving else 0.0
        compute_nodes = progress_state[0]

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
            dt=dt,
            compute_time=compute_time,
            compute_nodes=compute_nodes
        )

    pygame.quit()

if __name__ == "__main__":
    main()