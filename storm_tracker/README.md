# Storm Tracker VN

WebGIS hỗ trợ tra cứu lịch sử bão, theo dõi gần thời gian thực, tìm bão tương tự và xem dashboard phân tích cho vùng biển Việt Nam.

## Cấu Trúc Thư Mục

```text
storm_tracker/
|-- app.py                  # Flask app, routes và API
|-- backend/                # Logic lấy dữ liệu realtime và so sánh bão
|-- data/                   # Dữ liệu GeoJSON dùng cho lịch sử, tương tự và dashboard
|-- frontend/               # Giao diện HTML/CSS/JS
|-- scripts/                # Script xử lý/cập nhật dữ liệu lịch sử
|-- tests/                  # Pytest
|-- docs/                   # Tài liệu demo, kiểm thử, kết quả phân tích
|-- requirements.txt
`-- README.md
```

## Module Chính

| Module | Trang | Nội dung |
| --- | --- | --- |
| Bản đồ lịch sử | `/` | Bản đồ lịch sử bão, lọc dữ liệu, track gradient, heatmap, animation |
| theo dõi thời gian thực | `/realtime` | Theo dõi bão gần thời gian thực, có fallback Yagi 2024 |
| tìm bão tương tự | Trong Bản đồ lịch sử | Tìm bão lịch sử tương tự bằng DTW và điểm tổng hợp |
| dashboard phân tích | `/dashboard` | Dashboard xu hướng theo thập kỷ, mùa vụ, cấp bão và vùng |
| dự báo mùa | `/seasonal-forecast` | Dự báo xác suất mùa bão 2026 theo tháng, ENSO/SST scenario |

## Chạy Local

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Các trang chính:

- Bản đồ lịch sử: `http://localhost:5000/`
- Theo dõi thời gian thực: `http://localhost:5000/realtime`
- Dashboard phân tích: `http://localhost:5000/dashboard`
- Dự báo mùa: `http://localhost:5000/seasonal-forecast`
- API status: `http://localhost:5000/api/status`

## Cập Nhật Dữ Liệu Lịch Sử

```bash
python scripts/process_historical_data.py
python scripts/process_historical_data.py --force
```

Output mặc định: `data/storms_vn.geojson`.

## Kiểm Thử

```bash
python -m py_compile app.py backend\fetcher.py backend\similarity.py scripts\process_historical_data.py
python -m pytest tests -q
```

Checklist chi tiết: [docs/TESTING.md](docs/TESTING.md).

## API Chính

| Endpoint | Mô tả |
| --- | --- |
| `GET /api/status` | Trạng thái hệ thống và module |
| `GET /api/historical-storms` | GeoJSON bão lịch sử |
| `GET /api/update-historical?force=1` | Cập nhật dữ liệu IBTrACS |
| `GET /api/active-storms` | Bão đang hoạt động hoặc dữ liệu mẫu |
| `GET /api/forecast/<storm_id>` | Dự báo của bão nếu có |
| `GET /api/similar-storms/<storm_id>` | Top bão lịch sử tương tự |
| `GET /api/dashboard-stats` | Số liệu dashboard phân tích |
| `GET /api/seasonal-forecast?year=2026` | Dự báo xác suất mùa bão 2026 |

## Tài Liệu Hỗ Trợ Bảo Vệ

- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md): kịch bản demo 10-15 phút.
- [docs/REPORT_FINDINGS.md](docs/REPORT_FINDINGS.md): kết luận phân tích dữ liệu.
- [docs/TESTING.md](docs/TESTING.md): kế hoạch kiểm thử.
- [docs/SEASONAL_FORECAST.md](docs/SEASONAL_FORECAST.md): mô tả model dự báo mùa bão 2026.

## Ghi Chú

- Phân cấp bão dùng nhóm: áp thấp nhiệt đới, bão thường, bão mạnh, bão rất mạnh, siêu bão.
- theo dõi thời gian thực dùng JMA và IBTrACS NRT; nếu nguồn ngoài lỗi hoặc không có bão, hệ thống dùng dữ liệu mẫu Yagi 2024.
- Bản đồ lịch sử luôn phục vụ GeoJSON đang có để tránh timeout khi deploy; chỉ cập nhật NOAA khi gọi `GET /api/update-historical?force=1`.
- dự báo mùa là model thử nghiệm phục vụ đồ án, không thay thế dự báo chính thức của cơ quan khí tượng.
- Phần deploy public và khảo sát người dùng không nằm trong phạm vi bắt buộc của đồ án cử nhân hiện tại.
