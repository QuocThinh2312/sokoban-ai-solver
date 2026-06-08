"""Bộ vẽ Pygame cho game Sokoban."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from .xu_ly_giai import SolveResult
from .hang_so import (
    ALGORITHMS,
    BUTTON_BAR_HEIGHT,
    COLOR_BG,
    COLOR_BG_DEEP,
    COLOR_BORDER,
    COLOR_BOX_GLOW,
    COLOR_BOX_ON_GOAL,
    COLOR_FLOOR,
    COLOR_FLOOR_GRID,
    COLOR_PANEL,
    COLOR_PANEL_HIGH,
    COLOR_PLAYER_CORE,
    COLOR_PLAYER_RING,
    COLOR_PRIMARY,
    COLOR_PRIMARY_DIM,
    COLOR_SECONDARY,
    COLOR_TERTIARY,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TEXT_FAINT,
    DASHBOARD_WIDTH,
    HEADER_HEIGHT,
    SIDEBAR_WIDTH,
    TILE_SIZE,
)
from .tro_choi import GameSession

THU_MUC_ASSET = Path(__file__).resolve().parent.parent / "assets"


class GiaoDien:
    def __init__(self, so_o_ngang_lon_nhat: int, so_o_doc_lon_nhat: int):
        pygame.init()
        pygame.display.set_caption("Sokoban - Trình giải thuật toán")

        self.kich_thuoc_o = TILE_SIZE
        self.rong_ban_co = so_o_ngang_lon_nhat * self.kich_thuoc_o
        self.cao_ban_co = so_o_doc_lon_nhat * self.kich_thuoc_o
        self.rong_cua_so = SIDEBAR_WIDTH + self.rong_ban_co + 80 + DASHBOARD_WIDTH
        self.cao_cua_so = HEADER_HEIGHT + max(self.cao_ban_co + BUTTON_BAR_HEIGHT + 80, 560)
        self.man_hinh = pygame.display.set_mode((self.rong_cua_so, self.cao_cua_so))

        self.font = pygame.font.SysFont("segoe ui", 16)
        self.font_nho = pygame.font.SysFont("segoe ui", 13)
        self.font_rat_nho = pygame.font.SysFont("segoe ui", 11)
        self.font_dam = pygame.font.SysFont("segoe ui", 12, bold=True)
        self.font_lon = pygame.font.SysFont("segoe ui", 22, bold=True)
        self.font_thong_so = pygame.font.SysFont("segoe ui", 20, bold=True)

        self.asset = self._tai_asset()
        self._cache_asset = {}
        self.hien_danh_sach_map = False
        self.vung_thuat_toan: Dict[str, pygame.Rect] = {}
        self.vung_nut: Dict[str, pygame.Rect] = {}
        self.vung_map: Dict[int, pygame.Rect] = {}

    def _dang_hover(self, rect: pygame.Rect) -> bool:
        return rect.collidepoint(pygame.mouse.get_pos())

    def _co_the_click(self) -> bool:
        vi_tri = pygame.mouse.get_pos()
        cac_vung = list(self.vung_thuat_toan.values()) + list(self.vung_nut.values())
        if self.hien_danh_sach_map:
            cac_vung += list(self.vung_map.values())
        return any(rect.collidepoint(vi_tri) for rect in cac_vung)

    def _cap_nhat_con_tro(self) -> None:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self._co_the_click() else pygame.SYSTEM_CURSOR_ARROW)

    def _mau_sang_hon(self, mau: Tuple[int, int, int], muc: int = 22) -> Tuple[int, int, int]:
        return tuple(min(255, x + muc) for x in mau)

    def _tai_asset(self) -> Dict[str, Optional[pygame.Surface]]:
        ket_qua: Dict[str, Optional[pygame.Surface]] = {}
        for ten, file in {"tuong": "wall.png", "thung": "crate.png", "dich": "target.png"}.items():
            try:
                ket_qua[ten] = pygame.image.load(str(THU_MUC_ASSET / file)).convert_alpha()
            except (pygame.error, FileNotFoundError):
                ket_qua[ten] = None
        return ket_qua

    def _asset_co_gian(self, ten: str, kich_thuoc: int) -> Optional[pygame.Surface]:
        anh = self.asset.get(ten)
        if anh is None:
            return None
        khoa = (ten, kich_thuoc)
        if khoa not in self._cache_asset:
            self._cache_asset[khoa] = pygame.transform.smoothscale(anh, (kich_thuoc, kich_thuoc))
        return self._cache_asset[khoa]

    def xu_ly_click(self, vi_tri: Tuple[int, int]) -> Tuple[str, object] | None:
        for ten, rect in self.vung_thuat_toan.items():
            if rect.collidepoint(vi_tri):
                return ("chon_thuat_toan", ten)
        for ten, rect in self.vung_nut.items():
            if rect.collidepoint(vi_tri):
                if ten == "chon_map":
                    self.hien_danh_sach_map = not self.hien_danh_sach_map
                return (ten, None)
        if self.hien_danh_sach_map:
            for chi_so, rect in self.vung_map.items():
                if rect.collidepoint(vi_tri):
                    self.hien_danh_sach_map = False
                    return ("chon_map_item", chi_so)
        return None

    def ve(
        self,
        phien_choi: GameSession,
        thuat_toan: str,
        ket_qua: Optional[SolveResult],
        chi_so_map: int,
        tong_so_map: int,
        ten_cac_map: List[str],
        trang_thai: str,
        dang_giai: bool,
        hien_chuc_mung: bool = False,
        ket_qua_theo_thuat_toan: Optional[Dict[str, SolveResult]] = None,
    ) -> None:
        self.vung_thuat_toan.clear()
        self.vung_nut.clear()
        self.vung_map.clear()

        self._ve_nen()
        self._ve_dau_trang()
        self._ve_thanh_trai(thuat_toan, ket_qua_theo_thuat_toan or {}, dang_giai)
        self._ve_ban_co(phien_choi)
        self._ve_cac_nut()
        self._ve_bang_phai(phien_choi, ket_qua, chi_so_map, tong_so_map)
        if self.hien_danh_sach_map:
            self._ve_popup_map(ten_cac_map, chi_so_map)
        if hien_chuc_mung:
            self._ve_popup_thang(chi_so_map, tong_so_map)
        self._cap_nhat_con_tro()
        pygame.display.flip()

    def _ve_nen(self) -> None:
        self.man_hinh.fill(COLOR_BG)
        for y in range(0, self.cao_cua_so, 4):
            t = y / max(1, self.cao_cua_so)
            r = int(250 * (1 - t) + 234 * t)
            g = int(248 * (1 - t) + 237 * t)
            b = int(255 * (1 - t) + 255 * t)
            pygame.draw.rect(self.man_hinh, (r, g, b), (0, y, self.rong_cua_so, 4))

    def _khung(self, rect: pygame.Rect, mau=COLOR_PANEL, vien=COLOR_BORDER) -> None:
        shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
        shadow.fill((0, 74, 198, 14))
        self.man_hinh.blit(shadow, (rect.x + 3, rect.y + 4))
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        surf.fill((mau[0], mau[1], mau[2], 245))
        self.man_hinh.blit(surf, rect.topleft)
        pygame.draw.rect(self.man_hinh, vien, rect, 1, border_radius=8)

    def _ve_dau_trang(self) -> None:
        rect = pygame.Rect(0, 0, self.rong_cua_so, HEADER_HEIGHT)
        self._khung(rect, COLOR_PANEL)
        title = "Sokoban"
        surf = self.font_lon.render(title, True, COLOR_PRIMARY)
        self.man_hinh.blit(surf, (self.rong_cua_so // 2 - surf.get_width() // 2, 16))

    def _ve_thanh_trai(self, thuat_toan: str, ket_qua_theo_thuat_toan: Dict[str, SolveResult], dang_giai: bool) -> None:
        rect = pygame.Rect(0, HEADER_HEIGHT, SIDEBAR_WIDTH, self.cao_cua_so - HEADER_HEIGHT)
        self._khung(rect, COLOR_PANEL)
        x, y = 20, HEADER_HEIGHT + 20
        self._chu(self.font_dam, "Thuật toán", x, y, COLOR_PRIMARY)
        y += 18
        self._chu(self.font_rat_nho, "Bấm chuột để chọn", x, y, COLOR_TEXT_FAINT)
        y += 30
        for ten in ALGORITHMS:
            active = ten == thuat_toan
            row = pygame.Rect(x, y, SIDEBAR_WIDTH - 40, 40)
            self.vung_thuat_toan[ten] = row
            hover = self._dang_hover(row)
            if active:
                shadow = pygame.Surface(row.size, pygame.SRCALPHA)
                pygame.draw.rect(shadow, (19, 27, 46, 28), shadow.get_rect(), border_radius=8)
                self.man_hinh.blit(shadow, (row.x + 2, row.y + 3))
                bg = pygame.Surface(row.size, pygame.SRCALPHA)
                pygame.draw.rect(bg, (28, 96, 220, 245), bg.get_rect(), border_radius=8)
                self.man_hinh.blit(bg, row.topleft)
                light = pygame.Surface((row.width, row.height // 2), pygame.SRCALPHA)
                pygame.draw.rect(light, (255, 255, 255, 40), light.get_rect(), border_radius=8)
                self.man_hinh.blit(light, row.topleft)
                pygame.draw.rect(self.man_hinh, self._mau_sang_hon(COLOR_PRIMARY, 42), row, 2, border_radius=8)
            elif hover:
                bg = pygame.Surface(row.size, pygame.SRCALPHA)
                bg.fill((226, 231, 255, 210))
                self.man_hinh.blit(bg, row.topleft)
                pygame.draw.rect(self.man_hinh, COLOR_PRIMARY_DIM, row, 1, border_radius=6)
            mau = (255, 255, 255) if active else COLOR_TEXT
            self._chu(self.font, ten, x + 12, y + 11, mau)
            buoc = "-"
            ket_qua = ket_qua_theo_thuat_toan.get(ten)
            if ket_qua is not None and ket_qua.found:
                buoc = str(ket_qua.steps)
            nhan = f"Bước: {buoc}"
            surf = self.font_rat_nho.render(nhan, True, mau)
            self.man_hinh.blit(surf, (x + row.width - surf.get_width() - 10, y + 14))
            y += 48
        btn = pygame.Rect(x, rect.bottom - 60, SIDEBAR_WIDTH - 40, 44)
        self.vung_nut["chay_ai"] = btn
        self._nut(btn, "Đang tính..." if dang_giai else "Chạy AI [phím cách]", COLOR_PRIMARY)

    def _goc_ban_co(self) -> Tuple[int, int]:
        vung_x = SIDEBAR_WIDTH
        vung_w = self.rong_cua_so - SIDEBAR_WIDTH - DASHBOARD_WIDTH
        vung_y = HEADER_HEIGHT
        vung_h = self.cao_cua_so - HEADER_HEIGHT - BUTTON_BAR_HEIGHT
        return vung_x + (vung_w - self.rong_ban_co) // 2, vung_y + (vung_h - self.cao_ban_co) // 2

    def _ve_ban_co(self, phien_choi: GameSession) -> None:
        man = phien_choi.level
        trang_thai = phien_choi.state
        ox, oy = self._goc_ban_co()
        self._khung(pygame.Rect(ox - 20, oy - 20, self.rong_ban_co + 40, self.cao_ban_co + 40), COLOR_PANEL, COLOR_PRIMARY_DIM)
        lx = ox + (self.rong_ban_co - man.width * self.kich_thuoc_o) // 2
        ly = oy + (self.cao_ban_co - man.height * self.kich_thuoc_o) // 2
        for r in range(man.height):
            for c in range(man.width):
                pos = (r, c)
                rect = pygame.Rect(lx + c * self.kich_thuoc_o, ly + r * self.kich_thuoc_o, self.kich_thuoc_o, self.kich_thuoc_o)
                if pos in man.walls:
                    self._ve_asset("tuong", rect, COLOR_PANEL_HIGH)
                else:
                    inner = rect.inflate(-2, -2)
                    pygame.draw.rect(self.man_hinh, COLOR_FLOOR, inner, border_radius=4)
                    pygame.draw.rect(self.man_hinh, COLOR_FLOOR_GRID, inner, 1, border_radius=4)
                if pos in man.goals:
                    self._ve_asset("dich", rect.inflate(-16, -16), COLOR_SECONDARY, la_tron=True)
        for thung in trang_thai.boxes:
            r, c = thung
            rect = pygame.Rect(lx + c * self.kich_thuoc_o, ly + r * self.kich_thuoc_o, self.kich_thuoc_o, self.kich_thuoc_o).inflate(-8, -8)
            self._phat_sang(rect, COLOR_BOX_ON_GOAL if thung in man.goals else COLOR_BOX_GLOW)
            self._ve_asset("thung", rect, COLOR_BOX_GLOW)
        self._ve_nguoi_choi(trang_thai.player, lx, ly)

    def _ve_cac_nut(self) -> None:
        ox, oy = self._goc_ban_co()
        y = oy + self.cao_ban_co + 26
        labels = [("choi_lai", "Chơi lại"), ("quay_lai", "Bước trước"), ("chon_map", "Chọn màn")]
        tong_w = 3 * 140 + 2 * 16
        x = ox + (self.rong_ban_co - tong_w) // 2
        for key, label in labels:
            rect = pygame.Rect(x, y, 140, 42)
            self.vung_nut[key] = rect
            self._nut(rect, label, COLOR_PRIMARY)
            x += 156

    def _ve_bang_phai(self, phien_choi: GameSession, ket_qua: Optional[SolveResult], chi_so_map: int, tong_so_map: int) -> None:
        x0 = self.rong_cua_so - DASHBOARD_WIDTH
        rect = pygame.Rect(x0, HEADER_HEIGHT, DASHBOARD_WIDTH, self.cao_cua_so - HEADER_HEIGHT)
        self._khung(rect, COLOR_PANEL)
        x, y = x0 + 20, HEADER_HEIGHT + 20
        self._chu(self.font_dam, "Thông số", x, y, COLOR_PRIMARY)
        y += 28
        y = self._thong_so(x, y, "Số bước", str(phien_choi.so_nuoc_di), COLOR_SECONDARY)
        y = self._thong_so(x, y, "Trạng thái", "Hoàn thành" if phien_choi.da_thang() else "Đang chơi", COLOR_TERTIARY if phien_choi.da_thang() else COLOR_TEXT)
        y = self._thong_so(x, y, "Màn", f"{chi_so_map + 1:02d}/{tong_so_map:02d}", COLOR_PRIMARY)
        so_thung_dung = sum(1 for b in phien_choi.state.boxes if b in phien_choi.level.goals)
        y = self._thong_so(x, y, "Thùng đúng", f"{so_thung_dung}/{len(phien_choi.level.goals)}", COLOR_TERTIARY)
        y += 10
        pygame.draw.line(self.man_hinh, COLOR_BORDER, (x, y), (x0 + DASHBOARD_WIDTH - 20, y))
        y += 16
        self._chu(self.font_dam, "Kết quả AI", x, y, COLOR_PRIMARY)
        y += 24
        if ket_qua is None:
            self._chu(self.font_nho, "Chưa chạy thuật toán.", x, y, COLOR_TEXT)
            return
        rows = [("Thuật toán", ket_qua.algorithm), ("Tìm thấy", "Có" if ket_qua.found else "Không"), ("Số bước", str(ket_qua.steps)), ("Đã mở rộng", str(ket_qua.expanded)), ("Thời gian", f"{ket_qua.elapsed_ms:.1f} ms"), ("Bộ nhớ", f"{ket_qua.memory_kb:.1f} KB")]
        for label, val in rows:
            self._chu(self.font_rat_nho, label, x, y, COLOR_TEXT)
            surf = self.font_nho.render(val, True, COLOR_TEXT)
            self.man_hinh.blit(surf, (x0 + DASHBOARD_WIDTH - 20 - surf.get_width(), y - 1))
            y += 20

    def _ve_popup_map(self, ten_cac_map: List[str], chi_so_map: int) -> None:
        ox, oy = self._goc_ban_co()
        w = min(360, self.rong_ban_co - 40)
        h = 44 + len(ten_cac_map) * 34
        rect = pygame.Rect(ox + (self.rong_ban_co - w) // 2, oy + 30, w, h)
        self._khung(rect, COLOR_PANEL, COLOR_PRIMARY)
        self._chu(self.font_dam, "Chọn màn", rect.x + 16, rect.y + 14, COLOR_PRIMARY)
        y = rect.y + 44
        for i, ten in enumerate(ten_cac_map):
            row = pygame.Rect(rect.x + 12, y, rect.width - 24, 28)
            self.vung_map[i] = row
            hover = self._dang_hover(row)
            if i == chi_so_map or hover:
                bg = pygame.Surface(row.size, pygame.SRCALPHA)
                bg.fill((180, 197, 255, 210 if hover else 180))
                self.man_hinh.blit(bg, row.topleft)
            pygame.draw.rect(self.man_hinh, COLOR_PRIMARY_DIM if hover else COLOR_BORDER, row, 1, border_radius=4)
            self._chu(self.font_nho, f"{i + 1}. {ten}", row.x + 8, row.y + 7, COLOR_TEXT)
            y += 34

    def _ve_popup_thang(self, chi_so_map: int, tong_so_map: int) -> None:
        overlay = pygame.Surface((self.rong_cua_so, self.cao_cua_so), pygame.SRCALPHA)
        overlay.fill((19, 27, 46, 95))
        self.man_hinh.blit(overlay, (0, 0))

        w, h = 420, 210
        rect = pygame.Rect((self.rong_cua_so - w) // 2, (self.cao_cua_so - h) // 2, w, h)
        self._khung(rect, COLOR_PANEL, COLOR_PRIMARY_DIM)

        title = "Chúc mừng!"
        surf = self.font_lon.render(title, True, COLOR_PRIMARY)
        self.man_hinh.blit(surf, (rect.centerx - surf.get_width() // 2, rect.y + 34))

        msg = "Bạn đã hoàn thành màn chơi."
        msg_surf = self.font.render(msg, True, COLOR_TEXT_DIM)
        self.man_hinh.blit(msg_surf, (rect.centerx - msg_surf.get_width() // 2, rect.y + 78))

        y = rect.y + 132
        close_rect = pygame.Rect(rect.x + 44, y, 150, 44)
        next_rect = pygame.Rect(rect.right - 194, y, 150, 44)
        self.vung_nut["dong_thang"] = close_rect
        self.vung_nut["man_tiep"] = next_rect
        self._nut(close_rect, "Đóng", COLOR_PANEL_HIGH)
        label = "Màn tiếp theo" if chi_so_map + 1 < tong_so_map else "Về màn đầu"
        self._nut(next_rect, label, COLOR_PRIMARY)

    def _thong_so(self, x: int, y: int, label: str, value: str, mau) -> int:
        self._chu(self.font_rat_nho, label, x, y, COLOR_TEXT)
        surf = self.font_thong_so.render(value, True, mau)
        self.man_hinh.blit(surf, (x + DASHBOARD_WIDTH - 40 - surf.get_width(), y - 4))
        y += 22
        pygame.draw.rect(self.man_hinh, COLOR_FLOOR_GRID, (x, y, DASHBOARD_WIDTH - 40, 3))
        return y + 16

    def _nut(self, rect: pygame.Rect, label: str, mau) -> None:
        hover = self._dang_hover(rect)
        mau_nen = self._mau_sang_hon(mau, 28) if hover else mau
        ve_rect = rect.move(0, -1 if hover else 0)

        shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (19, 27, 46, 32 if hover else 20), shadow.get_rect(), border_radius=8)
        self.man_hinh.blit(shadow, (rect.x + 2, rect.y + (4 if hover else 3)))

        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (mau_nen[0], mau_nen[1], mau_nen[2], 245), bg.get_rect(), border_radius=8)
        self.man_hinh.blit(bg, ve_rect.topleft)

        highlight = pygame.Surface((ve_rect.width, max(1, ve_rect.height // 2)), pygame.SRCALPHA)
        pygame.draw.rect(highlight, (255, 255, 255, 42 if hover else 26), highlight.get_rect(), border_radius=8)
        self.man_hinh.blit(highlight, ve_rect.topleft)

        pygame.draw.rect(self.man_hinh, self._mau_sang_hon(mau, 45) if hover else mau, ve_rect, 2 if hover else 1, border_radius=8)
        chu_mau = (255, 255, 255) if sum(mau_nen) < 560 else COLOR_TEXT
        surf = self.font_dam.render(label, True, chu_mau)
        self.man_hinh.blit(surf, (ve_rect.centerx - surf.get_width() // 2, ve_rect.centery - surf.get_height() // 2))

    def _phat_sang(self, rect: pygame.Rect, mau) -> None:
        glow_rect = rect.inflate(10, 10)
        glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(glow, (mau[0], mau[1], mau[2], 60), glow.get_rect(), border_radius=8)
        self.man_hinh.blit(glow, glow_rect.topleft)

    def _ve_asset(self, ten: str, rect: pygame.Rect, mau_fallback, la_tron: bool = False) -> None:
        anh = self._asset_co_gian(ten, rect.width)
        if anh is not None:
            self.man_hinh.blit(anh, rect.topleft)
        elif la_tron:
            pygame.draw.circle(self.man_hinh, mau_fallback, rect.center, rect.width // 3)
        else:
            pygame.draw.rect(self.man_hinh, mau_fallback, rect, border_radius=4)

    def _ve_nguoi_choi(self, nguoi_choi, lx: int, ly: int) -> None:
        r, c = nguoi_choi
        tam = (lx + c * self.kich_thuoc_o + self.kich_thuoc_o // 2, ly + r * self.kich_thuoc_o + self.kich_thuoc_o // 2)
        ban_kinh = self.kich_thuoc_o // 2 - 8
        glow = pygame.Surface((self.kich_thuoc_o, self.kich_thuoc_o), pygame.SRCALPHA)
        pygame.draw.circle(glow, (0, 74, 198, 70), (self.kich_thuoc_o // 2, self.kich_thuoc_o // 2), ban_kinh + 5)
        self.man_hinh.blit(glow, (tam[0] - self.kich_thuoc_o // 2, tam[1] - self.kich_thuoc_o // 2))
        pygame.draw.circle(self.man_hinh, COLOR_PLAYER_CORE, tam, ban_kinh)
        pygame.draw.circle(self.man_hinh, COLOR_PLAYER_RING, tam, ban_kinh, 3)
        for dx in (-ban_kinh // 3, ban_kinh // 3):
            pygame.draw.circle(self.man_hinh, COLOR_BG_DEEP, (tam[0] + dx, tam[1] - ban_kinh // 6), 3)

    def _chu(self, font, text: str, x: int, y: int, mau=COLOR_TEXT) -> None:
        self.man_hinh.blit(font.render(text, True, mau), (x, y))
