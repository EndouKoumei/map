# STORM TRACKER VN - HỆ THỐNG THEO DÕI VÀ PHÂN TÍCH BÃO ẢNH HƯỞNG VIỆT NAM

## TÁC GIẢ

- **Họ tên sinh viên**: Đặng Hồng Minh
- **Mã số sinh viên**: 20225740
- **Lớp**: CNTT Việt-Nhật 05, K67 (Chương trình định hướng Nhật Bản - IT-E6)
- **Trường**: Đại học Bách Khoa Hà Nội (HUST)
- **Giảng viên hướng dẫn**: ThS. Vũ Đức Vượng

## GIỚI THIỆU

Storm Tracker VN là một hệ thống WebGIS phục vụ đồ án tốt nghiệp, cho phép tra cứu, trực quan hóa và phân tích các cơn bão ảnh hưởng tới vùng biển Việt Nam trong lịch sử (1884-nay), đồng thời theo dõi bão đang hoạt động và so sánh với các cơn bão lịch sử có quỹ đạo/cường độ tương tự. Hệ thống được xây dựng dưới dạng ứng dụng Flask (Python) phục vụ cả backend xử lý dữ liệu và frontend bản đồ tương tác, với dữ liệu gốc lấy từ **IBTrACS v04r01 (NOAA)**.

### Tính năng chính:
- **Bản đồ bão lịch sử**: hiển thị quỹ đạo hơn 2.300 cơn bão (1884-2026) trên nền Leaflet.js, đường đi đổi màu theo cấp gió tại từng thời điểm (theo tiêu chuẩn phân cấp QĐ 18/2021/QĐ-TTg), kèm heatmap mật độ, animation phát lại theo thời gian và bộ lọc theo mùa/khu vực/cường độ
- **Theo dõi thời gian thực (near real-time)**: tổng hợp bão đang hoạt động từ nhiều nguồn theo thứ tự ưu tiên (JMA → IBTrACS NRT → dữ liệu mẫu Yagi 2024 khi các nguồn ngoài không khả dụng)
- **Tìm quỹ đạo bão tương tự**: sử dụng thuật toán Dynamic Time Warping (DTW) kết hợp cosine similarity trên vector đặc trưng 9 chiều để tìm các cơn bão lịch sử có quỹ đạo và cường độ gần giống một cơn bão cho trước, hiển thị đồng thời trên bản đồ để so sánh trực quan
- **Dashboard phân tích thống kê**: xu hướng theo thập kỷ, phân bố theo mùa, tỉ lệ bão mạnh (STY) trước/sau năm 2000, tần suất ảnh hưởng theo tỉnh ven biển
- **Outlook xác suất mùa bão**: ước lượng số lượng bão theo tháng bằng phân phối Poisson, hiệu chỉnh theo kịch bản ENSO/SST
- **API RESTful**: 9 endpoint phục vụ dữ liệu cho frontend và có thể tích hợp bên ngoài
- **Cơ chế dữ liệu bền vững**: cache GeoJSON lịch sử (TTL 7 ngày), tự động dùng lại dữ liệu cũ khi NOAA không phản hồi, tránh timeout khi triển khai

- Hình ảnh tổng quan bản đồ lịch sử:
<div align="center">
<img src="/storm_tracker/docs/screenshot_historical_map.png" width="700"/>
</div>
<p align="center"><em>Hình 1: Giao diện bản đồ bão lịch sử</em></p>

## KIẾN TRÚC HỆ THỐNG

Hệ thống được tổ chức thành 2 thành phần chính, chạy trong một ứng dụng Flask duy nhất:

### 1. **Backend xử lý & phân tích dữ liệu** (Python / Flask)
- Framework: Flask 3.x + Flask-CORS
- Xử lý dữ liệu: pandas, numpy
- Thu thập dữ liệu bão lịch sử từ IBTrACS (NOAA) qua script ETL riêng
- Thu thập dữ liệu bão hoạt động (near real-time) từ JMA / IBTrACS NRT với cơ chế fallback
- Thuật toán tìm kiếm tương đồng quỹ đạo (DTW + cosine similarity)
- Mô hình thống kê outlook mùa bão (Poisson + hệ số hiệu chỉnh ENSO/SST)
- Triển khai: Gunicorn (production) trên Railway/Render qua `Procfile`

### 2. **Frontend bản đồ tương tác** (HTML/CSS/JavaScript)
- Bản đồ: Leaflet.js (quỹ đạo, heatmap, animation theo thời gian)
- Không dùng framework SPA - render qua Flask `render_template` (Jinja2) kết hợp JavaScript thuần
- Biểu đồ thống kê trong dashboard
- Layout dùng chung qua partials (navbar)

### Cấu trúc thư mục:
```
storm_tracker/
├── app.py                        # Flask routes + tổng hợp toàn bộ API endpoint
├── backend/
│   ├── fetcher.py                 # StormRealtimeFetcher - lấy bão đang hoạt động (JMA/NRT/fallback)
│   ├── similarity.py              # Tìm bão lịch sử tương tự (DTW + cosine similarity)
│   └── seasonal_forecast.py       # Xây dựng outlook xác suất mùa bão (Poisson + ENSO/SST)
├── scripts/
│   └── process_historical_data.py # Tải & xử lý dữ liệu IBTrACS thành GeoJSON
├── data/
│   ├── storms_vn.geojson          # Dữ liệu bão lịch sử đã xử lý (~13.8 MB)
│   └── climate_scenario_2026.csv  # Kịch bản ENSO/SST cho outlook mùa bão
├── frontend/
│   ├── index.html                  # Trang bản đồ bão lịch sử (route "/")
│   ├── historical_map.html         # Template bản đồ lịch sử
│   ├── dashboard.html              # Dashboard phân tích thống kê
│   ├── seasonal_forecast.html      # Trang outlook mùa bão
│   └── partials/navbar.html        # Thanh điều hướng dùng chung
├── static/css/shared.css          # CSS dùng chung toàn hệ thống
├── tests/
│   └── test_core.py               # 15 test tự động (pytest)
├── docs/                          # Tài liệu demo, kiểm thử, phân tích, mô tả outlook
├── requirements.txt
└── Procfile                       # Lệnh chạy khi triển khai (Railway/Render)
```

## MÔI TRƯỜNG HOẠT ĐỘNG

### Nguồn dữ liệu

| Nguồn | Vai trò | Mô tả |
|---|---|---|
| **IBTrACS v04r01 (NOAA)** | Dữ liệu bão lịch sử | ~2.345 cơn bão, giai đoạn 1884-2026 (143 năm), tải từ [NOAA NCEI IBTrACS](https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/) |
| **IBTrACS NRT** | Dữ liệu near real-time | Bổ sung bão đang hoạt động khi có |
| **JMA (Japan Meteorological Agency)** | Dữ liệu bão hoạt động | Nguồn ưu tiên cho khu vực Tây Bắc Thái Bình Dương |
| **Yagi 2024** (mẫu dự phòng) | Fallback | SID `2024244N09137`, mã JTWC `WP032024`, dùng khi các nguồn ngoài không khả dụng |
| **Kịch bản ENSO/SST 2026** | Đầu vào outlook mùa bão | File `data/climate_scenario_2026.csv` |

### Yêu cầu hệ thống
- Python >= 3.10
- pip
- Kết nối Internet (để tải/cập nhật dữ liệu IBTrACS từ NOAA)

- Sơ đồ luồng dữ liệu tổng quan:
<div align="center">
<img src="/storm_tracker/docs/data_flow_diagram.png" width="700"/>
</div>
<p align="center"><em>Hình 2: Luồng dữ liệu tổng quan của hệ thống</em></p>

## HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY THỬ

### Bước 1: Chuẩn bị môi trường

**Yêu cầu:**
- [Python](https://www.python.org/downloads/) >= 3.10
- Trình duyệt web hiện đại (Chrome, Edge, Firefox)

**Cài đặt:**

```powershell
# Di chuyển vào thư mục dự án
cd storm_tracker

# Tạo môi trường ảo
python -m venv venv
venv\Scripts\activate

# Cài đặt các thư viện phụ thuộc
python -m pip install -r requirements.txt
```

**Các thư viện chính** (`requirements.txt`):
```
flask>=3.0.0
flask-cors>=4.0.0
numpy>=1.26.0
pandas>=2.0.0
pytest>=8.0.0
requests>=2.31.0
gunicorn>=21.2.0
```

### Bước 2: Chuẩn bị dữ liệu lịch sử

Nếu chưa có sẵn `data/storms_vn.geojson`, tạo/cập nhật từ IBTrACS:

```powershell
python scripts/process_historical_data.py

# Ép tải lại dữ liệu mới nhất từ NOAA (bỏ qua cache)
python scripts/process_historical_data.py --force
```

> Khi triển khai, endpoint `/api/historical-storms` chỉ phục vụ GeoJSON đang có sẵn để tránh timeout khi NOAA phản hồi chậm. Muốn cập nhật thủ công khi hệ thống đang chạy, gọi `GET /api/update-historical?force=1`.

### Bước 3: Chạy ứng dụng

```powershell
python app.py
```

Mở các trang sau trên trình duyệt:

| Trang | Địa chỉ |
|---|---|
| Bản đồ bão lịch sử | `http://localhost:5000/` |
| Theo dõi thời gian thực | `http://localhost:5000/realtime` |
| Dashboard phân tích | `http://localhost:5000/dashboard` |
| Outlook mùa bão | `http://localhost:5000/seasonal-forecast` |
| Trạng thái API | `http://localhost:5000/api/status` |

- Screenshot terminal khi server chạy thành công:
<div align="center">
<img src="/storm_tracker/docs/screenshot_server_start.png" width="700"/>
</div>
<p align="center"><em>Hình 3: Server khởi động thành công</em></p>

### Bước 4: Kiểm thử

```powershell
python -m py_compile app.py backend\fetcher.py backend\similarity.py scripts\process_historical_data.py
python -m pytest tests -q -o cache_dir=$env:TEMP\storm_tracker_pytest_cache
```

Checklist kiểm thử chi tiết: `docs/TESTING.md`.

### Bước 5: Triển khai (deploy)

Hệ thống dùng Gunicorn qua `Procfile`, phù hợp triển khai trên Railway hoặc Render:

```
web: gunicorn app:app
```

## NGUYÊN LÝ CƠ BẢN

### 1. Kiến trúc xử lý dữ liệu

Hệ thống hoạt động theo mô hình 3 lớp:

**Lớp thu thập dữ liệu (Data Acquisition)**
- Tải CSV bão lịch sử từ IBTrACS (NOAA), lọc các điểm quỹ đạo trong/gần vùng biển Việt Nam
- Chuyển đổi thành GeoJSON với các thuộc tính chuẩn hóa (`sid`, `name`, `season`, `point_count`, `max_wind_kt`, `max_category`), dữ liệu áp suất được lưu trong `track_points[]`
- Lấy dữ liệu bão đang hoạt động theo thứ tự ưu tiên nguồn (JMA → IBTrACS NRT → fallback Yagi 2024), cache trong bộ nhớ (RAM-only)

**Lớp xử lý và phân tích (Processing & Analytics)**
- Phân loại cấp bão theo tiêu chuẩn Việt Nam (QĐ 18/2021/QĐ-TTg), gán mã màu tương ứng cho từng đoạn quỹ đạo theo cường độ tại thời điểm đó
- Tìm kiếm bão tương tự bằng DTW kết hợp cosine similarity trên vector đặc trưng 9 chiều (trọng số 0.55 / 0.25 / 0.10 / 0.05 / 0.05 cho các nhóm đặc trưng)
- Tính outlook xác suất mùa bão: `khí hậu nền (baseline) × hệ số ENSO × hệ số SST → λ → xác suất Poisson`

**Lớp trình diễn (Presentation)**
- Flask render các trang HTML, frontend gọi API (`/api/...`) để lấy dữ liệu và vẽ lên bản đồ Leaflet.js
- Đường quỹ đạo đổi màu theo cường độ tại từng đoạn thời gian; bão hiện tại và bão lịch sử tương tự được hiển thị đồng thời (2 màu khác nhau) để so sánh trực quan

### 2. Tìm kiếm quỹ đạo tương tự (Similar Trajectory Search)

**Dynamic Time Warping (DTW):**
- So khớp hai chuỗi thời gian (quỹ đạo di chuyển) có độ dài khác nhau, cho phép "co giãn" thời gian để tìm điểm tương đồng tốt nhất giữa hai cơn bão
- Kết hợp với cosine similarity trên vector đặc trưng gồm vị trí, hướng di chuyển, mùa và cường độ cực đại

**Ứng dụng:** trả lời câu hỏi "Cơn bão hiện tại có quỹ đạo giống bão nào trong lịch sử?" - phục vụ cả mục đích nghiên cứu và tham khảo khi theo dõi bão mới

### 3. Mô hình outlook xác suất mùa bão

**Công thức hiệu chỉnh:**
- Hệ số ENSO: `max(0.78, 1.0 − min(max(oni, 0), 2.2) × 0.07)`
- Hệ số SST: `min(1.25, max(0.80, 1.0 + mean_anom × 0.10))`
- Xác suất theo tháng được ước lượng từ phân phối Poisson với tham số λ đã hiệu chỉnh

> **Lưu ý**: đây là mô hình thống kê phục vụ nghiên cứu và demo, không dự báo đường đi, cường độ hay thời điểm của từng cơn bão cụ thể, và không thay thế bản tin của cơ quan khí tượng. Chi tiết xem `docs/SEASONAL_FORECAST.md`.

### 4. Các API chính

| Endpoint | Mô tả |
|---|---|
| `GET /api/status` | Trạng thái các chức năng và cache dữ liệu |
| `GET /api/historical-storms` | GeoJSON bão lịch sử đang có |
| `GET /api/update-historical?force=1` | Cập nhật dữ liệu IBTrACS theo yêu cầu |
| `GET /api/active-storms` | Bão đang hoạt động (hoặc dữ liệu fallback) |
| `GET /api/forecast/<storm_id>` | Quỹ đạo dự báo nếu nguồn dữ liệu có cung cấp |
| `GET /api/similar-storms/<storm_id>` | Danh sách bão lịch sử tương tự nhất |
| `GET /api/dashboard-stats` | Số liệu cho dashboard phân tích |
| `GET /api/seasonal-forecast?year=2026` | Outlook xác suất mùa bão theo tháng |

## KẾT QUẢ

### 1. Thành tựu đạt được

**Hoàn thành đầy đủ 4 module chính của hệ thống**:
- M1: Bản đồ bão lịch sử (quỹ đạo theo cường độ, heatmap, animation, bộ lọc, biểu đồ thống kê)
- M2: Theo dõi bão thời gian thực đa nguồn (JMA → IBTrACS NRT → fallback)
- M3: Tìm kiếm quỹ đạo tương tự bằng DTW kết hợp cosine similarity
- M4: Dashboard phân tích nâng cao (outlook mùa vụ, xu hướng thập kỷ, tần suất theo vùng ven biển)

**Số liệu triển khai:**
- ~3.300 dòng code, 9 API endpoint, 15 test tự động (đều pass)
- Xử lý ~2.345 hệ thống bão, giai đoạn 1884-2026 (143 năm)
- Một số kết quả phân tích nổi bật: tháng đỉnh điểm mùa bão là tháng 9 (487 trường hợp); tỉ lệ bão siêu mạnh (STY) tăng từ 9,9% (trước 2000) lên 21,8% (sau 2000)

**Khả năng mở rộng**:
- Kiến trúc API RESTful thuận lợi cho tích hợp hoặc xây dựng frontend khác trong tương lai
- Cơ chế cache và fallback giúp hệ thống ổn định khi triển khai thực tế (tránh phụ thuộc hoàn toàn vào tính sẵn sàng của NOAA)

### 2. Hướng phát triển tương lai

1. **Dữ liệu**:
   - Bổ sung dữ liệu dự báo chính thức từ Joint Typhoon Warning Center (JTWC) và Trung tâm Dự báo Khí tượng Thủy văn Quốc gia
   - Tích hợp dữ liệu thiệt hại kinh tế - xã hội từ EM-DAT để phân tích tác động thực tế của từng cơn bão

2. **Tính năng**:
   - Tự động hóa lịch cập nhật dữ liệu lịch sử (hiện tại chạy thủ công hoặc qua endpoint)
   - Cảnh báo khi có bão mới hình thành gần vùng biển Việt Nam
   - Mở rộng bộ đặc trưng và tinh chỉnh trọng số cho thuật toán tìm quỹ đạo tương tự

3. **Triển khai**:
   - Đóng gói Docker để triển khai nhất quán trên nhiều môi trường
   - Bổ sung CI/CD (GitHub Actions) chạy tự động test khi có thay đổi
