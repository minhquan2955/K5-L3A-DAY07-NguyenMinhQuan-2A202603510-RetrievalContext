# Tái lập dữ liệu Day06 để chạy Day07

Day07 dùng code ingestion, tài liệu và cấu hình đã chốt trong repo Day06. Không cần chép repo Day06, PDF, vector hoặc Docker volume vào repo Day07. Thông tin đối chiếu có thể đọc bằng máy ở [data/day06_reference.json](../data/day06_reference.json).

## Phiên bản nguồn

- Repo: [K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion](https://github.com/minhquan2955/K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion).
- Commit dùng tái lập: [`e81e2efa357db48ea263deb7efe27086b60a85dc`](https://github.com/minhquan2955/K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion/tree/e81e2efa357db48ea263deb7efe27086b60a85dc).
- [Code pipeline](https://github.com/minhquan2955/K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion/blob/e81e2efa357db48ea263deb7efe27086b60a85dc/starter/src/run.py), [Docker Compose](https://github.com/minhquan2955/K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion/blob/e81e2efa357db48ea263deb7efe27086b60a85dc/starter/docker-compose.yml), [manifest](https://github.com/minhquan2955/K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion/blob/e81e2efa357db48ea263deb7efe27086b60a85dc/data/manifest.json), [artifact run-02](https://github.com/minhquan2955/K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion/tree/e81e2efa357db48ea263deb7efe27086b60a85dc/starter/src/results/run-02).

Repo và commit đã được xác nhận có trên GitHub ngày 14/11/2026; tại thời điểm kiểm tra repo công khai. Nếu sau này thay quyền truy cập, cần cấp quyền xem **cả hai repo** cho người chấm. Dùng commit trên thay vì lấy nhánh `main` mới nhất.

PDF gốc `chapter1-2.pdf` đã được Git theo dõi trong commit này. Tài liệu là phần trích chương 1–2 của *Foundations of Information Systems*, Dr. Mahesh S. Raisinghani, OpenStax/Rice University. Giữ attribution và điều kiện sử dụng được ghi trong manifest Day06; hướng dẫn này không mở rộng phạm vi quyền sử dụng đã ghi nhận. Nguồn/ghi công gốc nằm trong manifest và PDF, không cần tải một bản sách mới có thể khác snapshot.

## Nếu đã có database Day06 trên máy

Không chạy lại ingestion. Từ thư mục gốc Day07, dùng hướng dẫn [RUN_AGENT.md](RUN_AGENT.md) hoặc môi trường Day07 riêng:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Điền OPENAI_API_KEY vào .env trên máy.
.\.venv\Scripts\python.exe -X utf8 starter/run.py check --env-file .env
```

Kiểm tra trace: strategy B, 505 chunk, 1536 chiều, fingerprint như bảng bên dưới. `check` không gọi embedding/model API. Nếu kết quả khác, đối chiếu phiên bản dữ liệu thay vì ghi đè store đang có.

## Dựng từ đầu trên máy mới — Windows PowerShell

Cần Git, Docker Compose đang hoạt động, Python 3.11+ và API key có quyền dùng embedding model cùng agent model. Môi trường nguồn dùng Python 3.14.2; các thư viện trích PDF được pin dưới đây để hạn chế khác biệt extraction. Bắt đầu từ thư mục gốc **Day07 đã clone**, dùng thư mục `day06-repro` mới cạnh Day07.

### 1. Lấy đúng code và tài liệu Day06

```powershell
$Day07Root = (Get-Location).Path
$Day06Root = Join-Path (Split-Path $Day07Root -Parent) 'day06-repro'
if (Test-Path -LiteralPath $Day06Root) { throw 'Thư mục đã tồn tại; chọn một thư mục mới hoặc dùng hướng dẫn database có sẵn.' }
git clone https://github.com/minhquan2955/K5-L3A-DAY06-NguyenMinhQuan-2A202603510-DataIngestion.git $Day06Root
if ($LASTEXITCODE -ne 0) { throw 'Clone Day06 không thành công.' }
git -C $Day06Root checkout --detach e81e2efa357db48ea263deb7efe27086b60a85dc
if ($LASTEXITCODE -ne 0) { throw 'Không checkout được commit đã chốt.' }
git -C $Day06Root rev-parse HEAD
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Day06Root 'chapter1-2.pdf')
```

SHA-256 của PDF phải là `45ea2a3a7fe5aa5f9fdf4beb4ef48bbdf9622d146c55684bb3edbe4b549f96b9`. Hai hash đầu vào còn lại nằm trong file reference. Pipeline Day06 tự kiểm tra PDF, manifest và câu hỏi theo `benchmark/freeze.json` trước khi xử lý.

### 2. Cài môi trường và cấu hình local

```powershell
Set-Location (Join-Path $Day06Root 'starter')
python -m venv .venv
$PythonDay06 = Join-Path $Day06Root 'starter\.venv\Scripts\python.exe'
& $PythonDay06 -m pip install -r requirements.txt 'pypdf==6.21.4' 'python-dotenv==1.2.4'
Copy-Item .env.example .env
```

Điền API key của người chạy vào `day06-repro/starter/.env`; giữ `EMBEDDING_MODEL=text-embedding-3-small`. `DATABASE_URL` mẫu dùng `127.0.0.1:55433/day6_lab` với tài khoản local được khai báo trong Compose. Không đưa `.env` vào Git; không dùng API key của người nộp bài để chia sẻ cho người chấm.

### 3. Khởi động PostgreSQL + pgvector

```powershell
docker compose -p day6_day7_repro up -d --wait
& $PythonDay06 -X utf8 scripts/check_setup.py
```

Chờ `Setup OK`. Compose dùng PostgreSQL 16, pgvector 0.8.7; `init.sql` bật extension. Tên project riêng tạo volume riêng trên máy mới. Nếu cổng 55433 đã có dịch vụ khác, dùng store Day06 sẵn có hoặc đổi đồng thời port mapping và `DATABASE_URL`; không xóa volume cũ để giải quyết xung đột.

### 4. Chuẩn bị offline rồi tạo lại vector store

Vẫn đứng tại `day06-repro/starter`:

```powershell
& $PythonDay06 -X utf8 -m src.run --mode prepare --size 500 --overlap 50 --paragraph-size 500 --dimensions 1536 --output results/day07-rebuild
```

Kỳ vọng 58 trang nội dung, A=449, B=505, C=505 chunk. Cảnh báo trang PDF 44 không có body là đã biết; trang này không thuộc nội dung được index. Kiểm tra phần `config` và `strategies` của `results/day07-rebuild/prepared.json` khớp `src/results/run-02/prepared.json` đã chốt.

Sau khi cấu hình và quyền sử dụng dữ liệu phù hợp với lần chạy của bạn, chạy:

```powershell
& $PythonDay06 -X utf8 -m src.run --mode ingest --size 500 --overlap 50 --paragraph-size 500 --dimensions 1536 --batch-size 64 --output results/day07-rebuild
```

Lệnh này gọi embedding API và ghi snapshot vào database được chọn trong `.env`. Pipeline Day06 dựng A/B/C; C dùng lại embedding B, Day07 chỉ chọn **B**. Ước lượng tham chiếu từ lần gốc: 75.979 document embedding token cho A+B; truy vấn/agent có chi phí riêng. Không cần chạy `eval` Day06 hay xem đáp án test để dựng store. Không dùng `--output src/results/run-02`, để giữ artifact gốc.

### 5. Chạy Day07 với store vừa dựng

```powershell
Set-Location $Day07Root
python -m venv .venv
$PythonDay07 = Join-Path $Day07Root '.venv\Scripts\python.exe'
& $PythonDay07 -m pip install -r requirements.txt
Copy-Item .env.example .env
# Điền OPENAI_API_KEY; nếu đổi cổng ở bước 3, sửa DATABASE_URL tương ứng.
& $PythonDay07 -X utf8 starter/run.py check --env-file .env
& $PythonDay07 -X utf8 starter/run.py search --env-file .env --method dense --query 'information system components' --top-k 3
& $PythonDay07 -X utf8 starter/run.py ask --env-file .env --method hybrid --model gpt-6-luna --query 'Hệ thống thông tin gồm những thành phần nào?'
```

`gpt-6-luna` dùng `reasoning_effort=none` cho function tools qua adapter hiện tại. Nếu model không được cấp quyền trên tài khoản của người chấm, ghi lại lỗi truy cập; việc đổi model cần được ghi rõ là cấu hình khác. Chi tiết trace và các tham số tại [RUN_AGENT.md](RUN_AGENT.md).

## Các giá trị phải đối chiếu

| Thuộc tính | Giá trị |
|---|---|
| Nguồn | `openstax-foundations-is-ch1-2` / `chapter1-2.pdf` |
| Trang | 83 trang vật lý, 58 trang nội dung; page là số trang PDF 1-based |
| Strategy Day07 | B: 505 chunk, tối đa 500 ký tự, không overlap |
| Embedding | `text-embedding-3-small`, 1536 chiều |
| Store | `day6_lab`, `public.day6_chunks`, cosine exact |
| Snapshot chunk B | `061cbe8ade9e8ff4b1574ce17d00f5c4bebccc400e6875564648d1008986ddbb` |
| Run fingerprint | `e3d97a351de5a9a1b21aa4f7067d58515fcd6c5397aab0150987e9bd6a376b5f` |

Snapshot chunk được Day06 tính bằng SHA-256 của JSON canonical từ các chunk (bao gồm ID, text, nguồn và metadata), không phải hash byte trực tiếp của file JSONL. Fingerprint run là hash của cấu hình đầy đủ, bao gồm hash cả ba snapshot. Dùng giá trị trong `prepared.json` để đối chiếu; trace `check` Day07 báo fingerprint đang có trong database.

Repo Day06 có chunk JSONL và log ingest, **không có vector float**. Vì vậy clone repo chưa đủ để dense retrieval hoạt động: cần dùng database có sẵn hoặc chạy ingest. Model embedding là alias không khóa revision weights; dựng lại cùng model/dimension và chunk không bảo đảm vector giống từng byte hoặc câu trả lời agent giống hệt. Khi cần giữ chính xác vector, phải chuyển database backup riêng theo phạm vi chia sẻ phù hợp; phương án hiện tại là tái tạo từ nguồn.

## Kiểm chứng đã thực hiện

Ngày 14/11/2026: xác nhận commit qua GitHub, checkout Day06 local sạch; chạy `prepare` vào thư mục kết quả mới trong Day07, không gọi API hay ghi database. Cấu hình, fingerprint, hash đầu vào và thống kê A/B/C khớp artifact `run-02`; B có 505 chunk. Đã kiểm tra cú pháp các tham số bằng `--help`. Chưa chạy lại toàn bộ ingest trên database trống trong lần bổ sung tài liệu này; database hiện có đã được kiểm tra ở bước triển khai agent trước đó.
