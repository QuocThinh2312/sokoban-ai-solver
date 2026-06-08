"""Điểm chạy chính: game Sokoban với chơi tay và 5 thuật toán tìm kiếm."""

from pathlib import Path
from typing import List, Optional

import pygame

from sokoban.ve_giao_dien import GiaoDien
from sokoban.xu_ly_giai import SolveResult
from sokoban.hang_so import DANH_SACH_THUAT_TOAN, FPS
from sokoban.man_choi import Level, tai_man_tu_thu_muc
from sokoban.thuat_toan import giai
from sokoban.tro_choi import GameSession

PHIM_THANH_BUOC = {
    pygame.K_UP: "U",
    pygame.K_w: "U",
    pygame.K_DOWN: "D",
    pygame.K_s: "D",
    pygame.K_LEFT: "L",
    pygame.K_a: "L",
    pygame.K_RIGHT: "R",
    pygame.K_d: "R",
}

PHIM_THANH_THUAT_TOAN = {
    pygame.K_1: "BFS",
    pygame.K_2: "DFS",
    pygame.K_3: "UCS",
    pygame.K_4: "Greedy",
    pygame.K_5: "A*",
}


def tai_cac_map() -> List[Level]:
    thu_muc_hien_tai = Path(__file__).parent
    thu_muc_map = thu_muc_hien_tai / "maps"
    if not thu_muc_map.is_dir():
        raise SystemExit(f"Không tìm thấy thư mục màn chơi: {thu_muc_map}")
    cac_map = tai_man_tu_thu_muc(thu_muc_map)
    if not cac_map:
        raise SystemExit("Không có tệp màn chơi nào trong thư mục maps/.")
    return cac_map


def chuyen_map(cac_map: List[Level], chi_so_map: int) -> GameSession:
    return GameSession(cac_map[chi_so_map])

def tao_trang_thai_chay_ai(thuat_toan: str, phien_choi: GameSession) -> tuple[SolveResult, List[str], str]:
    phien_choi.choi_lai()
    ket_qua = giai(thuat_toan, phien_choi.level)
    if ket_qua.found:
        return ket_qua, list(ket_qua.actions), f"{thuat_toan} tìm được lời giải {len(ket_qua.actions)} bước."
    return ket_qua, [], ket_qua.message or f"{thuat_toan} không tìm được lời giải."


def main() -> None:
    cac_map = tai_cac_map()
    ten_cac_map = [m.name for m in cac_map]
    rong_lon_nhat = max(m.width for m in cac_map)
    cao_lon_nhat = max(m.height for m in cac_map)

    giao_dien = GiaoDien(rong_lon_nhat, cao_lon_nhat)
    dong_ho = pygame.time.Clock()

    chi_so_map = 0
    phien_choi = chuyen_map(cac_map, chi_so_map)
    thuat_toan = DANH_SACH_THUAT_TOAN[0]
    ket_qua: Optional[SolveResult] = None
    ket_qua_theo_thuat_toan: dict[str, SolveResult] = {}
    trang_thai = "Chọn thuật toán rồi bấm phím cách hoặc nút Chạy AI."
    hien_chuc_mung = False

    cac_buoc_ai: List[str] = []
    bo_dem_phat = 0
    toc_do_phat_ms = 120

    dang_chay = True
    while dang_chay:
        dt = dong_ho.tick(FPS)

        for su_kien in pygame.event.get():
            if su_kien.type == pygame.QUIT:
                dang_chay = False
                break

            if su_kien.type == pygame.MOUSEBUTTONDOWN and su_kien.button == 1:
                hanh_dong = giao_dien.xu_ly_click(su_kien.pos)
                if hanh_dong is None:
                    continue
                loai, gia_tri = hanh_dong

                if loai == "chon_thuat_toan":
                    thuat_toan = str(gia_tri)
                    ket_qua = ket_qua_theo_thuat_toan.get(thuat_toan)
                    trang_thai = f"Đã chọn thuật toán {thuat_toan}."
                    continue

                if loai == "chay_ai":
                    if cac_buoc_ai:
                        trang_thai = "AI đang phát lời giải, vui lòng đợi."
                        continue
                    ket_qua = None
                    trang_thai = f"Đang giải bằng {thuat_toan}..."
                    giao_dien.ve(phien_choi, thuat_toan, None, chi_so_map, len(cac_map), ten_cac_map, trang_thai, True, hien_chuc_mung, ket_qua_theo_thuat_toan=ket_qua_theo_thuat_toan)
                    ket_qua, cac_buoc_ai, trang_thai = tao_trang_thai_chay_ai(thuat_toan, phien_choi)
                    ket_qua_theo_thuat_toan[thuat_toan] = ket_qua
                    bo_dem_phat = 0
                    continue

                if loai == "choi_lai":
                    phien_choi.choi_lai()
                    cac_buoc_ai = []
                    ket_qua = None
                    hien_chuc_mung = False
                    trang_thai = "Đã chơi lại màn hiện tại."
                    continue

                if loai == "quay_lai":
                    if phien_choi.quay_lai():
                        hien_chuc_mung = False
                        trang_thai = "Đã quay về bước trước."
                    else:
                        trang_thai = "Không có bước trước để quay lại."
                    continue

                if loai == "dong_thang":
                    hien_chuc_mung = False
                    continue

                if loai == "man_tiep":
                    chi_so_map = (chi_so_map + 1) % len(cac_map)
                    phien_choi = chuyen_map(cac_map, chi_so_map)
                    cac_buoc_ai = []
                    ket_qua = None
                    ket_qua_theo_thuat_toan.clear()
                    hien_chuc_mung = False
                    trang_thai = f"Màn: {phien_choi.level.name}"
                    continue

                if loai == "chon_map_item":
                    chi_so_map = int(gia_tri)
                    phien_choi = chuyen_map(cac_map, chi_so_map)
                    cac_buoc_ai = []
                    ket_qua = None
                    ket_qua_theo_thuat_toan.clear()
                    hien_chuc_mung = False
                    trang_thai = f"Đã chọn màn: {phien_choi.level.name}."
                    continue

            if su_kien.type != pygame.KEYDOWN:
                continue

            phim = su_kien.key
            if phim == pygame.K_ESCAPE:
                dang_chay = False
                break

            if phim in PHIM_THANH_THUAT_TOAN:
                thuat_toan = PHIM_THANH_THUAT_TOAN[phim]
                ket_qua = ket_qua_theo_thuat_toan.get(thuat_toan)
                trang_thai = f"Đã chọn thuật toán {thuat_toan}."
                continue

            if phim == pygame.K_SPACE:
                if cac_buoc_ai:
                    trang_thai = "AI đang phát lời giải, vui lòng đợi."
                    continue
                ket_qua = None
                trang_thai = f"Đang giải bằng {thuat_toan}..."
                giao_dien.ve(phien_choi, thuat_toan, None, chi_so_map, len(cac_map), ten_cac_map, trang_thai, True, hien_chuc_mung, ket_qua_theo_thuat_toan=ket_qua_theo_thuat_toan)
                ket_qua, cac_buoc_ai, trang_thai = tao_trang_thai_chay_ai(thuat_toan, phien_choi)
                ket_qua_theo_thuat_toan[thuat_toan] = ket_qua
                bo_dem_phat = 0
                continue

            if phim == pygame.K_r:
                phien_choi.choi_lai()
                cac_buoc_ai = []
                ket_qua = None
                hien_chuc_mung = False
                trang_thai = "Đã chơi lại màn hiện tại."
                continue

            if phim == pygame.K_u:
                if phien_choi.quay_lai():
                    hien_chuc_mung = False
                    trang_thai = "Đã quay về bước trước."
                else:
                    trang_thai = "Không có bước trước để quay lại."
                continue

            if phim == pygame.K_n:
                chi_so_map = (chi_so_map + 1) % len(cac_map)
                phien_choi = chuyen_map(cac_map, chi_so_map)
                cac_buoc_ai = []
                ket_qua = None
                ket_qua_theo_thuat_toan.clear()
                hien_chuc_mung = False
                trang_thai = f"Màn: {phien_choi.level.name}"
                continue

            if phim == pygame.K_p:
                chi_so_map = (chi_so_map - 1) % len(cac_map)
                phien_choi = chuyen_map(cac_map, chi_so_map)
                cac_buoc_ai = []
                ket_qua = None
                ket_qua_theo_thuat_toan.clear()
                hien_chuc_mung = False
                trang_thai = f"Màn: {phien_choi.level.name}"
                continue

            if phim in PHIM_THANH_BUOC and not cac_buoc_ai:
                if phien_choi.di_chuyen(PHIM_THANH_BUOC[phim]):
                    if phien_choi.da_thang():
                        hien_chuc_mung = True
                        trang_thai = "Bạn đã hoàn thành màn chơi!"
                else:
                    trang_thai = "Không thể đi hướng đó."

        if cac_buoc_ai:
            bo_dem_phat += dt
            if bo_dem_phat >= toc_do_phat_ms:
                bo_dem_phat = 0
                buoc = cac_buoc_ai.pop(0)
                phien_choi.di_chuyen(buoc)
                if not cac_buoc_ai and phien_choi.da_thang():
                    hien_chuc_mung = True
                    trang_thai = "AI đã đẩy hết thùng vào đích!"

        giao_dien.ve(phien_choi, thuat_toan, ket_qua, chi_so_map, len(cac_map), ten_cac_map, trang_thai, False, hien_chuc_mung, ket_qua_theo_thuat_toan=ket_qua_theo_thuat_toan)

    pygame.quit()


if __name__ == "__main__":
    main()
