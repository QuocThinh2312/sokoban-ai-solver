# CLAUDE.md

Hướng dẫn làm việc để giảm các lỗi lập trình thường gặp của mô hình ngôn ngữ. Có thể kết hợp với hướng dẫn riêng của dự án khi cần.

**Đánh đổi:** các hướng dẫn này ưu tiên cẩn thận hơn tốc độ. Với việc nhỏ, dùng phán đoán phù hợp.

## 1. Suy nghĩ trước khi viết mã

**Không tự đoán. Không giấu điểm chưa rõ. Nêu rõ đánh đổi.**

Trước khi triển khai:

- Nêu rõ giả định. Nếu chưa chắc, hãy hỏi.
- Nếu có nhiều cách hiểu, trình bày các cách hiểu đó, đừng tự chọn âm thầm.
- Nếu có cách đơn giản hơn, hãy nói ra. Phản biện khi cần.
- Nếu yêu cầu chưa rõ, dừng lại. Nói rõ điểm chưa rõ và hỏi lại.

## 2. Ưu tiên đơn giản

**Viết lượng mã tối thiểu để giải quyết vấn đề. Không thêm thứ suy đoán.**

- Không thêm tính năng ngoài yêu cầu.
- Không tạo trừu tượng cho mã chỉ dùng một lần.
- Không thêm khả năng linh hoạt hoặc cấu hình nếu không được yêu cầu.
- Không thêm xử lý lỗi cho trường hợp không thể xảy ra.
- Nếu viết 200 dòng mà có thể còn 50 dòng, hãy viết lại cho gọn.

Tự hỏi: "Một kỹ sư lâu năm có thấy phần này quá phức tạp không?" Nếu có, hãy đơn giản hóa.

## 3. Sửa đúng phạm vi

**Chỉ chạm vào phần cần thiết. Chỉ dọn phần do chính thay đổi của mình tạo ra.**

Khi sửa mã có sẵn:

- Không tiện tay chỉnh mã, bình luận hoặc định dạng ở khu vực không liên quan.
- Không tái cấu trúc phần không hỏng.
- Giữ phong cách hiện có, kể cả khi bạn thích cách khác hơn.
- Nếu thấy mã chết không liên quan, hãy ghi chú, đừng tự xóa.

Khi thay đổi của bạn tạo ra phần thừa:

- Xóa import, biến, hàm do chính thay đổi của bạn làm thành không dùng nữa.
- Không xóa mã chết có sẵn trừ khi được yêu cầu.

Tiêu chí kiểm tra: mọi dòng thay đổi phải gắn trực tiếp với yêu cầu của người dùng.

## 4. Làm việc theo mục tiêu

**Đặt tiêu chí thành công. Lặp lại cho tới khi đã kiểm chứng.**

Chuyển việc cần làm thành mục tiêu có thể kiểm tra:

- "Thêm kiểm tra hợp lệ" -> "Viết kiểm thử cho đầu vào sai, rồi làm cho kiểm thử chạy qua".
- "Sửa lỗi" -> "Viết kiểm thử tái hiện lỗi, rồi làm cho kiểm thử chạy qua".
- "Tái cấu trúc X" -> "Đảm bảo kiểm thử chạy qua trước và sau khi sửa".

Với việc nhiều bước, nêu kế hoạch ngắn:

```text
1. [Bước] -> kiểm tra: [lệnh hoặc kết quả]
2. [Bước] -> kiểm tra: [lệnh hoặc kết quả]
3. [Bước] -> kiểm tra: [lệnh hoặc kết quả]
```

Tiêu chí thành công rõ giúp tự làm việc tới cùng. Tiêu chí yếu như "làm cho chạy" thường cần hỏi lại liên tục.

---

## 5. Viết ngắn gọn

Ưu tiên rõ ràng với ít chữ nhất có thể. Tránh dài dòng.

- Trả lời ngắn nhưng đủ ý.
- Tránh giải thích không cần thiết.
- Tập trung vào ý chính, bỏ phần thừa.
- Chỉ mở rộng khi cần để tránh hiểu nhầm.
- Ưu tiên danh sách hoặc các bước thay vì đoạn văn dài.

Tự hỏi: "Có thể nói ngắn hơn mà không mất ý không?" Nếu có, hãy rút gọn.

---

**Các hướng dẫn này hiệu quả khi:** diff ít thay đổi thừa hơn, ít phải viết lại vì quá phức tạp hơn, và câu hỏi làm rõ xuất hiện trước khi triển khai thay vì sau khi sai.
