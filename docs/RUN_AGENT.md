# Chạy Day07 — bước 1 đến 3

Đã triển khai kết nối Day06, ba phương pháp retrieval và agent dùng model thật. Benchmark Day07 đã chạy: xem [thí nghiệm](EXPERIMENTS.md), [báo cáo](../report/individual/2A202603510_NguyenMinhQuan.md) và [kết quả](../artifacts/day07/run-01/). Phần dưới hướng dẫn chạy từng câu; các smoke ban đầu không thay benchmark.

## Chuẩn bị

Chạy từ thư mục gốc repo Day07, dùng Python 3.11+. Docker Compose Day06 phải đang chạy. Có thể dùng venv Day06 hiện có, không cần cài thêm vào Day06:

```powershell
$LabDay6 = 'D:\K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion'
$PythonDay7 = "$LabDay6\starter\src\.venv\Scripts\python.exe"
$EnvDay7 = "$LabDay6\starter\.env"
& $PythonDay7 -X utf8 starter/run.py check --env-file $EnvDay7
```

Hoặc tạo môi trường riêng tại repo Day07:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Điền OPENAI_API_KEY vào .env trên máy; không commit file này.
$PythonDay7 = '.\.venv\Scripts\python.exe'
$EnvDay7 = '.env'
& $PythonDay7 -X utf8 starter/run.py check --env-file $EnvDay7
```

`--env-file` được đọc rõ ràng và ưu tiên hơn biến môi trường cùng tên trong tiến trình. Không sao chép secret sang code hay trace. Nếu chuyển sang máy khác, làm theo [hướng dẫn tái lập Day06 đã pin commit](DAY06_REPRODUCIBILITY.md); repo Day07 không chứa vector hay database volume. [File reference](../data/day06_reference.json) ghi model, số chiều, hash và snapshot cần đối chiếu.

## Truy xuất

```powershell
& $PythonDay7 -X utf8 starter/run.py search --env-file $EnvDay7 --method dense --query 'information system components' --top-k 3
& $PythonDay7 -X utf8 starter/run.py search --env-file $EnvDay7 --method tfidf --query 'information system components' --top-k 3
& $PythonDay7 -X utf8 starter/run.py search --env-file $EnvDay7 --method hybrid --query 'information system components' --top-k 3
```

Mở file JSON ở đường dẫn `trace` để đọc kết quả, score, rank, nguồn, trang và metadata. Có thể chỉ định đường dẫn mới bằng `--output starter/results/my-search.json`; CLI từ chối ghi đè file đã có.

- **Dense:** `text-embedding-3-small`, 1536 chiều, cosine exact trong `public.day6_chunks`, mặc định `strategy=B`.
- **TF-IDF:** dùng implementation sẵn trong `starter/baseline.py`, chỉ mục lexical được dựng từ chính snapshot B lấy từ database. Không gọi embedding API khi chạy `search --method tfidf`.
- **Hybrid:** lấy mặc định 20 candidate mỗi phương pháp, hợp nhất bằng RRF: `sum(1 / (60 + rank))`, rồi lấy top-k. Không cộng raw cosine score với TF-IDF score. Trace có ranking thành phần và rank của từng hit.

Cả ba dùng chung corpus và filter. `--filter` nhận JSON, ví dụ `'{"chapter":2}'` (với shell không giữ nguyên dấu nháy, dùng biến PowerShell hoặc escape theo phiên bản shell). Filter phải do người dùng cung cấp; agent không đọc gold để tạo filter. Filter được áp dụng trước cutoff. ID, số trang vật lý PDF 1-based và metadata được giữ nguyên; `source_id` là `document_id` Day06.

Khi khởi tạo, chương trình kiểm tra kích thước vector, không chấp nhận strategy rỗng hoặc nhiều fingerprint. Mọi SQL đều chỉ đọc; không tạo bảng, ingest hay cập nhật Day06. Tên embedding model phải khớp model dùng ingest Day06: database tự kiểm tra được kích thước, nhưng không chứng minh model identity chỉ từ vector. Cấu hình model được xác nhận từ artifact Day06 `run-02`; không đổi `--embedding-model` sang model khác dù cùng số chiều.

## Hỏi agent thật

```powershell
& $PythonDay7 -X utf8 starter/run.py ask --env-file $EnvDay7 --method hybrid --query 'Hệ thống thông tin gồm những thành phần nào? Giải thích ngắn gọn dựa trên tài liệu.'
& $PythonDay7 -X utf8 starter/run.py ask --env-file $EnvDay7 --method hybrid --query 'Theo tài liệu, VinUni có chính xác bao nhiêu sinh viên nhập học năm 2026?'
```

Model mặc định `gpt-6-luna` theo yêu cầu người dùng; thay bằng `--model <model-tool-calling>` hoặc `AGENT_MODEL` trong env file. Cần API endpoint và API key có quyền truy cập đúng model ID này. Agent dùng Chat Completions tool calling, bắt buộc gọi `search` đầu tiên, sau đó có thể tìm lại, gọi `answer` hoặc `abstain`. Một retrieval tool sử dụng phương pháp đã chọn qua `--method` cho suốt lần chạy. Không cần framework agent bổ sung.

Với `gpt-6-luna`, adapter gửi `reasoning_effort=none` vì API Chat Completions yêu cầu tùy chọn này khi dùng function tools. Tùy chọn được lưu trong trace; các model khác không nhận override này. Các trace `gpt-4.1-mini` bên dưới là lịch sử kiểm tra trước khi đổi model.

Nếu model cung cấp danh sách `citations` riêng nhưng bỏ toàn bộ citation trong văn bản, adapter hiển thị các ID đã khai báo ở cuối câu trả lời. Validator vẫn từ chối ID ngoài context; không tự tìm hoặc tạo nguồn thay model. Citation hỗ trợ nội dung hay không vẫn cần đánh giá riêng.

Giới hạn mặc định: `--max-searches 3`, `--top-k 5`, `--candidate-k 20`, `--budget 4000` **ký tự** (bao gồm nguồn/citation). Đây là cấu hình khởi đầu, chưa được chọn bằng benchmark. Context được deduplicate theo chunk ID; chunk không vừa budget bị bỏ nguyên khối. Khung hiện giữ ưu tiên các chunk tìm trước; khi nhiều lượt tìm, evidence mới có thể không vừa budget — kiểm tra context trong trace khi làm dev.

Agent chỉ nhận câu hỏi, query đã tìm và context trong budget. Prompt yêu cầu xem nội dung truy xuất là dữ liệu, trả lời tiếng Việt khi người dùng hỏi tiếng Việt, trích `[chunk-id]`, và từ chối khi thiếu evidence. Citation ID được kiểm tra lại bằng code; việc nguồn có hỗ trợ từng khẳng định vẫn cần đánh giá nội dung ở các bước sau.

## Trace và lỗi

Mỗi lệnh ghi JSON UTF-8 trong `starter/results/smoke/` theo mặc định. Đây là kiểm tra vận hành, **không phải kết quả benchmark**. `starter/results/` bị Git bỏ qua; có thể chọn chia sẻ các trace được phép sau.

Trace gồm cấu hình; corpus/fingerprint; query gốc; query agent viết lại; filter; retrieval results/score/rank; context cuối trong event search; câu trả lời/citation; các quyết định model; token usage của model và embedding; thời gian; lỗi. Chi phí USD để `null` vì chưa cấu hình đơn giá; không coi `null` là 0 USD. `check` xác nhận database, không xác nhận API key hay quyền truy cập agent model.

Lỗi API/database trả `status=error`, mã thoát 1, và trace lỗi với tên loại lỗi (thêm HTTP status khi có). Không fallback sang mock/vector giả. Tránh ghi raw exception vì có thể chứa credential. Khi lỗi giữa chừng, `model_calls` giữ context đã gửi và `retrieval_calls` giữ các lượt truy xuất trước lỗi. Không diễn giải lỗi kết nối thành abstention đúng.

## Kiểm tra code

```powershell
& $PythonDay7 -X utf8 -m unittest discover -s tests -v
```

Test offline dùng dữ liệu nhỏ và thay network boundary khi cần; không dùng kết quả này để báo chất lượng agent. Khi chạy từ sandbox chặn mạng, cần quyền chạy API ngoài sandbox; giữ trace lỗi và chạy lại với đường dẫn output mới.

## Code

| File | Vai trò |
|---|---|
| `starter/retrieval.py` | Snapshot pgvector, dense, TF-IDF có filter và RRF |
| `starter/model_controller.py` | Model thật quyết định search/answer/abstain qua tool calling |
| `starter/agentic.py` | Vòng lặp có giới hạn, context và kiểm tra citation ID |
| `starter/run.py` | CLI, cấu hình, trace và lỗi |
| `tests/test_connected_agent.py` | Kiểm tra các hành vi mới |

Benchmark dev/test, so sánh/cải thiện, selection trước test và báo cáo cá nhân đã thực hiện. Câu hỏi Day06 giữ nguyên; câu hỏi benchmark Day07 là tiếng Việt, query viết lại được lưu riêng.

## Kết quả kiểm tra vận hành ngày 14/11/2026

- Database thật: snapshot B có 505 chunk, vector 1536 chiều.
- Cả dense, TF-IDF và hybrid đã trả kết quả từ corpus thật. Dense/hybrid đã dùng embedding API thật.
- `gpt-4.1-mini` đã dùng retrieval tool và trả lời có citation cho câu hỏi thành phần hệ thống thông tin: `starter/results/smoke/live-answer-v2.json`.
- Câu hỏi số sinh viên VinUni nhập học năm 2026 được agent từ chối: `starter/results/smoke/live-abstain.json`.
- 24 test offline đạt. Có thêm 12 kiểm tra filter trực tiếp trên PostgreSQL bằng vector có sẵn làm fixture (không phải query embedding API, không phải benchmark), lưu tại `starter/results/smoke/regression.json`.
- Review độc lập phát hiện citation không khai báo và khác biệt bool/number giữa filter Python và JSONB; đã tái hiện bằng test rồi sửa. Validator hiện yêu cầu toàn bộ citation trong câu trả lời khớp danh sách khai báo và đều thuộc context.
- Lần trả lời đầu bị từ chối do model gộp citation `[id1, id2]`; trace lỗi định dạng được giữ tại `live-answer.json`. Adapter hiện chỉ chuyển nhóm ID đã khai báo thành `[id1][id2]`, không tạo nguồn mới. Câu trả lời API thật `live-answer-v2.json` cũng đã qua validator cuối cùng bằng replay, không gọi API lại.

Đây chỉ xác nhận kết nối và luồng chạy. Chưa có kết luận về chất lượng benchmark hoặc cấu hình tối ưu; citation ID hợp lệ vẫn cần đối chiếu nội dung nguồn.
