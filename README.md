# 🤖 Sokoban AI Solver

Một hệ thống tự động giải game Sokoban được viết bằng Python. Dự án áp dụng các kỹ thuật tìm kiếm không gian trạng thái từ cơ bản đến nâng cao để tự động tìm ra chuỗi hành động tối ưu đẩy toàn bộ hộp vào đích.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)

## ✨ Các thuật toán AI được tích hợp

Hệ thống hỗ trợ 7 thuật toán tìm kiếm đa dạng, cho phép theo dõi và so sánh hiệu suất theo thời gian thực:

1. **BFS**: Đảm bảo tìm được đường đi ngắn nhất.
2. **DFS**: Tìm kiếm theo chiều sâu, tiết kiệm bộ nhớ.
3. **UCS**: Tối ưu theo chi phí di chuyển.
4. **Greedy Search**: Tốc độ cực nhanh, kết hợp đa tầng Tie-breaking và Jitter để tránh Local Optimum.
5. **A\***: Thuật toán tối ưu cân bằng giữa Heuristic `h(n)` và chi phí `g(n)`.
6. **Weighted A\***: Nhân trọng số cho Heuristic để tăng tốc độ tìm kiếm tại các map lớn.
7. **Beam Search**: Mở rộng linh hoạt với giới hạn bộ nhớ, tự động nhận diện bế tắc.

## 🚀 Kỹ thuật tối ưu & cải tiến

- **State-aware Heuristic (Bitmask DP)**: Đánh giá khoảng cách chính xác bằng quy hoạch động với bitmask.
- **Geometric Deadlock Detection & Caching**: Nhận diện bế tắc hình học và lưu vết để cắt sớm các nhánh vô vọng.
- **Precomputed Distances** Chạy BFS ngược từ đích để tính sẵn chi phí đường đi với thời gian tra cứu O(1).
- **Zobrist Hashing & Macro-moves:** Mã hóa trạng thái bằng Zobrist Hash 64-bit và gom nhóm di chuyển tự do thành thao tác đẩy để giảm hệ số phân nhánh.
- **Map Hash Caching**: Cơ chế cache tiền xử lý map dựa trên kiến trúc địa hình để tránh Cache Collision.
- **Hungarian Algorithm:** Tính toán ánh xạ UI giúp hoạt ảnh mượt mà.

## 🛠 Cài đặt & khởi chạy

### 1. Yêu cầu hệ thống

- **Python 3.10** trở lên.

### 2. Cài đặt thư viện

Mở terminal tại thư mục gốc và chạy:

```bash
pip install -r requirements.txt
```

### 3. Khởi chạy

```bash
python run.py
```

## 🎮 Điều khiển & tương tác UI

- **Nút RUN AI (Space)**: Khởi chạy thuật toán AI để giải màn chơi hiện tại.
- **Nút RESTART (R)**: Chơi lại từ đầu màn hiện tại.
- **Nút MAPS (M)**: Mở cửa sổ popup chọn level với thanh cuộn tương tác.
- **Nút PAUSE/CONTINUE (P/C)**: Tạm dừng hoặc tiếp tục quá trình di chuyển của bot AI.
- **Nút UNDO (U)**: Quay lại bước di chuyển trước đó của bot AI.
- **Nút RANDOM**: Chọn ngẫu nhiên một màn chơi trong hệ thống.
- **Nút QUIT (Esc/Q)**: Thoát game.
- **Phím W/A/S/D hoặc các phím mũi tên**: Người chơi tự di chuyển nhân vật theo các hướng.

## 🗺️ Tự tạo màn chơi

Hệ thống cung cấp sẵn hàng trăm map trong folder `maps/`. Bạn hoàn toàn có thể tự tạo màn chơi riêng bằng cách tạo file .txt mới trong folder này với các ký hiệu sau:

| Ký hiệu | Ý nghĩa                   |
| ------- | ------------------------- |
| `#`     | Tường                     |
| `@`     | Người chơi                |
| `+`     | Người chơi đứng trên đích |
| `$`     | Thùng                     |
| `*`     | Thùng đặt trên đích       |
| `.`     | Vị trí đích               |
| (Space) | Ô trống                   |

_Lưu ý: Map hợp lệ phải có tường bao quanh và số lượng thùng phải bằng số lượng đích._

## Cấu trúc thư mục

```text

sokoban-ai-solver/
├── assets/                 # Các file hình ảnh và âm thanh
├── docs/                   # Tài liệu báo cáo
├── maps/                   # Kho dữ liệu các file .txt chứa màn chơi
├── sokoban/
│   ├── __init__.py
│   ├── algorithms.py       # Cài đặt logic 7 thuật toán tìm kiếm AI
│   ├── constants.py        # Định nghĩa các hằng số toàn cục (FPS, màu sắc, phím)
│   ├── game.py             # Xử lý logic game và quản lý phiên chơi
│   ├── level.py            # Đọc, phân tích và mã hóa map từ file .txt
│   ├── main.py             # Quản lý game loop, xử lý sự kiện và điều phối đa luồng cho AI
│   ├── solver_utils.py     # Các kỹ thuật tối ưu (Heuristic, Deadlock Detection, Macro-moves)
│   ├── state.py            # Định nghĩa Data Class cho State
│   └── ui.py               # Render giao diện, animation, layout
├── .gitignore
├── README.md               # Tài liệu dự án
├── requirements.txt        # Danh sách thư viện phụ thuộc
└── run.py                  # Entry point khởi chạy

```

## Chỉ số Telemetry

Sau khi AI giải quyết một màn chơi, bảng dashboard sẽ hiển thị chi tiết các thông số đo lường hiệu năng:

- **ALGORITHM**: Thuật toán được sử dụng.
- **SOLVED**: Trạng thái hoàn thành (YES / NO).
- **PATH**: Số bước đi thực tế để giải map.
- **NODES**: Số lượng trạng thái đã mở rộng trong bộ nhớ.
- **TIME**: Thời gian chạy thuật toán (ms hoặc s)
