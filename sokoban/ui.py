from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any

import pygame

from .solver_utils import SolveResult
from .constants import (
    ALGORITHMS, BUTTON_BAR_HEIGHT, COLOR_BG, COLOR_BG_DEEP, COLOR_BORDER,
    COLOR_BOX_GLOW, COLOR_BOX_ON_GOAL, COLOR_FLOOR, COLOR_FLOOR_GRID,
    COLOR_PANEL, COLOR_PANEL_HIGH, COLOR_PLAYER_CORE, COLOR_PLAYER_RING,
    COLOR_PRIMARY, COLOR_PRIMARY_DIM, COLOR_SECONDARY, COLOR_TERTIARY,
    COLOR_HIGHLIGHT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_TEXT_FAINT, DASHBOARD_WIDTH,
    HEADER_HEIGHT, SIDEBAR_WIDTH, TILE_SIZE,
)
from .game import GameSession

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

class GameUI:
    def __init__(self, max_grid_width: int, max_grid_height: int) -> None:
        pygame.init()
        pygame.display.set_caption("Sokoban AI - Solver")

        self.tile_size: int = TILE_SIZE
        self.board_width: int = max_grid_width * self.tile_size
        self.board_height: int = max_grid_height * self.tile_size
        self.window_width: int = SIDEBAR_WIDTH + self.board_width + 80 + DASHBOARD_WIDTH
        self.window_height: int = HEADER_HEIGHT + max(self.board_height + BUTTON_BAR_HEIGHT + 80, 560)
        self.screen: pygame.Surface = pygame.display.set_mode((self.window_width, self.window_height))

        self.font: pygame.font.Font = pygame.font.SysFont("segoe ui", 16)
        self.font_small: pygame.font.Font = pygame.font.SysFont("segoe ui", 13)
        self.font_tiny: pygame.font.Font = pygame.font.SysFont("segoe ui", 11)
        self.font_bold: pygame.font.Font = pygame.font.SysFont("segoe ui", 12, bold=True)
        self.font_large: pygame.font.Font = pygame.font.SysFont("segoe ui", 22, bold=True)
        self.font_metric: pygame.font.Font = pygame.font.SysFont("segoe ui", 20, bold=True)

        self._asset_cache: Dict[Tuple[str, int], pygame.Surface] = {}
        self.assets: Dict[str, Optional[pygame.Surface]] = self._load_assets()
        
        self._ui_cache: Dict[Tuple[Any, ...], pygame.Surface] = {}
        
        self.show_map_list: bool = False
        self.algo_rects: Dict[str, pygame.Rect] = {}
        self.button_rects: Dict[str, pygame.Rect] = {}
        self.map_rects: Dict[int, pygame.Rect] = {}

    def _is_hovered(self, rect: pygame.Rect) -> bool:
        return rect.collidepoint(pygame.mouse.get_pos())

    def _is_clickable(self) -> bool:
        mouse_pos = pygame.mouse.get_pos()
        all_rects = list(self.algo_rects.values()) + list(self.button_rects.values())
        if self.show_map_list:
            all_rects += list(self.map_rects.values())
        return any(rect.collidepoint(mouse_pos) for rect in all_rects)

    def _update_cursor(self) -> None:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self._is_clickable() else pygame.SYSTEM_CURSOR_ARROW)

    def _lighten_color(self, color: Tuple[int, int, int], amount: int = 22) -> Tuple[int, int, int]:
        return (min(255, color[0] + amount), min(255, color[1] + amount), min(255, color[2] + amount))

    def _load_assets(self) -> Dict[str, Optional[pygame.Surface]]:
        result: Dict[str, Optional[pygame.Surface]] = {}
        for key, filename in {"wall": "wall.png", "box": "crate.png", "goal": "target.png"}.items():
            try:
                result[key] = pygame.image.load(str(ASSETS_DIR / filename)).convert_alpha()
            except (pygame.error, FileNotFoundError):
                result[key] = None
        return result

    def _get_scaled_asset(self, key: str, size: int) -> Optional[pygame.Surface]:
        image = self.assets.get(key)
        if image is None: 
            return None
        cache_key = (key, size)
        if cache_key not in self._asset_cache:
            self._asset_cache[cache_key] = pygame.transform.smoothscale(image, (size, size))
        return self._asset_cache[cache_key]
        
    def _get_cached_ui(self, cache_key: Tuple[Any, ...], size: Tuple[int, int], draw_func: Callable[[pygame.Surface], Any]) -> pygame.Surface:
        if cache_key not in self._ui_cache:
            surf = pygame.Surface(size, pygame.SRCALPHA)
            draw_func(surf)
            self._ui_cache[cache_key] = surf
        return self._ui_cache[cache_key]

    def handle_click(self, pos: Tuple[int, int]) -> Optional[Tuple[str, Any]]:
        for key, rect in self.algo_rects.items():
            if rect.collidepoint(pos): 
                return ("select_algo", key)
        for key, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                if key == "select_map": 
                    self.show_map_list = not self.show_map_list
                return (key, None)
        if self.show_map_list:
            for index, rect in self.map_rects.items():
                if rect.collidepoint(pos):
                    self.show_map_list = False
                    return ("select_map_item", index)
        return None

    def draw(self, game_session: GameSession, current_algo: str, current_result: Optional[SolveResult], 
           level_index: int, total_levels: int, level_names: List[str], status_text: str, 
           is_solving: bool, show_win_popup: bool, 
           results_by_algo: Optional[Dict[str, SolveResult]] = None) -> None:
           
        if results_by_algo is None:
            results_by_algo = {}
            
        self.algo_rects.clear()
        self.button_rects.clear()
        self.map_rects.clear()

        self._draw_background()
        self._draw_header(status_text)
        self._draw_sidebar(current_algo, results_by_algo, is_solving)
        self._draw_board(game_session)
        self._draw_buttons()
        self._draw_dashboard(game_session, current_result, level_index, total_levels)
        
        if self.show_map_list: 
            self._draw_map_popup(level_names, level_index)
        if show_win_popup: 
            self._draw_win_popup(level_index, total_levels)
        
        self._update_cursor()
        pygame.display.flip()

    def _draw_background(self) -> None:
        self.screen.fill(COLOR_BG)

    def _draw_panel(self, rect: pygame.Rect, color: Tuple[int, int, int] = COLOR_PANEL, border_color: Tuple[int, int, int] = COLOR_BORDER) -> None:
        shadow_key = ("panel_shadow", rect.size)
        shadow = self._get_cached_ui(shadow_key, rect.size, lambda s: s.fill((0, 74, 198, 14)))
        self.screen.blit(shadow, (rect.x + 3, rect.y + 4))

        bg_key = ("panel_bg", rect.size, color)
        bg = self._get_cached_ui(bg_key, rect.size, lambda s: s.fill((color[0], color[1], color[2], 245)))
        self.screen.blit(bg, rect.topleft)

        pygame.draw.rect(self.screen, border_color, rect, 1, border_radius=8)

    def _draw_header(self, status_text: str) -> None:
        rect = pygame.Rect(0, 0, self.window_width, HEADER_HEIGHT)
        self._draw_panel(rect, COLOR_PANEL)
        title = "Sokoban AI Master"
        surf = self.font_large.render(title, True, COLOR_PRIMARY)
        self.screen.blit(surf, (20, 16))
        
        status_surf = self.font.render(status_text, True, COLOR_TEXT_DIM)
        self.screen.blit(status_surf, (self.window_width // 2 - status_surf.get_width() // 2, 18))

    def _draw_sidebar(self, current_algo: str, results_by_algo: Dict[str, SolveResult], is_solving: bool) -> None:
        rect = pygame.Rect(0, HEADER_HEIGHT, SIDEBAR_WIDTH, self.window_height - HEADER_HEIGHT)
        self._draw_panel(rect, COLOR_PANEL)
        x, y = 20, HEADER_HEIGHT + 20
        self._draw_text(self.font_bold, "Algorithm", x, y, COLOR_PRIMARY)
        y += 30
        
        for algo_name in ALGORITHMS:
            is_active = (algo_name == current_algo)
            row_rect = pygame.Rect(x, y, SIDEBAR_WIDTH - 40, 40)
            self.algo_rects[algo_name] = row_rect
            is_hovered = self._is_hovered(row_rect)
            
            if is_active:
                pygame.draw.rect(self.screen, (28, 96, 220), row_rect, border_radius=8)
                pygame.draw.rect(self.screen, self._lighten_color(COLOR_PRIMARY, 42), row_rect, 2, border_radius=8)
            elif is_hovered:
                pygame.draw.rect(self.screen, (226, 231, 255), row_rect, border_radius=8)
                pygame.draw.rect(self.screen, COLOR_PRIMARY_DIM, row_rect, 1, border_radius=8)
                
            text_color: Tuple[int, int, int] = (255, 255, 255) if is_active else COLOR_TEXT
            self._draw_text(self.font, algo_name, x + 12, y + 11, text_color)
            
            result = results_by_algo.get(algo_name)
            steps_text = str(result.steps) if (result and result.found) else "-"
            surf = self.font_tiny.render(f"Steps: {steps_text}", True, text_color)
            self.screen.blit(surf, (x + row_rect.width - surf.get_width() - 10, y + 14))
            y += 48
            
        btn_rect = pygame.Rect(x, rect.bottom - 60, SIDEBAR_WIDTH - 40, 44)
        self.button_rects["run_ai"] = btn_rect
        self._draw_button(btn_rect, "Processing..." if is_solving else "Run AI [Space]", COLOR_SECONDARY if is_solving else COLOR_PRIMARY)

    def _get_board_origin(self) -> Tuple[int, int]:
        avail_w = self.window_width - SIDEBAR_WIDTH - DASHBOARD_WIDTH
        avail_h = self.window_height - HEADER_HEIGHT - BUTTON_BAR_HEIGHT
        return SIDEBAR_WIDTH + (avail_w - self.board_width) // 2, HEADER_HEIGHT + (avail_h - self.board_height) // 2

    def _draw_board(self, game_session: GameSession) -> None:
        level, state = game_session.level, game_session.state
        ox, oy = self._get_board_origin()
        self._draw_panel(pygame.Rect(ox - 20, oy - 20, self.board_width + 40, self.board_height + 40), COLOR_PANEL, COLOR_PRIMARY_DIM)
        
        lx = ox + (self.board_width - level.width * self.tile_size) // 2
        ly = oy + (self.board_height - level.height * self.tile_size) // 2
        
        for r in range(level.height):
            for c in range(level.width):
                pos = (r, c)
                rect = pygame.Rect(lx + c * self.tile_size, ly + r * self.tile_size, self.tile_size, self.tile_size)
                if pos in level.walls:
                    self._draw_asset("wall", rect, COLOR_PANEL_HIGH)
                else:
                    inner = rect.inflate(-2, -2)
                    pygame.draw.rect(self.screen, COLOR_FLOOR, inner, border_radius=4)
                    pygame.draw.rect(self.screen, COLOR_FLOOR_GRID, inner, 1, border_radius=4)
                if pos in level.goals:
                    self._draw_asset("goal", rect.inflate(-16, -16), COLOR_SECONDARY, is_circle=True)
                    
        for box in state.boxes:
            rect = pygame.Rect(lx + box[1] * self.tile_size, ly + box[0] * self.tile_size, self.tile_size, self.tile_size).inflate(-8, -8)
            self._draw_glow(rect, COLOR_BOX_ON_GOAL if box in level.goals else COLOR_BOX_GLOW)
            self._draw_asset("box", rect, COLOR_BOX_GLOW)
            
        self._draw_player(state.player, lx, ly)

    def _draw_buttons(self) -> None:
        ox, oy = self._get_board_origin()
        y = oy + self.board_height + 26
        labels = [("restart", "Restart"), ("undo", "Undo"), ("select_map", "Select Level")]
        x = ox + (self.board_width - (3 * 140 + 32)) // 2
        for key, label in labels:
            rect = pygame.Rect(x, y, 140, 42)
            self.button_rects[key] = rect
            self._draw_button(rect, label, COLOR_PRIMARY)
            x += 156

    def _draw_dashboard(self, game_session: GameSession, result: Optional[SolveResult], level_index: int, total_levels: int) -> None:
        x0 = self.window_width - DASHBOARD_WIDTH
        rect = pygame.Rect(x0, HEADER_HEIGHT, DASHBOARD_WIDTH, self.window_height - HEADER_HEIGHT)
        self._draw_panel(rect, COLOR_PANEL)
        x, y = x0 + 20, HEADER_HEIGHT + 20
        self._draw_text(self.font_bold, "Metrics", x, y, COLOR_PRIMARY)
        y += 28
        y = self._draw_metric(x, y, "Steps", str(game_session.steps_count), COLOR_SECONDARY)
        y = self._draw_metric(x, y, "Level", f"{level_index + 1:02d}/{total_levels:02d}", COLOR_PRIMARY)
        
        y += 10
        pygame.draw.line(self.screen, COLOR_BORDER, (x, y), (x0 + DASHBOARD_WIDTH - 20, y))
        y += 16
        self._draw_text(self.font_bold, "AI Results (Memory Optimized)", x, y, COLOR_PRIMARY)
        y += 24
        
        if result is None:
            self._draw_text(self.font_small, "No computation data.", x, y, COLOR_TEXT)
            return
            
        time_str = f"{result.elapsed_ms:.1f} ms" if result.elapsed_ms < 1000 else f"{result.elapsed_ms/1000:.2f} s"
        rows = [
            ("Algorithm", result.algorithm),
            ("Solution Found", "Yes" if result.found else "No"),
            ("Path Length", str(result.steps)),
            ("Nodes Expanded", f"{result.expanded:,}"),
            ("Execution Time", time_str),
            ("RAM Allocated", f"{result.memory_kb:.1f} KB")
        ]
        
        for label, val in rows:
            self._draw_text(self.font_tiny, label, x, y, COLOR_TEXT)
            surf = self.font_small.render(val, True, COLOR_TEXT)
            self.screen.blit(surf, (x0 + DASHBOARD_WIDTH - 20 - surf.get_width(), y - 1))
            y += 20

    def _draw_map_popup(self, level_names: List[str], current_index: int) -> None:
        ox, oy = self._get_board_origin()
        w = min(360, self.board_width - 40)
        h = 44 + len(level_names) * 34
        rect = pygame.Rect(ox + (self.board_width - w) // 2, oy + 30, w, h)
        self._draw_panel(rect, COLOR_PANEL, COLOR_PRIMARY)
        self._draw_text(self.font_bold, "Select Level", rect.x + 16, rect.y + 14, COLOR_PRIMARY)
        y = rect.y + 44
        for i, name in enumerate(level_names):
            row_rect = pygame.Rect(rect.x + 12, y, rect.width - 24, 28)
            self.map_rects[i] = row_rect
            is_hovered = self._is_hovered(row_rect)
            if i == current_index or is_hovered:
                pygame.draw.rect(self.screen, (180, 197, 255), row_rect, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_PRIMARY_DIM if is_hovered else COLOR_BORDER, row_rect, 1, border_radius=4)
            self._draw_text(self.font_small, f"{i + 1}. {name}", row_rect.x + 8, row_rect.y + 7, COLOR_TEXT)
            y += 34

    def _draw_win_popup(self, level_index: int, total_levels: int) -> None:
        overlay = self._get_cached_ui(("overlay",), (self.window_width, self.window_height), lambda s: s.fill((19, 27, 46, 95)))
        self.screen.blit(overlay, (0, 0))

        w, h = 420, 210
        rect = pygame.Rect((self.window_width - w) // 2, (self.window_height - h) // 2, w, h)
        self._draw_panel(rect, COLOR_PANEL, COLOR_HIGHLIGHT)

        surf = self.font_large.render("Victory!", True, COLOR_TERTIARY)
        self.screen.blit(surf, (rect.centerx - surf.get_width() // 2, rect.y + 34))

        close_rect = pygame.Rect(rect.x + 44, rect.y + 132, 150, 44)
        next_rect = pygame.Rect(rect.right - 194, rect.y + 132, 150, 44)
        self.button_rects["close_win"] = close_rect
        self.button_rects["next_level"] = next_rect
        self._draw_button(close_rect, "Close", COLOR_PANEL_HIGH)
        self._draw_button(next_rect, "Next Level" if level_index + 1 < total_levels else "Back to First Level", COLOR_PRIMARY)

    def _draw_metric(self, x: int, y: int, label: str, value: str, color: Tuple[int, int, int]) -> int:
        self._draw_text(self.font_tiny, label, x, y, COLOR_TEXT)
        surf = self.font_metric.render(value, True, color)
        self.screen.blit(surf, (x + DASHBOARD_WIDTH - 40 - surf.get_width(), y - 4))
        pygame.draw.rect(self.screen, COLOR_FLOOR_GRID, (x, y + 22, DASHBOARD_WIDTH - 40, 3))
        return y + 38

    def _draw_button(self, rect: pygame.Rect, label: str, base_color: Tuple[int, int, int]) -> None:
        is_hovered = self._is_hovered(rect)
        bg_color = self._lighten_color(base_color, 28) if is_hovered else base_color
        draw_rect = rect.move(0, -1 if is_hovered else 0)

        cache_key = ("button", rect.size, base_color, is_hovered)
        btn_surf = self._get_cached_ui(cache_key, rect.size, lambda s: (
            pygame.draw.rect(s, (bg_color[0], bg_color[1], bg_color[2], 255), s.get_rect(), border_radius=8),
            pygame.draw.rect(s, self._lighten_color(base_color, 45) if is_hovered else base_color, s.get_rect(), 2 if is_hovered else 1, border_radius=8)
        ))
        self.screen.blit(btn_surf, draw_rect.topleft)
        
        text_color: Tuple[int, int, int] = (255, 255, 255) if sum(bg_color) < 560 else COLOR_TEXT
        surf = self.font_bold.render(label, True, text_color)
        self.screen.blit(surf, (draw_rect.centerx - surf.get_width() // 2, draw_rect.centery - surf.get_height() // 2))

    def _draw_glow(self, rect: pygame.Rect, color: Tuple[int, int, int]) -> None:
        glow_rect = rect.inflate(10, 10)
        cache_key = ("glow", glow_rect.size, color)
        glow = self._get_cached_ui(cache_key, glow_rect.size, lambda s: pygame.draw.rect(s, (color[0], color[1], color[2], 60), s.get_rect(), border_radius=8))
        self.screen.blit(glow, glow_rect.topleft)

    def _draw_asset(self, key: str, rect: pygame.Rect, fallback_color: Tuple[int, int, int], is_circle: bool = False) -> None:
        image = self._get_scaled_asset(key, rect.width)
        if image: 
            self.screen.blit(image, rect.topleft)
        elif is_circle: 
            pygame.draw.circle(self.screen, fallback_color, rect.center, rect.width // 3)
        else: 
            pygame.draw.rect(self.screen, fallback_color, rect, border_radius=4)

    def _draw_player(self, player_pos: Tuple[int, int], lx: int, ly: int) -> None:
        center = (lx + player_pos[1] * self.tile_size + self.tile_size // 2, ly + player_pos[0] * self.tile_size + self.tile_size // 2)
        radius = self.tile_size // 2 - 8
        pygame.draw.circle(self.screen, COLOR_PLAYER_CORE, center, radius)
        pygame.draw.circle(self.screen, COLOR_PLAYER_RING, center, radius, 3)

    def _draw_text(self, font: pygame.font.Font, text: str, x: int, y: int, color: Tuple[int, int, int] = COLOR_TEXT) -> None:
        self.screen.blit(font.render(text, True, color), (x, y))