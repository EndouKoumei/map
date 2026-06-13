"""
M1 Data Processor – IBTrACS → GeoJSON nâng cao
Tích hợp cơ chế tự động tải dữ liệu từ NOAA (kế thừa từ GR2 - StormDataProcessor).

Quy trình:
  1. Kiểm tra cache cục bộ (data_cache/) → nếu còn mới (< 7 ngày) thì dùng lại
  2. Nếu không có hoặc đã cũ → tự động tải từ NOAA qua requests
  3. Xử lý CSV → GeoJSON nâng cao (cường độ từng điểm, phục vụ gradient màu)

Sử dụng:
    python m1_process_data.py              # tự tải từ NOAA nếu cần
    python m1_process_data.py --force      # bắt buộc tải lại dù cache còn mới
    python m1_process_data.py --input path/to/ibtracs.WP.list.v04r01.csv  # dùng file sẵn có
"""
import pandas as pd
import json, argparse, os, sys, time, requests
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NOAA_URL    = ("https://www.ncei.noaa.gov/data/international-best-track-archive-"
               "for-climate-stewardship-ibtracs/v04r01/access/csv/"
               "ibtracs.WP.list.v04r01.csv")
CACHE_DIR   = os.path.join(BASE_DIR, "data_cache")
CACHE_FILE  = os.path.join(CACHE_DIR, "ibtracs.WP.list.v04r01.csv")
CACHE_DAYS  = 7          # cache hợp lệ trong 7 ngày (NOAA cập nhật theo tuần)
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "data", "storms_vn.geojson")

LAT_MIN, LAT_MAX = 5.0,  25.0
LON_MIN, LON_MAX = 100.0, 125.0


# CƠ CHẾ TỰ TẢI VÀ CACHE – kế thừa từ GR2 (StormDataProcessor)
def is_cache_valid() -> bool:
    """Kiểm tra cache còn hợp lệ không (tồn tại + chưa quá CACHE_DAYS ngày)."""
    if not os.path.exists(CACHE_FILE):
        return False
    age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
    return age < timedelta(days=CACHE_DAYS)


def download_from_noaa(force: bool = False) -> str:
    """
    Tải file CSV từ NOAA về cache cục bộ.
    - Nếu cache còn mới và force=False → dùng lại, không tải lại.
    - Trả về đường dẫn tới file CSV.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    if not force and is_cache_valid():
        age_h = (datetime.now() - datetime.fromtimestamp(
                     os.path.getmtime(CACHE_FILE))).total_seconds() / 3600
        print(f"   Dùng cache cục bộ ({age_h:.0f}h trước) → {CACHE_FILE}")
        return CACHE_FILE

    action = "Cập nhật" if os.path.exists(CACHE_FILE) else "Tải mới"
    print(f"  → {action} dữ liệu từ NOAA...")
    print(f"  URL: {NOAA_URL}")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Storm Tracker DATN/1.0)'}
        resp = requests.get(NOAA_URL, headers=headers, stream=True, timeout=120)
        resp.raise_for_status()

        total = int(resp.headers.get('content-length', 0))
        downloaded = 0
        chunk_size  = 1024 * 256   # 256 KB

        with open(CACHE_FILE, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        mb  = downloaded / 1024 / 1024
                        print(f"\r  Đã tải: {mb:.1f} MB ({pct:.0f}%)", end='', flush=True)
        print(f"\n   Tải xong → {CACHE_FILE} ({downloaded/1024/1024:.1f} MB)")
        return CACHE_FILE

    except requests.exceptions.ConnectionError:
        print("   Không kết nối được NOAA (kiểm tra internet)")
        if os.path.exists(CACHE_FILE):
            print(f"  → Dùng cache cũ: {CACHE_FILE}")
            return CACHE_FILE
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("   Timeout khi tải – thử lại sau hoặc tải thủ công")
        if os.path.exists(CACHE_FILE):
            return CACHE_FILE
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"   Lỗi HTTP: {e}")
        if os.path.exists(CACHE_FILE):
            return CACHE_FILE
        sys.exit(1)

VN_CATS = [
    {"code": "TD",  "name": "Áp thấp nhiệt đới", "min_kt": 0,  "max_kt": 33,  "color": "#6EC1EA"},
    {"code": "TS",  "name": "Bão (bão thường)",   "min_kt": 34, "max_kt": 47,  "color": "#4DFFFF"},
    {"code": "STS", "name": "Bão mạnh",           "min_kt": 48, "max_kt": 63,  "color": "#C0FFC0"},
    {"code": "TY",  "name": "Bão rất mạnh",       "min_kt": 64, "max_kt": 98,  "color": "#FF738A"},
    {"code": "STY", "name": "Siêu bão",           "min_kt": 99, "max_kt": 999, "color": "#A188FC"},
]

def classify(wind_kt):
    w = float(wind_kt) if wind_kt and str(wind_kt).strip() not in ['', ' '] else 0
    for cat in VN_CATS:
        if w <= cat["max_kt"]:
            return cat
    return VN_CATS[-1]

def safe_float(v, default=None):
    try:
        f = float(v)
        return f if f == f else default   # NaN check
    except (ValueError, TypeError):
        return default

def process(input_csv: str, output_json: str):
    print(f"[1/5] Đọc file: {input_csv}")
    if not os.path.exists(input_csv):
        print(f"   Không tìm thấy file: {input_csv}")
        print("  Tải dữ liệu từ: https://www.ncei.noaa.gov/data/international-best-track-archive-"
              "for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.WP.list.v04r01.csv")
        sys.exit(1)

    # Dòng 0 = header, dòng 1 = đơn vị → skiprows=[1]
    df = pd.read_csv(input_csv, skiprows=[1], low_memory=False)
    df.columns = df.columns.str.strip()
    print(f"   Tổng số hàng: {len(df):,}")

    cols = ['SID', 'SEASON', 'NAME', 'ISO_TIME', 'LAT', 'LON', 'WMO_WIND', 'WMO_PRES']
    # Thêm USA_WIND nếu có (dữ liệu tốt hơn WMO_WIND)
    if 'USA_WIND' in df.columns:
        cols.append('USA_WIND')
    if 'USA_PRES' in df.columns:
        cols.append('USA_PRES')
    df = df[[c for c in cols if c in df.columns]].copy()

    print("[2/5] Lọc tọa độ vùng biển Việt Nam...")
    df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
    df['LON'] = pd.to_numeric(df['LON'], errors='coerce')
    df = df.dropna(subset=['LAT', 'LON'])
    df = df[(df['LAT'] >= LAT_MIN) & (df['LAT'] <= LAT_MAX) &
            (df['LON'] >= LON_MIN) & (df['LON'] <= LON_MAX)]
    print(f"   Số hàng sau lọc: {len(df):,}")

    # Ưu tiên USA_WIND (thường đầy đủ hơn WMO_WIND với WP basin)
    if 'USA_WIND' in df.columns:
        df['WIND_KT'] = pd.to_numeric(df['USA_WIND'], errors='coerce').fillna(
                        pd.to_numeric(df['WMO_WIND'], errors='coerce')).fillna(0)
    else:
        df['WIND_KT'] = pd.to_numeric(df['WMO_WIND'], errors='coerce').fillna(0)

    if 'USA_PRES' in df.columns:
        df['PRES_MB'] = pd.to_numeric(df['USA_PRES'], errors='coerce').fillna(
                        pd.to_numeric(df['WMO_PRES'], errors='coerce')).fillna(0)
    else:
        df['PRES_MB'] = pd.to_numeric(df['WMO_PRES'], errors='coerce').fillna(0)

    df = df.sort_values(['SID', 'ISO_TIME'])

    print("[3/5] Gom nhóm và tạo GeoJSON...")
    groups  = df.groupby('SID')
    features = []

    for sid, grp in groups:
        pts = grp.reset_index(drop=True)
        if len(pts) < 2:
            continue

        coords       = [[safe_float(r['LON']), safe_float(r['LAT'])]   for _, r in pts.iterrows()]
        wind_series  = [safe_float(r['WIND_KT'], 0)                    for _, r in pts.iterrows()]
        pres_series  = [safe_float(r['PRES_MB'], 0)                    for _, r in pts.iterrows()]
        times        = [str(r['ISO_TIME'])                              for _, r in pts.iterrows()]

        # Bỏ tọa độ None
        valid = [(c, w, p, t) for c, w, p, t in zip(coords, wind_series, pres_series, times)
                 if c[0] is not None and c[1] is not None]
        if len(valid) < 2:
            continue

        coords, wind_series, pres_series, times = zip(*valid)
        coords, wind_series, pres_series, times = list(coords), list(wind_series), list(pres_series), list(times)

        max_wind    = max(wind_series)
        max_cat     = classify(max_wind)
        season      = int(pts['SEASON'].iloc[0]) if 'SEASON' in pts else 0
        name        = str(pts['NAME'].iloc[0]).strip()
        if name in ('NOT_NAMED', 'UNNAMED', ''):
            name = f"Không tên ({season})"

        feature = {
            "type": "Feature",
            "properties": {
                "sid":          sid,
                "name":         name,
                "season":       season,
                "point_count":  len(coords),
                "max_wind_kt":  max_wind,
                "max_category": max_cat,
                # Dữ liệu từng điểm – dùng cho gradient màu & animation
                "track_points": [
                    {
                        "lat":      coords[i][1],
                        "lon":      coords[i][0],
                        "wind_kt":  wind_series[i],
                        "pres_mb":  pres_series[i],
                        "time":     times[i],
                        "category": classify(wind_series[i]),
                    }
                    for i in range(len(coords))
                ],
            },
            "geometry": {
                "type":        "LineString",
                "coordinates": coords,
            },
        }
        features.append(feature)

    print("[4/5] Tính toán thống kê...")
    years  = sorted(set(f["properties"]["season"] for f in features if f["properties"]["season"] > 0))
    by_year = {}
    for f in features:
        y = f["properties"]["season"]
        if y not in by_year:
            by_year[y] = {"total": 0, "TD": 0, "TS": 0, "STS": 0, "TY": 0, "STY": 0}
        by_year[y]["total"] += 1
        by_year[y][f["properties"]["max_category"]["code"]] += 1

    by_month = {str(m): 0 for m in range(1, 13)}
    for f in features:
        for pt in f["properties"]["track_points"]:
            try:
                mo = str(datetime.strptime(pt["time"][:10], "%Y-%m-%d").month)
                by_month[mo] += 1
            except Exception:
                pass

    geojson = {
        "type":          "FeatureCollection",
        "generated_at":  datetime.now().isoformat(),
        "source":        "IBTrACS v04r01 (NOAA)",
        "storm_count":   len(features),
        "year_range":    [min(years) if years else 0, max(years) if years else 0],
        "stats": {
            "by_year":  by_year,
            "by_month": by_month,
        },
        "features": features,
    }

    print(f"[5/5] Ghi file: {output_json}")
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(output_json) / 1024 / 1024
    print(f"\n Hoàn thành!")
    print(f"   Số cơn bão: {len(features):,}")
    print(f"   Giai đoạn:  {geojson['year_range'][0]} – {geojson['year_range'][1]}")
    print(f"   File size:  {size_mb:.1f} MB → {output_json}")
    return output_json


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='M1 Data Processor – Tự tải IBTrACS từ NOAA và tạo GeoJSON nâng cao')
    parser.add_argument('--input',  default=None,
                        help='(Tuỳ chọn) Dùng file CSV sẵn có thay vì tải từ NOAA')
    parser.add_argument('--output', default=DEFAULT_OUTPUT,
                        help='Đường dẫn output GeoJSON (mặc định: data/storms_vn.geojson)')
    parser.add_argument('--force',  action='store_true',
                        help='Bắt buộc tải lại từ NOAA dù cache còn mới')
    args = parser.parse_args()

    if args.input:
        # Người dùng chỉ định file thủ công (tương thích ngược với GR2)
        csv_path = args.input
        print(f"[0/5] Dùng file chỉ định: {csv_path}")
    else:
        # Tự động tải từ NOAA với cache (cơ chế từ GR2)
        print("[0/5] Kiểm tra / tải dữ liệu từ NOAA IBTrACS...")
        csv_path = download_from_noaa(force=args.force)

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)
    process(csv_path, args.output)
