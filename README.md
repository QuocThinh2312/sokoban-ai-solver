# Sokoban AI Solver

Một hệ thống tự động giải game Sokoban được viết bằng Python và Pygame. Dự án áp dụng các kỹ thuật tìm kiếm không gian trạng thái từ cơ bản đến nâng cao để tự động tìm ra chuỗi hành động tối ưu đẩy toàn bộ hộp vào đích.

## Cài đặt

Cài đặt các thư viện phụ thuộc (Pygame, Numpy, Scipy,...)

## Chạy chương trình

Mở terminal tại thư mục gốc của dự án và gõ lệnh:

```bash
python run.py
```

## Điều khiển & tương tác UI

- **Nút RUN AI (Backspace)**: Khởi chạy thuật toán AI để giải màn chơi hiện tại.
- **Nút RESTART (R)**: Chơi lại từ đầu màn hiện tại.
- **Nút MAPS (M)**: Mở cửa sổ popup chọn level với thanh cuộn tương tác.
- **Nút PAUSE/CONTINUE (P/C)**: Tạm dừng hoặc tiếp tục quá trình di chuyển của bot AI.
- **Nút UNDO (U)**: Quay lại bước di chuyển trước đó của bot AI.
- **Nút RANDOM**: Chọn ngẫu nhiên một màn chơi trong hệ thống.
- **Nút QUIT (Esc/Q)**: Thoát game.

## Ký hiệu trong tệp màn chơi

| Ký hiệu      | Ý nghĩa                   |
| ------------ | ------------------------- |
| `#`          | Tường                     |
| `@`          | Người chơi                |
| `+`          | Người chơi đứng trên đích |
| `$`          | Thùng                     |
| `*`          | Thùng đặt trên đích       |
| `.`          | Vị trí đích               |
| khoảng trắng | Ô trống                   |

## Kho dữ liệu màn chơi

Hệ thống hiện tại tích hợp một kho dữ liệu khổng lồ với hàng trăm màn chơi nằm trong thư mục maps/. Các map đa dạng độ khó từ cơ bản đến cực khó (đòi hỏi xử lý deadlock hình học phức tạp).

## Các thuật toán AI được tích hợp

Danh sách các thuật toán tìm kiếm được cài đặt trong `sokoban/algorithms.py`:

1. **BFS**: Đảm bảo đường đi ngắn nhất nhưng tốn nhiều RAM.
2. **DFS**: Tiết kiệm bộ nhớ nhưng không tối ưu số bước.
3. **UCS**: Tối ưu theo chi phí.
4. **Greedy Search**: Tốc độ cực nhanh, kết hợp đa tầng Tie-breaking và Jitter để tránh Local Optimum.
5. **A\***: Kết hợp g(n) + h(n), cân bằng giữa tối ưu và hiệu suất.
6. **Weighted A\***: Nhân trọng số cho Heuristic để tăng tốc độ tìm kiếm tại các map cực lớn.
7. **Adaptive Beam Search**: Beam Search mở rộng linh hoạt, tự động nhận diện bế tắc để điều hướng không gian tìm kiếm.

## Kỹ thuật tối ưu & cải tiến

- **State-aware Heuristic (Bitmask DP)**: Tối ưu hóa việc gán Hộp -> Đích bằng Bitmask DP. Heuristic không chỉ đo khoảng cách Manhattan mà còn cộng điểm phạt khi hộp nằm ở góc/tường hẹp và thưởng khi người chơi đứng gần hộp.
- **Geometric Deadlock Detection**: Hệ thống nhận diện bế tắc hình học chính xác (Static deadlock, Freeze deadlock, Tunnel deadlock, bẫy 2x2 tường/hộp) để cắt tỉa các nhánh vô vọng từ sớm mà không làm mất lời giải tối ưu.
- **Zobrist Hashing & State Representation**: Mô hình hóa trạng thái siêu nhẹ, lưu trữ dạng tuple kết hợp Zobrist Hash để tra cứu và caching trạng thái cực nhanh.
- **Macro-moves**: Gom nhóm các di chuyển tự do của người chơi thành một lệnh đẩy hộp, thu hẹp đáng kể không gian tìm kiếm.
- **Tracking `best_g_cost`**: Thay thế cơ chế Visited Sets cứng nhắc bằng `best_g_cost` để không bỏ sót các đường đi ngắn hơn dẫn đến cùng một trạng thái.
- **Map Hash Caching**: Cơ chế cache tiền xử lý dựa trên kiến trúc map thay vì tên file, loại bỏ rủi ro Cache Collision.

## Cấu trúc thư mục

```text

sokoban-ai-solver/
├── assets/                 # Các file hình ảnh và âm thanh
├── maps/                   # Kho dữ liệu các file .txt chứa ma trận màn chơi
├── sokoban/
│   ├── __init__.py
│   ├── algorithms.py       # Cài đặt logic cốt lõi của 7 thuật toán tìm kiếm AI .
│   ├── constants.py        # Định nghĩa các hằng số toàn cục: ký hiệu màu sắc, kích thước UI,...
│   ├── game.py             # Xử lý logic game và quản lý phiên chơi.
│   ├── level.py            # Đọc, phân tích và mã hóa map từ file .txt
│   ├── main.py             # Quản lý game loop, bắt sự kiện chuột/phím và điều phối đa luồng cho AI.
│   ├── solver_utils.py     # Các kỹ thuật tối ưu: tính heuristic, deadlock detection, sinh macro-moves,...
│   ├── state.py            # Định nghĩa cấu trúc bất biến của state, bao gồm vị trí player, boxes và zobrist.
│   └── ui.py               # Render giao diện, bảng điều khiển, popup, scrollbar
├── .gitignore
├── project_report.docx
├── README.md               # Tài liệu dự án
└── run.py                  # Script khởi chạy phụ

```

## Chỉ số Telemetry

Sau khi AI giải quyết một màn chơi, bảng dashboard sẽ hiển thị chi tiết các thông số đo lường hiệu năng:

- **ALGORITHM**: Thuật toán được sử dụng.
- **SOLVED**: Trạng thái hoàn thành (YES / NO).
- **PATH**: Số bước đi thực tế để giải map.
- **NODES**: Số lượng trạng thái đã mở rộng trong bộ nhớ.
- **TIME**: Thời gian chạy thuật toán (ms hoặc s)
