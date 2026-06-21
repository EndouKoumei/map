# Storm Tracker VN

WebGIS tra cuu lich su bao, theo doi bao gan thoi gian thuc, tim quy dao tuong tu,
phan tich thong ke va xem outlook xac suat mua bao cho khu vuc Viet Nam.

## Chuc Nang

| Chuc nang | Duong dan | Mo ta |
| --- | --- | --- |
| Ban do lich su | `/` | Loc du lieu, quy dao theo cuong do, heatmap, animation va thong tin bao. |
| Theo doi thoi gian thuc | `/realtime` | Du lieu JMA/IBTrACS NRT va fallback Yagi 2024 khi nguon ngoai khong san sang. |
| Tim bao tuong tu | Trong ban do lich su | DTW ket hop diem huong di, vi tri, mua bao va gio cuc dai. |
| Dashboard phan tich | `/dashboard` | Xu huong theo thap ky, mua vu, phan cap va vung anh huong gan Viet Nam. |
| Outlook mua bao | `/seasonal-forecast` | Uoc luong xac suat theo thang tu lich su va kich ban ENSO/SST. |

## Cau Truc Thu Muc

```text
storm_tracker/
|-- app.py                  # Flask routes va API
|-- backend/                # Xu ly realtime, tuong tu va outlook mua bao
|-- data/                   # GeoJSON lich su va kich ban khi hau
|-- frontend/               # HTML, CSS va JavaScript
|-- scripts/                # Xu ly/cap nhat du lieu lich su
|-- tests/                  # Pytest
|-- docs/                   # Tai lieu demo, kiem thu va phan tich
|-- requirements.txt
`-- Procfile                # Lenh chay tren Railway/Render
```

## Chay Local

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Mo cac trang:

- Ban do lich su: `http://localhost:5000/`
- Theo doi thoi gian thuc: `http://localhost:5000/realtime`
- Dashboard: `http://localhost:5000/dashboard`
- Outlook mua bao: `http://localhost:5000/seasonal-forecast`
- Trang thai API: `http://localhost:5000/api/status`

## Du Lieu Lich Su

Tao hoac cap nhat GeoJSON tu IBTrACS/NOAA:

```powershell
python scripts/process_historical_data.py
python scripts/process_historical_data.py --force
```

Tep dau ra mac dinh la `data/storms_vn.geojson`.

Khi deploy, `/api/historical-storms` chi phuc vu GeoJSON dang co. Cach nay tranh
timeout khi NOAA cham hoac khong truy cap duoc. Chi goi cap nhat chu dong khi can:

```text
GET /api/update-historical?force=1
```

## Kiem Thu

```powershell
python -m py_compile app.py backend\fetcher.py backend\similarity.py scripts\process_historical_data.py
python -m pytest tests -q -o cache_dir=$env:TEMP\storm_tracker_pytest_cache
```

Checklist chi tiet: [docs/TESTING.md](docs/TESTING.md).

## API Chinh

| Endpoint | Mo ta |
| --- | --- |
| `GET /api/status` | Trang thai cac chuc nang va cache du lieu. |
| `GET /api/historical-storms` | GeoJSON bao lich su dang co. |
| `GET /api/update-historical?force=1` | Cap nhat IBTrACS theo yeu cau. |
| `GET /api/active-storms` | Bao dang hoat dong hoac fallback. |
| `GET /api/forecast/<storm_id>` | Quy dao du bao neu nguon co cung cap. |
| `GET /api/similar-storms/<storm_id>` | Top bao lich su tuong tu. |
| `GET /api/dashboard-stats` | So lieu dashboard phan tich. |
| `GET /api/seasonal-forecast?year=2026` | Outlook xac suat mua bao theo thang. |

## Luu Y Ve Outlook Mua Bao

Outlook mua bao la model thong ke phuc vu nghien cuu va demo. No khong du bao
duong di, cuong do hay thoi diem cua tung con bao, va khong thay the ban tin cua co
quan khi tuong. Xem [docs/SEASONAL_FORECAST.md](docs/SEASONAL_FORECAST.md) de biet
data dau vao, cach dien giai va gioi han.

## Tai Lieu Ho Tro

- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md): kich ban demo 10-15 phut.
- [docs/REPORT_FINDINGS.md](docs/REPORT_FINDINGS.md): ket qua phan tich lich su.
- [docs/TESTING.md](docs/TESTING.md): ke hoach kiem thu.
- [docs/SEASONAL_FORECAST.md](docs/SEASONAL_FORECAST.md): mo ta outlook mua bao.
