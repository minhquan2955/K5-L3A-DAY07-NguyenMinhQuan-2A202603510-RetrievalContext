# Kiểm tra bài nộp Day07

- [x] Code dense, TF-IDF, hybrid RRF và agent thật `gpt-6-luna`; hướng dẫn chạy và test offline.
- [x] Model embedding/số chiều, vector store, repo/commit Day06 và cách tái tạo đã ghi rõ.
- [x] 24 câu Việt: dev15+2, test5+2; freeze/hash và kiểm tra nguồn, gold riêng khỏi agent.
- [x] So sánh ba phương pháp trên cùng B505; hai cấu hình thử cải thiện với giả thuyết riêng.
- [x] Raw trace65 lượt agent: dev51, test14; có query gốc/viết lại, tool/context/answer/citation/time/token/error.
- [x] Chốt TF-IDF theo dev trước test, có timestamp và hash; test baseline+selected giữ nguyên pipeline.
- [x] Đọc/audit đủ5 câu test có đáp án và2 câu thiếu evidence cho mỗi cấu hình; labels có lý do, source/citation; công khai Codex hỗ trợ.
- [x] Báo cáo cá nhân có bảng metric, ít nhất2 lỗi dev, ví dụ có nguồn/từ chối/lỗi và giới hạn.
- [x] `REPORT.md` và `report/individual/2A202603510_NguyenMinhQuan.md` cùng tuân thủ cấu trúc template: tiêu đề, bốn mục, nhãn bullet và các bảng; liên kết được chỉnh đúng theo vị trí file.
- [x] Không sửa câu hỏi, PDF, manifest, code ingestion hay store Day06; đối chiếu hash trước/sau.
- [x] Token usage đo được, USD ghi chưa xác định thay vì bịa giá; chưa bao gồm hóa đơn ingest/smoke.
- [ ] Học viên tự đọc/xác nhận lại source và nhãn hỗ trợ AI; trường `independent_student_review=false` được giữ trung thực.
- [ ] Đối soát chi phí USD từ provider nếu cần số tiền thực tế; kết quả hiện tại công bố token và USD=null.
- [ ] Commit/push bản bài làm vào repo Day07 và nộp link theo giảng viên. Repo hiện công khai, nhưng kiểm tra GitHub ngày 14/11/2026 chưa thấy `starter/benchmark.py`; code và kết quả mới còn ở local.

Không làm thử thách100 trang/bonus15. Các ô còn mở là trạng thái thực tế, không phải kết quả đánh giá thất bại.

## Điểm vào

- [Báo cáo](../../report/individual/2A202603510_NguyenMinhQuan.md)
- [Lệnh benchmark và cách chấm](../../docs/EXPERIMENTS.md)
- [Tái lập Day06](../../docs/DAY06_REPRODUCIBILITY.md)
- [Dev summary](run-01/summary.dev.json) / [Test summary](run-01/summary.test.json)
- [Selection trước test](run-01/selection.dev.json)
- [Integrity trước](day06-integrity.before.json) / [Integrity sau](day06-integrity.after.json)
- [Kiểm tra cấu trúc template và hồ sơ nộp](submission_audit.json) / [Log test lần kiểm tra nộp](submission-unittest.log)
