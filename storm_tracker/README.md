# 🌀 Storm Tracker – Module M2: Theo dõi Bão Thời Gian Thực

## Cấu trúc thư mục

```
storm_tracker/
├── app.py                  # Flask server chính
├── requirements.txt        # Các thư viện cần cài
├── data/
│   ├── __init__.py
│   └── fetcher.py          # Lấy dữ liệu từ JTWC qua tropycal
└── templates/
    └── index.html          # Giao diện bản đồ
```

## Cài đặt

```bash
# 1. Tạo môi trường ảo (khuyến nghị)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Chạy server
python app.py
```

Mở trình duyệt: **http://localhost:5000**

---

## Chạy test

```bash
pytest
```

## Deploy nhanh Render/Railway

- Root directory: `storm_tracker`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Health/smoke URL: `/api/status`

---

## Tính năng M2

| Tính năng | Mô tả |
|-----------|-------|
| 🌀 Bão hiện tại | Danh sách + icon nhấp nháy trên bản đồ |
| 🎨 Gradient cường độ | Mỗi đoạn track đổi màu theo sức gió |
| 📡 Dự báo 5 ngày | Đường dự báo JTWC (nét đứt) |
| 🔄 Tự động làm mới | Cập nhật mỗi 6 giờ |
| 📊 Phân cấp Việt Nam | Theo QĐ 18/2021/QĐ-TTg |

## Nguồn dữ liệu

- **JTWC** (Joint Typhoon Warning Center) – dữ liệu thực tế + dự báo
- Truy cập qua thư viện **tropycal** (Python)
- Fallback: dữ liệu mẫu bão Yagi 2024 khi không có internet

## API Endpoints

| Endpoint | Mô tả |
|----------|-------|
| `GET /api/active-storms` | GeoJSON tất cả bão đang hoạt động |
| `GET /api/forecast/<id>` | Dự báo 5 ngày của 1 cơn bão |
| `GET /api/storm/<id>` | Chi tiết 1 cơn bão |
| `GET /api/status` | Trạng thái hệ thống + thời gian cập nhật |

## Tích hợp với GR2

Thêm link sang module lịch sử (GR2) trong `index.html`:
```html
<a href="/historical">📚 Xem lịch sử bão</a>
```

Và thêm route trong `app.py`:
```python
@app.route('/historical')
def historical():
    return render_template('historical.html')  # file từ GR2
```
