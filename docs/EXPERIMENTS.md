# Chạy và kiểm chứng benchmark Day07

Day06 được giữ nguyên. Câu hỏi Day07 vẫn là tiếng Việt; 15 câu dev có đáp án được tái sử dụng nguyên văn từ dev Day06. Câu hỏi test Day07 được tạo riêng trước thí nghiệm. Query agent viết lại bằng tiếng Anh được ghi trong tool trace, không thay câu hỏi gốc hay benchmark Day06.

## Dữ liệu và cấu hình

- `benchmark/cases.json`: câu hỏi, split, đáp án/evidence và các câu thiếu bằng chứng; chỉ evaluator đọc gold.
- `benchmark/freeze.json`: hash dữ liệu và thời điểm đóng băng.
- `benchmark/source_review.json`: kiểm tra nguồn, evidence và giới hạn.
- `benchmark/configs.json`: ba cấu hình đã công bố trước chạy dev.
- `artifacts/day07/run-01/`: metadata, raw trace theo từng câu, nhãn đọc đối chiếu và summary.

Không chỉnh câu hỏi hay code để tối ưu sau khi xem test. Muốn thử tiếp phải dùng run mới và test mới nếu đã dùng test để chỉnh.

## Lệnh chạy

Từ thư mục gốc Day07, dùng venv đã cài `requirements.txt`. Ví dụ khi tận dụng môi trường Day06 trên máy hiện tại:

```powershell
$Day06Root = 'D:\K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion'
$PythonDay07 = "$Day06Root\starter\src\.venv\Scripts\python.exe"
$EnvDay07 = "$Day06Root\starter\.env"
& $PythonDay07 -X utf8 starter/benchmark.py run --split dev --env-file $EnvDay07 --output artifacts/day07/run-02
```

Trên máy mới, thay `$PythonDay07` bằng `.\.venv\Scripts\python.exe` và `$EnvDay07` bằng `.env`; dựng store theo [hướng dẫn tái lập](DAY06_REPRODUCIBILITY.md). Dùng `--output artifacts/day07/run-02` cho lần chạy khác; không ghi đè run đã chọn.

Mỗi câu thực hiện retrieval bằng query gốc, sau đó chạy agent thật với phương pháp tương ứng. Các query viết lại và nhiều lượt tìm được lưu riêng. Chạy đồng thời mặc định 4 câu (`--workers`), thời gian mỗi câu là wall time và không phải benchmark tải hệ thống. Trace có token đo được; USD để `null` khi chưa có đơn giá thực tế.

Sau khi đọc lỗi dev và đối chiếu kết quả, chốt cấu hình:

```powershell
& $PythonDay07 -X utf8 starter/benchmark.py select --output artifacts/day07/run-02
& $PythonDay07 -X utf8 starter/benchmark.py run --split test --env-file $EnvDay07 --output artifacts/day07/run-02
```

`selection.dev.json` lưu timestamp và hash pipeline/cases/config/corpus-reference, chặn test nếu code hoặc cấu hình khác lần dev. Quy tắc công bố trước: ưu tiên Context Evidence count dev, rồi first-tool Hit@3, ít lỗi provider/retrieval hơn, ít token đo được hơn, cuối cùng ID cấu hình. Grounded answer/citation được đọc riêng và công bố; không dùng điểm test để đổi lựa chọn. Nếu baseline được chọn, kết quả baseline và selected là cùng một lần chạy, không giả tạo một phép so sánh độc lập.

## Định nghĩa metric

- Hit yêu cầu đúng `source_id`, trang PDF vật lý và chứa trọn evidence chuẩn hóa NFC/whitespace trong một chunk; các gold là evidence thay thế.
- `original_hit1/3`: ranking query tiếng Việt gốc, cutoff thống nhất 1/3.
- `first_tool_hit1/3`: ranking của lượt retrieval đầu do agent quyết định, kể cả query viết lại. Không coi ranking này là ranking hợp nhất của mọi lượt tìm.
- `context_evidence`: có gold evidence hợp lệ trong context cuối, kể cả evidence từ lượt tìm trước. Chỉ tính câu có đáp án; 4 câu thiếu evidence không vào mẫu số retrieval/context.
- Exact evidence metric là chỉ báo bảo thủ, không thay thế đọc ngữ nghĩa. Ví dụ evidence gốc của q13 Day06 bị chia qua nhiều chunk B: giữ gold nguyên vẹn; ghi riêng trường hợp context hỗ trợ nội dung dù exact metric không hit.
- Lỗi agent/model/store được lưu riêng. Partial search events đã hoàn tất được giữ nếu lần model sau lỗi; không thay lỗi bằng vector/câu trả lời giả.

## Chấm câu trả lời và citation

Đọc mỗi trace cùng câu hỏi, đáp án, evidence và context. Tạo `reviews.json` trong từng thư mục cấu hình/split, mỗi dòng có `query_id`, `context_grade` (0/1/2 cho câu có đáp án), `answer_grade` (0/1/2), `citation_support` (một boolean mỗi citation), `abstention_correct` cho câu thiếu evidence, lý do và người/công cụ hỗ trợ. Không suy citation support từ việc ID có trong context.

Nhãn Codex hỗ trợ phải ghi rõ là audit hỗ trợ AI, chưa phải chấm độc lập của học viên. Người nộp cần đọc lại nguồn, nhãn và giải thích được pipeline. Không ghi tên học viên như thể đã tự chấm nếu chưa có xác nhận.

Sau khi có nhãn:

```powershell
& $PythonDay07 -X utf8 starter/benchmark.py summarize --split dev --output artifacts/day07/run-02
& $PythonDay07 -X utf8 starter/benchmark.py summarize --split test --output artifacts/day07/run-02
```

Summary tổng hợp nhãn, không tự phán đoán câu trả lời. Đọc toàn bộ 5 câu test có đáp án và 2 câu thiếu evidence cho baseline và selected. Báo điểm context/answer, citation hỗ trợ nội dung, abstention, từ chối nhầm, lỗi, token và thời gian. Báo cáo cá nhân liên kết các trace cụ thể và phân tích ít nhất hai lỗi dev.
