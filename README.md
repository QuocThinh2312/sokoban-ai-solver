# Sokoban AI - Đồ án Trí tuệ Nhân tạo

Game Sokoban viết bằng Python + Pygame, kết hợp 5 thuật toán tìm kiếm để giải tự động.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy game

```bash
python main.py
```

## Phím điều khiển

- **Mũi tên / WASD**: di chuyển nhân vật
- **U**: quay lại bước vừa đi
- **R**: chơi lại màn hiện tại
- **N / P**: chuyển màn kế tiếp / trước
- **1-5**: chọn thuật toán BFS, DFS, UCS, Greedy, A*
- **Phím cách**: AI giải màn hiện tại bằng thuật toán đã chọn
- **Esc**: thoát

## Ký hiệu trong tệp màn chơi

| Ký hiệu      | Ý nghĩa                |
|--------------|------------------------|
| `#`          | Tường                  |
| `@`          | Người chơi             |
| `+`          | Người chơi đứng trên đích |
| `$`          | Thùng                  |
| `*`          | Thùng đặt trên đích    |
| `.`          | Vị trí đích            |
| khoảng trắng | Ô trống                |

## 4 màn chơi kịch bản

| Tệp                           | Mô tả                                                |
|-------------------------------|------------------------------------------------------|
| `maps/level1_small.txt`       | Bản đồ nhỏ, 1 thùng - kiểm tra luật cơ bản          |
| `maps/level2_medium.txt`      | Bản đồ trung bình, 2 thùng - đánh giá hiệu năng     |
| `maps/level3_deadlock.txt`    | Có vị trí dễ kẹt góc - kiểm tra loại sớm            |
| `maps/level4_multiple_paths.txt` | Nhiều đường đi - so sánh độ tối ưu giữa các thuật toán |

## Thuật toán

5 thuật toán cài đặt trong `sokoban/thuat_toan.py`:

1. **BFS** (tìm kiếm theo chiều rộng) — tối ưu khi chi phí mỗi bước bằng nhau.
2. **DFS** (tìm kiếm theo chiều sâu) — tiết kiệm bộ nhớ, không tối ưu, có giới hạn độ sâu.
3. **UCS** (tìm kiếm theo chi phí đều) — tối ưu theo chi phí đường đi.
4. **Greedy** (tìm kiếm tham lam) — nhanh, dùng heuristic, không tối ưu.
5. **A*** — kết hợp `g(n) + h(n)`, tối ưu nếu heuristic chấp nhận được.

Heuristic dùng tổng khoảng cách Manhattan ngắn nhất từ mỗi thùng tới một đích.

## Kỹ thuật tối ưu

- **Tập đã thăm**: lưu khóa trạng thái `(player, sorted(boxes))` để tránh duyệt lại.
- **Phát hiện kẹt góc**: phát hiện thùng kẹt ở góc tường (không phải đích) và loại sớm.
- **Chuẩn hóa trạng thái**: sắp xếp tập thùng để các trạng thái tương đương có cùng khóa.

## Cấu trúc thư mục

```text
.
├── main.py
├── README.md
├── maps/
│   ├── level1_small.txt
│   ├── level2_medium.txt
│   ├── level3_deadlock.txt
│   └── level4_multiple_paths.txt
└── sokoban/
    ├── __init__.py
    ├── hang_so.py      # ký hiệu màn chơi, màu sắc, hằng số
    ├── man_choi.py     # đọc màn chơi -> Level
    ├── trang_thai.py   # State (người chơi, thùng), kiểm tra đích
    ├── tro_choi.py     # luật di chuyển/đẩy thùng, phiên chơi
    ├── xu_ly_giai.py   # trạng thái kề, heuristic, kẹt góc, SolveResult
    ├── thuat_toan.py   # 5 thuật toán + hàm gọi chung
    └── ve_giao_dien.py # vẽ bàn chơi và bảng thông tin bằng Pygame
```

## Đầu ra của bộ giải

Mỗi lần chạy thuật toán, bảng bên phải hiển thị:

- Tên thuật toán
- Có tìm được lời giải không
- Số bước trong lời giải
- Số trạng thái mở rộng
- Thời gian thực thi (ms)
- Bộ nhớ ước lượng (KB) cho tập đã thăm
