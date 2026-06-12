import math
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any

import pygame
import numpy as np
from scipy.optimize import linear_sum_assignment

from .solver_utils import SolveResult
from .constants import (
    ALGORITHMS, COLOR_BG, COLOR_BORDER, COLOR_BOX_FALLBACK,
    COLOR_BOX_ON_GOAL_FALLBACK, COLOR_GOAL_FALLBACK,
    COLOR_HIGHLIGHT, COLOR_PANEL, COLOR_PLAYER_FALLBACK, COLOR_PRIMARY, COLOR_PRIMARY_DIM,
    COLOR_SECONDARY, COLOR_TERTIARY, COLOR_TEXT, COLOR_TEXT_DIM,
    DASHBOARD_WIDTH, HEADER_HEIGHT, SIDEBAR_WIDTH,
    MIN_SPEED_MS, MAX_SPEED_MS, DEFAULT_SPEED_MS
)
from .game import GameSession

ASSETS_DIR: Path = Path(__file__).resolve().parent.parent / "assets"

RETRO_FLOOR: Tuple[int, int, int] = (218, 212, 186)

class GameUI:
    def __init__(self) -> None:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption("Sokoban AI")

        self.screen: pygame.Surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.window_width: int = self.screen.get_width()
        self.window_height: int = self.screen.get_height()
        
        self.tile_size: int = 32
        self.board_ox: int = 0
        self.board_oy: int = 0

        self.speed_ms: int = DEFAULT_SPEED_MS
        self.is_dragging_slider: bool = False

        self.anim_player_pos: Optional[Tuple[float, float]] = None
        self.anim_boxes: List[Tuple[float, float]] = []

        self.font: pygame.font.Font
        self.font_small: pygame.font.Font
        self.font_tiny: pygame.font.Font
        self.font_bold: pygame.font.Font
        self.font_large: pygame.font.Font
        self.font_metric: pygame.font.Font
        self._load_custom_fonts()
        
        self._asset_cache: Dict[Tuple[Any, ...], pygame.Surface] = {}
        self.assets: Dict[str, Optional[pygame.Surface]] = self._load_assets()
        
        self.show_map_list: bool = False
        self.algo_rects: Dict[str, pygame.Rect] = {}
        self.button_rects: Dict[str, pygame.Rect] = {}
        self.map_rects: Dict[int, pygame.Rect] = {}
        
        self.slider_rect: pygame.Rect = pygame.Rect(20, self.window_height - 60, SIDEBAR_WIDTH - 40, 14)

        self.map_scroll_y: int = 0
        self.max_scroll_y: int = 0
        self.temp_selected_map_index: int = 0
        self.popup_rect: Optional[pygame.Rect] = None
        self.is_paused: bool = False

        self.is_dragging_map_scroll: bool = False
        self.scrollbar_track_rect: Optional[pygame.Rect] = None

        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.last_sound_ticks: Dict[str, int] = {"move": 0, "click": 0}
        self.win_sound_played: bool = False
        self._load_sounds()

    def _load_sounds(self) -> None:
        audio_dir = ASSETS_DIR / "audio"
        
        sound_files = {
            "click": "click.ogg",
            "move": "move.ogg",
            "select": "select.ogg",
            "win": "win.ogg"
        }
        
        for key, filename in sound_files.items():
            path = audio_dir / filename
            if path.exists():
                try:
                    snd = pygame.mixer.Sound(str(path))
                    if key == "move": snd.set_volume(0.1)
                    elif key == "click": snd.set_volume(0.2)
                    elif key == "select": snd.set_volume(0.05)
                    elif key == "win": snd.set_volume(0.05)
                    self.sounds[key] = snd
                except Exception:
                    self.sounds[key] = None
            else:
                self.sounds[key] = None
                
        bgm_path = audio_dir / "bgm.ogg" 
        if bgm_path.exists():
            try:
                pygame.mixer.music.load(str(bgm_path))
                pygame.mixer.music.set_volume(0.1) 
                pygame.mixer.music.play(-1)
            except Exception:
                pass

    def play_sound(self, key: str) -> None:
        sound = self.sounds.get(key)
        
        if sound is None:
            return
            
        now = pygame.time.get_ticks()
        if key == "move" and now - self.last_sound_ticks.get("move", 0) < 50:
            return
            
        self.last_sound_ticks[key] = now
        
        sound.play()

    def _load_custom_fonts(self) -> None:
        font_path = ASSETS_DIR / "PressStart2P.ttf"
        try:
            if font_path.exists():
                self.font = pygame.font.Font(str(font_path), 14)
                self.font_small = pygame.font.Font(str(font_path), 12)
                self.font_tiny = pygame.font.Font(str(font_path), 10)
                self.font_bold = pygame.font.Font(str(font_path), 14)
                self.font_large = pygame.font.Font(str(font_path), 20)
                self.font_metric = pygame.font.Font(str(font_path), 16)
            else:
                raise FileNotFoundError
        except Exception:
            sys_font = "courier"
            self.font = pygame.font.SysFont(sys_font, 18, bold=True)
            self.font_small = pygame.font.SysFont(sys_font, 16, bold=True)
            self.font_tiny = pygame.font.SysFont(sys_font, 14)
            self.font_bold = pygame.font.SysFont(sys_font, 18, bold=True)
            self.font_large = pygame.font.SysFont(sys_font, 26, bold=True)
            self.font_metric = pygame.font.SysFont(sys_font, 22, bold=True)

    def _load_assets(self) -> Dict[str, Optional[pygame.Surface]]:
        result: Dict[str, Optional[pygame.Surface]] = {}
        
        img_dir = ASSETS_DIR / "img"
        
        asset_files: Dict[str, str] = {
            "wall": "wall.png", 
            "box": "box.jpg", 
            "box_on_goal": "box_on_goal.jpg", 
            "goal": "target.png",
            "player": "character.png"
        }
        
        for key, filename in asset_files.items():
            try:
                asset_path = str(img_dir / filename)
                
                if filename.endswith(".jpg"):
                    img = pygame.image.load(asset_path).convert()
                else:
                    img = pygame.image.load(asset_path).convert_alpha()
                    
                    if key == "goal":
                        bounding_rect = img.get_bounding_rect()
                        img = img.subsurface(bounding_rect).copy()
                        
                result[key] = img
            except (pygame.error, FileNotFoundError):
                result[key] = None
                
        return result

    def _lighten_color(self, base_color: Tuple[int, int, int], amount: int) -> Tuple[int, int, int]:
        return (
            min(255, base_color[0] + amount),
            min(255, base_color[1] + amount),
            min(255, base_color[2] + amount)
        )

    def _calculate_dynamic_viewport(self, map_width: int, map_height: int) -> None:
        center_w = self.window_width - SIDEBAR_WIDTH - DASHBOARD_WIDTH - 40
        center_h = self.window_height - HEADER_HEIGHT - 60
        
        max_tile_w = center_w // max(1, map_width)
        max_tile_h = center_h // max(1, map_height)
        
        self.tile_size = min(max_tile_w, max_tile_h, 64)
        
        board_pixel_w = self.tile_size * map_width
        board_pixel_h = self.tile_size * map_height
        
        self.board_ox = SIDEBAR_WIDTH + 20 + (center_w - board_pixel_w) // 2
        self.board_oy = HEADER_HEIGHT + 20 + (center_h - board_pixel_h) // 2

    def _get_scaled_asset(self, key: str, custom_size: Optional[int] = None) -> Optional[pygame.Surface]:
        size = custom_size if custom_size is not None else self.tile_size
        size = max(1, int(size))
        
        image = self.assets.get(key)
        if image is None: 
            return None
            
        cache_key = (key, size)
        if cache_key not in self._asset_cache:
            self._asset_cache[cache_key] = pygame.transform.scale(image, (size, size))
            
        return self._asset_cache[cache_key]

    def _get_player_sprite(self) -> Optional[pygame.Surface]:
        image = self.assets.get("player")
        if image is None: 
            return None
        cache_key = ("player_static", self.tile_size)
        if cache_key not in self._asset_cache:
            self._asset_cache[cache_key] = pygame.transform.scale(image, (self.tile_size, self.tile_size))
        return self._asset_cache[cache_key]

    def _process_slider(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        if mouse_pressed:
            if self.slider_rect.collidepoint(mouse_pos):
                self.is_dragging_slider = True
        else:
            self.is_dragging_slider = False

        if self.is_dragging_slider:
            rel_x = min(max(mouse_pos[0] - self.slider_rect.x, 0), self.slider_rect.width)
            ratio = rel_x / self.slider_rect.width
            self.speed_ms = MAX_SPEED_MS - int(ratio * (MAX_SPEED_MS - MIN_SPEED_MS))

    def _process_map_scrollbar(self) -> None:
        if not self.show_map_list or self.max_scroll_y <= 0 or self.scrollbar_track_rect is None:
            self.is_dragging_map_scroll = False
            return

        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        if mouse_pressed:
            hit_rect = self.scrollbar_track_rect.inflate(40, 0)
            if hit_rect.collidepoint(mouse_pos) or self.is_dragging_map_scroll:
                self.is_dragging_map_scroll = True
        else:
            self.is_dragging_map_scroll = False

        if self.is_dragging_map_scroll:
            track_y = self.scrollbar_track_rect.y
            track_h = self.scrollbar_track_rect.height
            
            rel_y = min(max(mouse_pos[1] - track_y, 0), track_h)
            
            ratio = rel_y / track_h
            self.map_scroll_y = int(ratio * self.max_scroll_y)

    def _update_animations(self, target_player: Tuple[int, int], target_boxes: Tuple[Tuple[int, int], ...], dt: int) -> None:
        if self.speed_ms < 15:
            self.anim_player_pos = (float(target_player[0]), float(target_player[1]))
            self.anim_boxes = [(float(b[0]), float(b[1])) for b in target_boxes]
            return

        step = dt / float(max(1, self.speed_ms))

        c_r, c_c = self.anim_player_pos if self.anim_player_pos else (float(target_player[0]), float(target_player[1]))
        t_r, t_c = float(target_player[0]), float(target_player[1])

        dist = math.hypot(t_r - c_r, t_c - c_c)
        if dist > 1.5: 
            self.anim_player_pos = (t_r, t_c) 
        elif dist <= step:
            self.anim_player_pos = (t_r, t_c) 
        else:
            self.anim_player_pos = (c_r + (t_r - c_r) / dist * step, c_c + (t_c - c_c) / dist * step)

        if len(self.anim_boxes) != len(target_boxes):
            self.anim_boxes = [(float(b[0]), float(b[1])) for b in target_boxes]
        else:
            n_boxes = len(target_boxes)
            cost_matrix = np.zeros((n_boxes, n_boxes), dtype=float)
            
            for i, vb in enumerate(self.anim_boxes):
                for j, tb in enumerate(target_boxes):
                    cost_matrix[i, j] = math.hypot(vb[0] - float(tb[0]), vb[1] - float(tb[1]))
            
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            new_anim_boxes: List[Tuple[float, float]] = [(0.0, 0.0)] * n_boxes
            
            for idx in range(n_boxes):
                v_idx = row_ind[idx]
                t_idx = col_ind[idx]
                
                vb_r, vb_c = self.anim_boxes[v_idx]
                tb_r, tb_c = float(target_boxes[t_idx][0]), float(target_boxes[t_idx][1])
                b_dist = cost_matrix[v_idx, t_idx]
                
                if b_dist > 1.5:
                    new_pos = (tb_r, tb_c)
                elif b_dist <= step:
                    new_pos = (tb_r, tb_c)
                else:
                    new_pos = (
                        vb_r + (tb_r - vb_r) / b_dist * step,
                        vb_c + (tb_c - vb_c) / b_dist * step
                    )
                
                new_anim_boxes[t_idx] = new_pos
                
            self.anim_boxes = new_anim_boxes

    def _is_animating(self, target_player: Tuple[int, int], target_boxes: Tuple[Tuple[int, int], ...]) -> bool:
        if self.anim_player_pos:
            if abs(self.anim_player_pos[0] - target_player[0]) > 0.05 or abs(self.anim_player_pos[1] - target_player[1]) > 0.05:
                return True
        for i, vb in enumerate(self.anim_boxes):
            if i < len(target_boxes):
                tb = target_boxes[i]
                if abs(vb[0] - tb[0]) > 0.05 or abs(vb[1] - tb[1]) > 0.05:
                    return True
        return False

    def handle_click(self, pos: Tuple[int, int]) -> Optional[Tuple[str, Any]]:
        if self.show_map_list:
            for key in ["cancel_map", "confirm_map"]:
                if key in self.button_rects and self.button_rects[key].collidepoint(pos):
                    return (key, None)
            
            for index, rect in self.map_rects.items():
                if rect.collidepoint(pos):
                    self.temp_selected_map_index = index
                    return ("temp_select_map", index)
            
            if self.popup_rect and not self.popup_rect.collidepoint(pos):
                return ("cancel_map", None)
                
            return None 

        for key, rect in self.algo_rects.items():
            if rect.collidepoint(pos): 
                return ("select_algo", key)
                
        for key, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                if key == "quit_game":
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                return (key, None)
                
        return None

    def draw(self, game_session: GameSession, current_algo: str, current_result: Optional[SolveResult], 
           level_index: int, total_levels: int, level_names: List[str], status_text: str, 
           is_solving: bool, is_ai_playing: bool = False,
           results_by_algo: Optional[Dict[str, SolveResult]] = None, dt: int = 16,
           compute_time: float = 0.0, compute_nodes: int = 0) -> None:
           
        if results_by_algo is None: 
            results_by_algo = {}
        
        self.algo_rects.clear()
        self.button_rects.clear()
        self.map_rects.clear()

        self._process_slider()
        self._process_map_scrollbar()
        self._calculate_dynamic_viewport(game_session.level.width, game_session.level.height)

        self.screen.fill(COLOR_BG)
        self._draw_board(game_session, is_ai_playing, dt)
        self._draw_sidebar(current_algo, results_by_algo, is_solving, is_ai_playing, compute_time, compute_nodes)
        self._draw_dashboard(game_session, current_result, level_index, total_levels, is_ai_playing, is_solving)
        self._draw_header() 
        
        if self.show_map_list: 
            self._draw_map_popup(level_names, level_index)
            
        if game_session.has_won() and not self._is_animating(game_session.state.player, game_session.state.boxes):
            if not self.win_sound_played:
                self.play_sound("win")
                self.win_sound_played = True
            self._draw_subtle_win_notification()
        elif not game_session.has_won():
            self.win_sound_played = False
            
        all_interactive_rects = list(self.algo_rects.values()) + list(self.button_rects.values()) + [self.slider_rect]
        
        if self.show_map_list:
            all_interactive_rects.extend(list(self.map_rects.values()))
            
            scroll_rect = self.scrollbar_track_rect
            if scroll_rect is not None:
                all_interactive_rects.append(scroll_rect.inflate(20, 0))

        is_hovering_clickable = any(r.collidepoint(pygame.mouse.get_pos()) for r in all_interactive_rects)
        is_dragging_any = getattr(self, 'is_dragging_map_scroll', False) or self.is_dragging_slider
        
        if is_hovering_clickable or is_dragging_any:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            
        pygame.display.flip()

    def _draw_subtle_win_notification(self) -> None:
        text_surf = self.font_large.render("PUZZLE SOLVED!", True, COLOR_TERTIARY)
        center_x = SIDEBAR_WIDTH + (self.window_width - SIDEBAR_WIDTH - DASHBOARD_WIDTH) // 2
        
        center_y = HEADER_HEIGHT + (self.board_oy - HEADER_HEIGHT) // 2
        
        bg_rect = text_surf.get_rect(center=(center_x, center_y))
        bg_rect.inflate_ip(40, 20)
        
        s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        s.fill((35, 35, 45, 230))
        
        self.screen.blit(s, bg_rect.topleft)
        pygame.draw.rect(self.screen, COLOR_TERTIARY, bg_rect, 2)
        self.screen.blit(text_surf, text_surf.get_rect(center=bg_rect.center))

    def _draw_panel(self, rect: pygame.Rect, color: Tuple[int, int, int] = COLOR_PANEL) -> None:
        pygame.draw.rect(self.screen, (5, 5, 10), rect.move(6, 6))
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, 3)

    def _draw_header(self) -> None:
        rect = pygame.Rect(0, 0, self.window_width, HEADER_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_PANEL, rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, 3)
        
        self.screen.blit(self.font_large.render("SOKOBAN", True, COLOR_PRIMARY), (20, 18))
        self.screen.blit(self.font_bold.render("AI SOLVER", True, COLOR_TEXT), (160, 22))

    def _draw_sidebar(self, current_algo: str, results_by_algo: Dict[str, SolveResult], is_solving: bool, is_ai_playing: bool, compute_time: float, compute_nodes: int) -> None:
        rect = pygame.Rect(0, HEADER_HEIGHT - 3, SIDEBAR_WIDTH, self.window_height - HEADER_HEIGHT + 3)
        self._draw_panel(rect)
        x, y = 20, HEADER_HEIGHT + 20
        self.screen.blit(self.font_bold.render("ALGORITHMS", True, COLOR_PRIMARY), (x, y))
        y += 40
        
        lock_algos = is_solving or is_ai_playing
        
        for algo_name in ALGORITHMS:
            is_active = (algo_name == current_algo)
            row_rect = pygame.Rect(x, y, SIDEBAR_WIDTH - 40, 44) 
            
            if lock_algos:
                is_hovered = False
                bg_col = (50, 50, 60) if is_active else (30, 30, 35)
                border_col = (80, 80, 90) if is_active else (40, 40, 45)
                text_col = (150, 150, 160) if is_active else (90, 90, 100)
                step_col = (100, 100, 110)
            else:
                self.algo_rects[algo_name] = row_rect
                is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
                bg_col = COLOR_PRIMARY_DIM if is_active else (35, 35, 45) if is_hovered else COLOR_BG
                border_col = COLOR_PRIMARY if is_active else COLOR_BORDER
                text_col = COLOR_BG if is_active else COLOR_TEXT
                step_col = COLOR_BG if is_active else COLOR_TEXT_DIM
                
            pygame.draw.rect(self.screen, bg_col, row_rect)
            pygame.draw.rect(self.screen, border_col, row_rect, 2)
            
            display_font = self.font_small if len(algo_name) >= 9 else self.font_bold
            offset_y = 15 if len(algo_name) >= 9 else 13
            self.screen.blit(display_font.render(algo_name, True, text_col), (x + 12, y + offset_y))
            
            result = results_by_algo.get(algo_name)
            steps_text = f"Steps:{result.steps}" if (result is not None and result.found) else ""
            surf = self.font_tiny.render(steps_text, True, step_col)
            self.screen.blit(surf, (x + row_rect.width - surf.get_width() - 8, y + 17))
            y += 52
            
        y += 15 
        self.screen.blit(self.font_small.render("AI SPEED:", True, COLOR_PRIMARY), (x, y))
        y += 35
        self.slider_rect = pygame.Rect(20, y, SIDEBAR_WIDTH - 40, 14)
        
        pygame.draw.rect(self.screen, (10, 10, 10), self.slider_rect.move(2, 2))
        pygame.draw.rect(self.screen, COLOR_BG, self.slider_rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.slider_rect, 2)
        
        ratio = (MAX_SPEED_MS - self.speed_ms) / (MAX_SPEED_MS - MIN_SPEED_MS)
        fill_w = int(ratio * self.slider_rect.width)
        pygame.draw.rect(self.screen, COLOR_SECONDARY, (self.slider_rect.x, self.slider_rect.y, fill_w, self.slider_rect.height))
        pygame.draw.rect(self.screen, COLOR_TEXT, (self.slider_rect.x + fill_w - 5, self.slider_rect.y - 4, 10, 22))

        btn_y = self.window_height - 68 
        
        if is_solving:
            info_y = btn_y - 45
            self.screen.blit(self.font_small.render("COMPUTING...", True, COLOR_SECONDARY), (x, info_y))
            time_str = f"{min(60.0, compute_time):.1f}s"
            self.screen.blit(self.font_small.render(time_str, True, COLOR_HIGHLIGHT), (x + 150, info_y))
            
            node_str = f"Nodes: {compute_nodes:,}"
            self.screen.blit(self.font_tiny.render(node_str, True, COLOR_TEXT_DIM), (x, info_y + 20))
            
            btn_rect = pygame.Rect(x, btn_y, SIDEBAR_WIDTH - 40, 48)
            self.button_rects["cancel_ai"] = btn_rect
            self._draw_button(btn_rect, "CANCEL", COLOR_HIGHLIGHT, is_pulse=True)
        else:
            btn_rect = pygame.Rect(x, btn_y, SIDEBAR_WIDTH - 40, 48)
            self.button_rects["run_ai"] = btn_rect
            self._draw_button(btn_rect, "RUN AI", COLOR_PRIMARY)

    def _draw_board(self, game_session: GameSession, is_ai_playing: bool, dt: int) -> None:
        level, state = game_session.level, game_session.state
        self._update_animations(state.player, state.boxes, dt)
        
        board_rect = pygame.Rect(
            self.board_ox, 
            self.board_oy, 
            level.width * self.tile_size, 
            level.height * self.tile_size
        )
        pygame.draw.rect(self.screen, RETRO_FLOOR, board_rect)
        
        for r in range(level.height):
            for c in range(level.width):
                rect = pygame.Rect(self.board_ox + c * self.tile_size, self.board_oy + r * self.tile_size, self.tile_size, self.tile_size)
                
                if (r, c) in level.walls:
                    self._draw_asset("wall", rect, COLOR_BORDER)
                elif (r, c) in level.goals:
                    gap_offset = max(2, int(self.tile_size * 0.15))
                    self._draw_asset("goal", rect, COLOR_GOAL_FALLBACK, True, scale_offset=gap_offset)
                    
        for i, visual_box in enumerate(self.anim_boxes):
            vr, vc = visual_box[0], visual_box[1]
            
            is_on_goal = False
            for gr, gc in level.goals:
                if abs(vr - gr) < 0.1 and abs(vc - gc) < 0.1:
                    is_on_goal = True
                    break
                    
            rect = pygame.Rect(
                int(self.board_ox + vc * self.tile_size), 
                int(self.board_oy + vr * self.tile_size), 
                self.tile_size, 
                self.tile_size
            )
            
            asset_key = "box_on_goal" if is_on_goal else "box"
            fallback_col = COLOR_BOX_ON_GOAL_FALLBACK if is_on_goal else COLOR_BOX_FALLBACK
            self._draw_asset(asset_key, rect, fallback_col)
            
        self._draw_player_logic(state.player, is_ai_playing)

    def _draw_player_logic(self, target_pos: Tuple[int, int], is_ai_playing: bool) -> None:
        is_visually_moving = False
        bob_offset = 0
        if self.anim_player_pos:
            dist = abs(self.anim_player_pos[0] - target_pos[0]) + abs(self.anim_player_pos[1] - target_pos[1])
            is_visually_moving = dist > 0.05

        if is_ai_playing or is_visually_moving:
            ticks = pygame.time.get_ticks()
            bob_offset = -4 if (ticks // 150) % 2 == 0 else 0

        if self.anim_player_pos:
            vr, vc = self.anim_player_pos
        else:
            vr, vc = float(target_pos[0]), float(target_pos[1])

        rect = pygame.Rect(
            int(self.board_ox + vc * self.tile_size), 
            int(self.board_oy + vr * self.tile_size + bob_offset), 
            self.tile_size, 
            self.tile_size
        )
        
        sprite = self._get_player_sprite()
        
        if sprite:
            self.screen.blit(sprite, rect.topleft)
        else:
            pygame.draw.rect(self.screen, COLOR_PLAYER_FALLBACK, rect.inflate(-8, -8))
            pygame.draw.rect(self.screen, COLOR_TEXT, rect.inflate(-16, -16))

    def _draw_dashboard(self, game_session: GameSession, result: Optional[SolveResult], level_index: int, total_levels: int, is_ai_playing: bool, is_solving: bool) -> None:
        x0 = self.window_width - DASHBOARD_WIDTH
        rect = pygame.Rect(x0, HEADER_HEIGHT - 3, DASHBOARD_WIDTH, self.window_height - HEADER_HEIGHT + 3)
        self._draw_panel(rect)
        x, y = x0 + 20, HEADER_HEIGHT + 20
        self.screen.blit(self.font_bold.render("METRICS", True, COLOR_PRIMARY), (x, y))
        y += 40
        y = self._draw_metric(x, y, "CURRENT STEPS", str(game_session.steps_count), COLOR_SECONDARY, draw_line=True)
        y = self._draw_metric(x, y, "LEVEL SEED", f"{level_index + 1:02d}/{total_levels:02d}", COLOR_TEXT, draw_line=True)
        
        y += 10
        self.screen.blit(self.font_bold.render("TELEMETRY", True, COLOR_PRIMARY), (x, y))
        y += 30
        
        if result is None:
            if is_solving:
                self.screen.blit(self.font_small.render("COMPUTING...", True, COLOR_SECONDARY), (x, y))
            else:
                self.screen.blit(self.font_small.render("AWAITING...", True, COLOR_TEXT_DIM), (x, y))
        else:
            time_str = f"{result.elapsed_ms:.1f} ms" if result.elapsed_ms < 1000 else f"{result.elapsed_ms/1000:.2f} s"
            display_algo = result.algorithm.split('(')[0].replace('_', ' ').strip()
            rows = [
                ("ALGORITHM:", display_algo),
                ("SOLVED:", "YES" if result.found else "NO"),
                ("PATH:", str(result.steps)),
                ("NODES:", f"{result.expanded:,}"),
                ("TIME:", time_str),
            ]
            
            for label, val in rows:
                self.screen.blit(self.font_tiny.render(label, True, COLOR_TEXT_DIM), (x, y + 2))
                surf = self.font_small.render(val, True, COLOR_SECONDARY if result.found else COLOR_HIGHLIGHT)
                self.screen.blit(surf, (x0 + DASHBOARD_WIDTH - 20 - surf.get_width(), y))
                y += 32

        btn_w = DASHBOARD_WIDTH - 40
        btn_x = x0 + 20
        half_btn_w = (btn_w - 10) // 2
        
        quit_y = self.window_height - 70
        map_y = quit_y - 56
        undo_y = map_y - 56
        restart_y = undo_y - 56
        
        ctrl_y = restart_y - 40
        self.screen.blit(self.font_bold.render("CONTROLS", True, COLOR_PRIMARY), (btn_x, ctrl_y))
        pygame.draw.line(self.screen, COLOR_BORDER, (btn_x, ctrl_y + 20), (x0 + DASHBOARD_WIDTH - 20, ctrl_y + 20), 2)
        
        dim_color = (60, 60, 70)  
        pause_color = dim_color if self.is_paused else COLOR_BORDER
        continue_color = COLOR_TERTIARY if self.is_paused else dim_color

        pause_disabled = not is_ai_playing or self.is_paused
        continue_disabled = not is_ai_playing or not self.is_paused
        
        buttons: List[Tuple[str, str, Tuple[int, int, int], int, int, int, bool]] = [
            ("restart", "RESTART", COLOR_BORDER, btn_x, restart_y, btn_w, False),
            ("pause", "PAUSE", COLOR_BORDER, btn_x, undo_y, half_btn_w, pause_disabled),
            ("continue", "CONTINUE", COLOR_TERTIARY, btn_x + half_btn_w + 10, undo_y, half_btn_w, continue_disabled),
            ("select_map", "MAPS", COLOR_BORDER, btn_x, map_y, half_btn_w, False),
            ("random_map", "RANDOM", COLOR_TERTIARY, btn_x + half_btn_w + 10, map_y, half_btn_w, False),
            ("quit_game", "QUIT", COLOR_HIGHLIGHT, btn_x, quit_y, btn_w, False)
        ]
        
        for key, label, color, bx, by, bw, is_disabled in buttons:
            btn_rect = pygame.Rect(bx, by, bw, 42)
            
            if not is_disabled:
                self.button_rects[key] = btn_rect
                
            self._draw_button(btn_rect, label, color, is_disabled=is_disabled)

    def _draw_map_popup(self, level_names: List[str], current_index: int) -> None:
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) 
        self.screen.blit(overlay, (0, 0))

        w, h = 380, 460
        
        center_area_w = self.window_width - SIDEBAR_WIDTH - DASHBOARD_WIDTH
        center_area_h = self.window_height - HEADER_HEIGHT
        
        popup_x = SIDEBAR_WIDTH + (center_area_w - w) // 2
        popup_y = HEADER_HEIGHT + (center_area_h - h) // 2
        
        rect = pygame.Rect(popup_x, popup_y, w, h)
        self.popup_rect = rect 
        self._draw_panel(rect, COLOR_BG)
        
        self.screen.blit(self.font_large.render("SELECT MAP", True, COLOR_PRIMARY), (rect.x + 20, rect.y + 20))
        
        list_y = rect.y + 60
        list_h = h - 130 
        list_rect = pygame.Rect(rect.x + 20, list_y, rect.width - 40, list_h)
        
        cols = 4
        item_size = 70  
        gap_x = (list_rect.width - 10 - (cols * item_size)) // max(1, cols - 1)
        gap_y = 20
        
        total_rows = math.ceil(len(level_names) / cols)
        total_content_h = total_rows * (item_size + gap_y)
        
        self.max_scroll_y = max(0, total_content_h - list_h)
        self.map_scroll_y = max(0, min(self.map_scroll_y, self.max_scroll_y))
        
        self.screen.set_clip(list_rect)
        
        self.map_rects.clear()
        for i, name in enumerate(level_names):
            r = i // cols
            c = i % cols
            
            item_x = list_rect.x + c * (item_size + gap_x)
            item_y = list_y - self.map_scroll_y + r * (item_size + gap_y)
            
            row_rect = pygame.Rect(item_x, item_y, item_size, item_size)
            
            if row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                self.map_rects[i] = row_rect
                is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
                
                if i == self.temp_selected_map_index:
                    pygame.draw.rect(self.screen, COLOR_PRIMARY_DIM, row_rect, border_radius=8)
                    pygame.draw.rect(self.screen, COLOR_PRIMARY, row_rect, 2, border_radius=8)
                    text_col = COLOR_BG
                elif is_hovered:
                    pygame.draw.rect(self.screen, (60, 60, 70), row_rect, border_radius=8)
                    pygame.draw.rect(self.screen, COLOR_BORDER, row_rect, 2, border_radius=8)
                    text_col = COLOR_TEXT
                else:
                    pygame.draw.rect(self.screen, COLOR_PANEL, row_rect, border_radius=8)
                    pygame.draw.rect(self.screen, COLOR_BORDER, row_rect, 2, border_radius=8)
                    text_col = COLOR_TEXT_DIM
                    
                text_surf = self.font_large.render(str(i + 1), True, text_col)
                self.screen.blit(text_surf, (row_rect.centerx - text_surf.get_width() // 2, row_rect.centery - text_surf.get_height() // 2))
                
        self.screen.set_clip(None)
        
        if self.max_scroll_y > 0:
            bar_w = 8
            bar_x = rect.right - 18
            
            self.scrollbar_track_rect = pygame.Rect(bar_x, list_y, bar_w, list_h)
            pygame.draw.rect(self.screen, (30, 30, 40), self.scrollbar_track_rect, border_radius=4)
            
            thumb_h = max(30, int((list_h / total_content_h) * list_h))
            thumb_y = list_y + (self.map_scroll_y / self.max_scroll_y) * (list_h - thumb_h)
            pygame.draw.rect(self.screen, COLOR_TEXT_DIM, (bar_x, int(thumb_y), bar_w, thumb_h), border_radius=4)
        else:
            self.scrollbar_track_rect = None

        btn_w = 140
        btn_y = rect.bottom - 55
        cancel_rect = pygame.Rect(rect.centerx - btn_w - 10, btn_y, btn_w, 42)
        confirm_rect = pygame.Rect(rect.centerx + 10, btn_y, btn_w, 42)
        
        self.button_rects["cancel_map"] = cancel_rect
        self.button_rects["confirm_map"] = confirm_rect
        
        self._draw_button(cancel_rect, "CANCEL", COLOR_BORDER)
        self._draw_button(confirm_rect, "CONFIRM", COLOR_SECONDARY)

    def _draw_metric(self, x: int, y: int, label: str, value: str, color: Tuple[int, int, int], draw_line: bool = True) -> int:
        self.screen.blit(self.font_tiny.render(label, True, COLOR_TEXT_DIM), (x, y))
        surf = self.font_metric.render(value, True, color)
        
        self.screen.blit(surf, (x + DASHBOARD_WIDTH - 40 - surf.get_width(), y + 22))
        
        if draw_line:
            pygame.draw.line(self.screen, COLOR_BORDER, (x, y + 44), (x + DASHBOARD_WIDTH - 40, y + 44), 2)
            return y + 54
        
        return y + 44

    def _draw_button(self, rect: pygame.Rect, label: str, base_color: Tuple[int, int, int], is_pulse: bool = False, is_disabled: bool = False) -> None:
        is_hovered = rect.collidepoint(pygame.mouse.get_pos()) if not is_disabled else False
        
        if is_disabled:
            bg_col = (40, 40, 45)
            border_col = (60, 60, 70)
            text_color = (100, 100, 110)
            draw_rect = rect 
        else:
            if is_pulse and (pygame.time.get_ticks() // 300) % 2 == 0:
                bg_col = COLOR_SECONDARY  
            else:
                bg_col = self._lighten_color(base_color, 40) if is_hovered else base_color

            draw_rect = rect.move(0, -2) if is_hovered else rect
            border_col = COLOR_TEXT
            text_color = COLOR_BG if sum(bg_col) > 400 else COLOR_TEXT

        pygame.draw.rect(self.screen, (0, 0, 0), rect.move(2, 2))
        pygame.draw.rect(self.screen, bg_col, draw_rect)
        pygame.draw.rect(self.screen, border_col if not is_disabled else (70, 70, 80), draw_rect, 2)
        
        surf = self.font_bold.render(label, True, text_color)
        self.screen.blit(surf, (draw_rect.centerx - surf.get_width() // 2, draw_rect.centery - surf.get_height() // 2))

    def _draw_asset(self, key: str, rect: pygame.Rect, fallback_color: Tuple[int, int, int], is_circle: bool = False, scale_offset: int = 0) -> None:
        size = max(1, self.tile_size - scale_offset)
        image = self._get_scaled_asset(key, size)
        
        if image: 
            img_rect = image.get_rect(center=rect.center)
            self.screen.blit(image, img_rect.topleft)
        elif is_circle: 
            pygame.draw.circle(self.screen, fallback_color, rect.center, max(1, size // 3))
        else: 
            draw_rect = pygame.Rect(0, 0, size, size)
            draw_rect.center = rect.center
            pygame.draw.rect(self.screen, fallback_color, draw_rect)