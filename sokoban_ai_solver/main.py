import queue
import threading
import random
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Final, Union

import pygame

from .ui import GameUI
from .solver_utils import SolveResult
from .constants import ALGORITHMS, FPS
from .level import Level, load_levels_from_directory
from .algorithms import solve
from .game import GameSession

KEY_TO_ACTION: Final[Dict[int, str]] = {
    pygame.K_UP: "U", pygame.K_w: "U",
    pygame.K_DOWN: "D", pygame.K_s: "D",
    pygame.K_LEFT: "L", pygame.K_a: "L",
    pygame.K_RIGHT: "R", pygame.K_d: "R",
}

_POPUP_DELAY_MS: Final[int] = 150

def load_all_levels() -> List[Level]:
    maps_dir: Path = Path(__file__).resolve().parent.parent / "assets" / "maps"
    if not maps_dir.is_dir():
        raise SystemExit(f"Levels directory not found: {maps_dir}")
    all_levels: List[Level] = load_levels_from_directory(maps_dir)
    if not all_levels:
        raise SystemExit("No level files found in maps/ directory.")
    return all_levels

def ai_solver_thread(
    algorithm: str, 
    level: Level, 
    result_queue: queue.Queue[Tuple[int, str, SolveResult]], 
    task_id: int, 
    stop_event: threading.Event, 
    progress_state: List[int]
) -> None:
    try:
        result: SolveResult = solve(algorithm, level, stop_event, progress_state)
        result_queue.put((task_id, algorithm, result))
    except Exception as e:
        traceback.print_exc()
        res: SolveResult = SolveResult(algorithm, False, message=f"Error: {e.__class__.__name__}")
        result_queue.put((task_id, algorithm, res))

class SokobanApp:
    def __init__(self) -> None:
        self.all_levels: List[Level] = load_all_levels()
        self.level_names: List[str] = [m.name for m in self.all_levels]
        
        self.ui: GameUI = GameUI()
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.is_running: bool = True

        self.level_index: int = 0
        self.game_session: GameSession = GameSession(self.all_levels[self.level_index])
        self.current_algo: str = ALGORITHMS[0]
        
        self.results_by_algo: Dict[str, SolveResult] = {}
        self.current_result: Optional[SolveResult] = None
        self.status_text: str = "Select an algorithm, then press Space or Run AI."
        
        self.ai_steps: List[str] = []
        self.history_ai_steps: List[str] = []
        self.playback_timer: int = 0

        self.manual_move_queue: List[str] = []
        self.undo_queue: int = 0       
        self.map_popup_timer: int = 0
        self.popup_close_timer: int = 0         
        self.popup_close_action: Optional[str] = None

        self.result_queue: queue.Queue[Tuple[int, str, SolveResult]] = queue.Queue()
        self.is_solving: bool = False
        self.current_task_id: int = 0
        
        self.stop_event: threading.Event = threading.Event()
        self.progress_state: List[int] = [0]
        self.solve_start_time: float = 0.0

    @property
    def is_ai_playing(self) -> bool:
        return bool(self.ai_steps and not self.is_solving)

    def reset_level_state(self, index: int, message: str) -> None:
        if self.is_solving:
            self.stop_event.set() 
            
        self.level_index = index
        self.game_session = GameSession(self.all_levels[self.level_index])
        self.ai_steps.clear()
        self.history_ai_steps.clear()
        self.ui.is_paused = False
        self.current_result = None
        self.results_by_algo.clear()
        self.is_solving = False
        self.status_text = message
        self.current_task_id += 1  
        
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

    def _start_ai_solver(self) -> None:
        if self.is_solving or self.ai_steps:
            self.status_text = "Please wait..."
            return
            
        self.ui.play_sound("click")
        self.game_session.restart()
        self.ai_steps.clear()
        self.history_ai_steps.clear()
        self.manual_move_queue.clear()
        self.undo_queue = 0
        self.ui.is_paused = False
        self.is_solving = True
        self.current_result = None
        self.current_task_id += 1
        
        self.stop_event.clear()
        self.progress_state[0] = 0
        self.solve_start_time = time.perf_counter()
        
        self.status_text = f"Computing with {self.current_algo}..."
        threading.Thread(
            target=ai_solver_thread, 
            args=(self.current_algo, self.game_session.level, self.result_queue, self.current_task_id, self.stop_event, self.progress_state), 
            daemon=True
        ).start()

    def _process_solver_results(self) -> None:
        if not self.is_solving:
            return
            
        try:
            task_id: int
            algo_name: str
            returned_result: SolveResult
            task_id, algo_name, returned_result = self.result_queue.get_nowait()
            
            if task_id == self.current_task_id:
                self.is_solving = False
                
                if not returned_result.found and self.stop_event.is_set():
                    returned_result.message = "Canceled by user"
                
                self.current_result = returned_result
                self.results_by_algo[algo_name] = returned_result
                
                if returned_result.found:
                    self.ai_steps = list(returned_result.actions)
                    self.history_ai_steps.clear()
                    self.status_text = f"{algo_name} found a solution in {len(self.ai_steps)} steps."
                    self.playback_timer = 0
                else:
                    self.status_text = returned_result.message or f"{algo_name} failed to find a solution."
        except queue.Empty:
            pass 

    def _handle_mouse_action(self, action_type: str, action_value: Union[int, str, None]) -> None:
        self.ui.register_click(action_type)

        if action_type in ("select_algo", "temp_select_map"):
            self.ui.play_sound("select")
        else:
            self.ui.play_sound("click")

        if action_type == "select_algo":
            self.current_algo = str(action_value)
            self.current_result = self.results_by_algo.get(self.current_algo)
            self.status_text = f"Selected {self.current_algo}."
        elif action_type == "restart":
            self.game_session.restart()
            self.ai_steps.clear()
            self.history_ai_steps.clear()
            self.ui.is_paused = False
            self.manual_move_queue.clear()
            self.undo_queue = 0
            self.status_text = "Restarted the current level."
        elif action_type == "pause" and not self.ui.is_paused:
            self.ui.is_paused = True
            self.status_text = "AI Paused."
        elif action_type == "continue" and self.ui.is_paused:
            self.ui.is_paused = False
            self.status_text = "AI Resumed."
        elif action_type == "undo":
            if self.is_ai_playing or self.ai_steps or self.history_ai_steps:
                self.ui.is_paused = True
            self.undo_queue += 1 
            self.manual_move_queue.clear()
            self.status_text = f"Queued undo ({self.undo_queue})."
        elif action_type == "select_map":
            self.map_popup_timer = pygame.time.get_ticks() + _POPUP_DELAY_MS
        elif action_type == "cancel_map":
            self.popup_close_timer = pygame.time.get_ticks() + _POPUP_DELAY_MS
            self.popup_close_action = "cancel_map"
        elif action_type == "confirm_map":
            self.popup_close_timer = pygame.time.get_ticks() + _POPUP_DELAY_MS
            self.popup_close_action = "confirm_map"
        elif action_type == "random_map":
            random_idx: int = random.randint(0, len(self.all_levels) - 1)
            self.reset_level_state(random_idx, f"Random level: {self.all_levels[random_idx].name}")
        elif action_type == "cancel_ai": 
            if self.is_solving:
                self.stop_event.set()
                self.status_text = "Cancelling AI..."

    def _handle_keyboard_action(self, key: int) -> None:
        if key == pygame.K_ESCAPE or key == pygame.K_q:
            self.ui.register_click("quit_game")
            self.ui.play_sound("click")
            self.is_running = False
        
        elif key == pygame.K_r:
            self.ui.register_click("restart")
            self.ui.play_sound("click")
            self.game_session.restart()
            self.ai_steps.clear()
            self.history_ai_steps.clear()
            self.ui.is_paused = False
            self.manual_move_queue.clear()
            self.undo_queue = 0
            self.status_text = "Restarted."
        
        elif key == pygame.K_u:
            if self.game_session.history:  
                self.ui.register_click("undo")
                self.ui.play_sound("click")
                if self.is_ai_playing or self.ai_steps or self.history_ai_steps:
                    self.ui.is_paused = True
                self.undo_queue += 1 
                self.manual_move_queue.clear()
                self.status_text = f"Queued undo ({self.undo_queue})."
        
        elif key == pygame.K_p:
            if not self.ui.is_paused and (self.is_ai_playing or self.ai_steps):
                self.ui.register_click("pause")
                self.ui.play_sound("click")
                self.ui.is_paused = True
                self.status_text = "AI Paused."
        
        elif key == pygame.K_c:
            if self.ui.is_paused and (self.is_ai_playing or self.ai_steps):
                self.ui.register_click("continue")
                self.ui.play_sound("click")
                self.ui.is_paused = False
                self.status_text = "AI Resumed."

        elif key == pygame.K_m:
            self.ui.register_click("select_map")
            self.ui.play_sound("click")
            self.map_popup_timer = pygame.time.get_ticks() + _POPUP_DELAY_MS

        elif key == pygame.K_n:
            self.ui.play_sound("click")
            next_idx: int = (self.level_index + 1) % len(self.all_levels)
            self.reset_level_state(next_idx, f"Level: {self.all_levels[next_idx].name}")
            
        elif key in KEY_TO_ACTION and not self.ai_steps and not self.is_solving:
            if len(self.manual_move_queue) < 3:
                self.manual_move_queue.append(KEY_TO_ACTION[key])

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            action_tuple: Optional[Tuple[str, Union[int, str, None]]] = None  

            if event.type == pygame.MOUSEWHEEL:
                if self.ui.show_map_list:
                    self.ui.map_scroll_y -= event.y * 30
            
            elif event.type == pygame.QUIT:
                self.is_running = False
                return

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action_tuple = self.ui.handle_click(event.pos)
                if action_tuple is not None:
                    self._handle_mouse_action(action_tuple[0], action_tuple[1])

            trigger_ai: bool = (
                (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or 
                (event.type == pygame.MOUSEBUTTONDOWN and action_tuple is not None and action_tuple[0] == "run_ai")
            )
                           
            if trigger_ai:
                self.ui.register_click("run_ai")
                self._start_ai_solver()
                continue

            if event.type == pygame.KEYDOWN:
                self._handle_keyboard_action(event.key)

    def _update_state(self, dt: int) -> None:
        current_time: int = pygame.time.get_ticks()
        
        if self.map_popup_timer > 0 and current_time >= self.map_popup_timer:
            self.ui.show_map_list = True
            self.ui.temp_selected_map_index = self.level_index
            self.map_popup_timer = 0

        if self.popup_close_timer > 0 and current_time >= self.popup_close_timer:
            self.ui.show_map_list = False
            if self.popup_close_action == "confirm_map":
                self.reset_level_state(self.ui.temp_selected_map_index, f"Selected level: {self.all_levels[self.ui.temp_selected_map_index].name}")
            self.popup_close_timer = 0
            self.popup_close_action = None

        is_animating: bool = self.ui._is_animating(self.game_session.state.player, self.game_session.state.boxes)
        
        if self.undo_queue > 0 and not is_animating and not self.is_solving:
            if self.game_session.undo():
                if self.history_ai_steps:
                    self.ai_steps.insert(0, self.history_ai_steps.pop())
            self.undo_queue -= 1
            
        elif self.manual_move_queue and not is_animating and not self.is_solving and self.undo_queue == 0:
            current_move: str = self.manual_move_queue.pop(0) 
            
            if self.game_session.move(current_move):
                self.ui.play_sound("move")
                if self.game_session.has_won():
                    self.status_text = "AI solved the puzzle!"
                    self.manual_move_queue.clear() 
            else:
                self.manual_move_queue.clear()
        
        if self.is_ai_playing and not self.ui.is_paused:
            self.playback_timer += dt
            if self.playback_timer >= self.ui.speed_ms:
                self.playback_timer = 0
                
                current_action: str = self.ai_steps.pop(0)
                if self.game_session.move(current_action):
                    self.ui.play_sound("move")
                    self.history_ai_steps.append(current_action)
                    
                    if not self.ai_steps and self.game_session.has_won():
                        self.status_text = "AI solved the puzzle!"

    def _render(self, dt: int) -> None:
        compute_time: float = time.perf_counter() - self.solve_start_time if self.is_solving else 0.0
        compute_nodes: int = self.progress_state[0]

        self.ui.draw(
            game_session=self.game_session, 
            current_algo=self.current_algo, 
            current_result=self.current_result, 
            level_index=self.level_index, 
            total_levels=len(self.all_levels), 
            level_names=self.level_names,
            status_text=self.status_text, 
            is_solving=self.is_solving, 
            is_ai_playing=self.is_ai_playing, 
            results_by_algo=self.results_by_algo, 
            dt=dt,
            compute_time=compute_time,
            compute_nodes=compute_nodes
        )

    def run(self) -> None:
        while self.is_running:
            dt: int = self.clock.tick(FPS)
            self._process_solver_results()
            self._handle_events()
            self._update_state(dt)
            self._render(dt)

def main() -> None:
    app: SokobanApp = SokobanApp()
    app.run()
    pygame.quit()

if __name__ == "__main__":
    main()