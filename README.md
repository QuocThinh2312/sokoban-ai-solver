# Sokoban AI Solver

Một hệ thống tự động giải game Sokoban được viết bằng Python và Pygame. Dự án áp dụng các kỹ thuật tìm kiếm không gian trạng thái từ cơ bản đến nâng cao để tự động tìm ra chuỗi hành động tối ưu đẩy toàn bộ hộp vào đích.

## Cài đặt

Cài đặt các thư viện phụ thuộc (Pygame, Numpy, Scipy,...)

## Cách chạy chương trình

Mở terminal tại thư mục gốc của dự án và gõ lệnh sau:

```bash
python run.py
```

## Điều khiển & Tương tác UI

- **Nút RUN AI**: Khởi chạy thuật toán AI để giải màn chơi hiện tại.
- **Nút RESTART**: Chơi lại từ đầu màn hiện tại.
- **Nút MAPS**: Mở cửa sổ popup chọn Level với thanh cuộn tương tác (hỗ trợ kéo thả và con lăn chuột).
- **Nút PAUSE / CONTINUE**: Tạm dừng hoặc tiếp tục quá trình di chuyển của bot AI sau khi đã giải xong.
- **Nút RANDOM**: Chọn ngẫu nhiên một màn chơi trong hệ thống.
- **Esc**: Thoát game.

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

Hệ thống hiện tại tích hợp một kho dữ liệu khổng lồ với hàng trăm màn chơi (ví dụ: level_001.txt đến level_694.txt và tiếp tục mở rộng) nằm trong thư mục maps/. Các map đa dạng độ khó từ cơ bản (kiểm tra luật) đến cực khó (đòi hỏi xử lý deadlock hình học phức tạp).

## Các Thuật toán AI được tích hợp

Danh sách các thuật toán tìm kiếm được cài đặt trong `sokoban/algorithms.py`:

1. **BFS**: Đảm bảo đường đi ngắn nhất nhưng tốn nhiều RAM.
2. **DFS**: Tiết kiệm bộ nhớ nhưng không tối ưu số bước.
3. **UCS**: Tối ưu theo chi phí.
4. **Greedy Search**: Tốc độ cực nhanh, kết hợp đa tầng Tie-breaking và Jitter (nhiễu ngẫu nhiên) để tránh Local Optimum.
5. **A\***: Kết hợp g(n) + h(n), cân bằng giữa tối ưu và hiệu suất.
6. **IDA\***: Phiên bản A\* tiết kiệm bộ nhớ.
7. **Weighted A\***: Nhân trọng số cho Heuristic để tăng tốc độ tìm kiếm tại các map cực lớn.
8. **Adaptive Beam Search**: Beam Search mở rộng linh hoạt, tự động nhận diện bế tắc (stagnation) để điều hướng không gian tìm kiếm.

## Kỹ thuật tối ưu & Cải tiến

- **State-aware Heuristic (Bitmask DP)**: Tối ưu hóa việc gán Hộp -> Đích bằng Bitmask DP. Heuristic không chỉ đo khoảng cách Manhattan mà còn cộng điểm phạt khi hộp nằm ở góc/tường hẹp và thưởng khi người chơi đứng gần hộp.
- **Geometric Deadlock Detection**: Hệ thống nhận diện bế tắc hình học chính xác (Static deadlock, Freeze deadlock, Tunnel deadlock, bẫy 2x2 tường/hộp) để cắt tỉa các nhánh vô vọng từ sớm mà không làm mất lời giải tối ưu.
- **Zobrist Hashing & State Representation**: Mô hình hóa trạng thái siêu nhẹ, lưu trữ dạng tuple kết hợp Zobrist Hash để tra cứu và caching trạng thái cực nhanh.
- **Macro-moves**: Gom nhóm các di chuyển tự do của người chơi thành một lệnh đẩy hộp, thu hẹp đáng kể không gian tìm kiếm.
- **Tracking `best_g_cost`**: Thay thế cơ chế Visited Sets cứng nhắc bằng `best_g_cost` để không bỏ sót các đường đi ngắn hơn dẫn đến cùng một trạng thái.
- **Map Hash Caching**: Cơ chế cache tiền xử lý dựa trên kiến trúc map thay vì tên file, loại bỏ rủi ro Cache Collision.

## Cấu trúc thư mục

SOKOBAN-AI-SOLVER/
├── assets/                 # Các file hình ảnh (box, wall, character, goal) và fonts
├── maps/                   # Kho dữ liệu các file .txt chứa ma trận màn chơi
├── sokoban/
│   ├── __init__.py
│   ├── algorithms.py       # Cài đặt logic cốt lõi của 8 thuật toán AI
│   ├── constants.py        # Định nghĩa màu sắc, tham số UI, kích thước
│   ├── game.py             # Quản lý phiên chơi, di chuyển, undo/restart
│   ├── level.py            # Đọc, phân tích và mã hóa bản đồ từ file txt
│   ├── main.py             # Vòng lặp game chính và luồng xử lý AI 
│   ├── solver_utils.py     # Lớp dữ liệu kết quả, cấu trúc Node và Hash
│   ├── state.py            # Quản lý State, Deadlock rules, Macro-moves
│   └── ui.py               # Render giao diện, bảng điều khiển, popup, scrollbar
├── .gitignore
├── project_report.docx
├── README.md               # Tài liệu dự án 
└── run.py                  # Script khởi chạy phụ

## Chỉ số Telemetry (Đầu ra hệ thống)

Sau khi AI giải quyết một màn chơi, bảng dashboard sẽ hiển thị chi tiết các thông số đo lường hiệu năng:

- **ALGO**: Thuật toán được sử dụng.
- **SOLVED**: Trạng thái hoàn thành (YES / NO).
- **PATH**: Số bước đi thực tế để giải map.
- **NODES**: Số lượng trạng thái đã mở rộng trong bộ nhớ.
- **TIME**: Thời gian chạy thuật toán.
- **RAM**: Ước lượng bộ nhớ đã tiêu thụ (KB).

```

```
