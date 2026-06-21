# Ke Hoach Kiem Thu

Tai lieu nay gom cac buoc kiem thu can co de doi chieu voi PGNV Noi dung 5: thu nghiem, danh gia do chinh xac, cap nhat du lieu, hieu nang va giao dien.

## 1. Automated Tests

Chay trong thu muc `storm_tracker/`:

```bash
python -m py_compile app.py backend\fetcher.py backend\similarity.py scripts\process_historical_data.py
python -m pytest tests -q -o cache_dir=%TEMP%\storm_tracker_pytest_cache
```

Pham vi test hien co:

- Phan cap bao theo thang Viet Nam.
- DTW/Cosine similarity tra dung `top_k`, khong tra lai chinh target.
- Fallback theo dõi thời gian thực khi nguon that loi.
- API smoke cho ban do lich su, theo doi thoi gian thuc, tim bao tuong tu, dashboard va outlook mua bao.

## 2. API Smoke Test

Khi server local dang chay bang `python app.py`, kiem tra:

| Endpoint | Ket qua mong doi |
| --- | --- |
| `GET /api/status` | HTTP 200, JSON co trang thai cac chuc nang |
| `GET /api/historical-storms` | GeoJSON `FeatureCollection` |
| `GET /api/active-storms` | JSON/GeoJSON co truong `features` |
| `GET /api/forecast/2024231N13138` | Forecast mau Yagi hoac JSON loi co cau truc |
| `GET /api/similar-storms/2024231N13138` | JSON hop le; neu khong co SID thi tra loi co cau truc |
| `GET /api/dashboard-stats` | JSON co summary, decade, month, category, region |
| `GET /api/seasonal-forecast?year=2026` | JSON co `months`, `expected_storms`, xac suat vung |

## 3. Manual Browser Test

Kiem thu tren Chrome va Edge.

### Bản đồ lịch sử - Lich Su Bao

- Mo `/`.
- Loc theo nam den 2026.
- Chuyen Track/Heatmap/Thong ke.
- Click vao bat ky diem nao tren duong di bao.
- Khi chon bao, cac bao khac an di va track duoc giu gradient theo cuong do.
- Nut `X` dong panel va hien lai tat ca bao.
- Danh sach ben trai tu cuon den bao dang chon.

### theo dõi thời gian thực - Thoi Gian Thuc

- Mo `/realtime`.
- Khi khong co bao that, he thong hien fallback Yagi 2024.
- Bam Lam moi, neu nguon that loi thi co thong bao than thien va khong crash.
- Panel chi tiet va duong du bao hien du lieu neu co forecast.

### tìm bão tương tự - Bao Tuong Tu

- Tu ban do lich su, chon mot bao.
- Bam `Tim bao lich su tuong tu `.
- Panel hien top-5, co score tong hop, DTW, Cosine, chenhlech gio, thang.
- Cac duong so sanh hien tren ban do va khong che mat track chinh.

### dashboard phân tích - Dashboard

- Mo `/dashboard`.
- Kiem tra KPI tong so bao, nam du lieu, gio max.
- Kiem tra bieu do theo thap ky, theo thang, theo cap, theo vung.
- Kiem tra top 10 bao manh nhat.

### dự báo mùa - Du Bao Mua Bao 2026

- Mo `/seasonal-forecast`.
- Kiem tra bieu do so con ky vong theo thang.
- Kiem tra bang outlook co ENSO, ONI, vung hinh thanh va vung anh huong.
- Xac nhan ghi chu model thu nghiem hien ro, khong nham voi du bao chinh thuc.
- Xac nhan chi dien giai cac thang chua qua khi demo outlook trong nam 2026.
- Neu cot SST trong, xac nhan giao dien/tai lieu khong khang dinh da co dieu chinh SST thuc te.

## 4. Fallback/Offline Test

- Ngat mang hoac chan nguon JMA/IBTrACS.
- Mo `/realtime`.
- Ket qua mong doi: API `/api/active-storms` van tra du lieu mau Yagi va frontend van hien ban do.

## 5. Performance Check

- Mo `/` voi toan bo 2,343 bao.
- Chuyen heatmap va track.
- Thao tac zoom/pan khong bi treo trinh duyet.
- Neu can ghi so lieu, dung DevTools Performance de chup thoi gian load lan dau.
- Tren Railway, mo `/api/historical-storms` khi GeoJSON qua 7 ngay; endpoint van phai tra 200 tu file dang co, khong doi tai NOAA trong request.

## 6. Ghi Nhan Ket Qua

Khi dua vao bao cao, nen co bang:

| Nhom test | Ket qua | Ghi chu |
| --- | --- | --- |
| Unit/API | Pass | Dinh kem output `pytest` |
| Browser Chrome | Pass/Fail | Ghi loi neu co |
| Browser Edge | Pass/Fail | Ghi loi neu co |
| Fallback offline | Pass/Fail | theo dõi thời gian thực co hien Yagi |
