"""
M3 – Storm Similarity Engine
Thuật toán Dynamic Time Warping (DTW) để tìm các cơn bão lịch sử
có quỹ đạo tương tự với cơn bão đang xem.

Quy trình:
  1. Chuẩn hóa quỹ đạo (resample → dịch về gốc tọa độ)
  2. Pre-filter theo vùng xuất phát (±20° lon, ±15° lat)
  3. Tính DTW distance cho từng cặp
  4. Trả về top-K bão tương đồng nhất kèm % tương đồng
"""
import json, os, math, time
import numpy as np
from typing import Optional

GEOJSON_PATH = os.path.join(os.path.dirname(__file__), 'storms_vn.geojson')
N_RESAMPLE   = 15    # số điểm resample mỗi track
REGION_LON   = 20.0  # ±20° kinh độ pre-filter
REGION_LAT   = 15.0  # ±15° vĩ độ pre-filter

# ── Cache ──────────────────────────────────────────────────────────────────────
_storms_cache   = None
_norm_cache     = {}   # sid → normalized track
_cache_loaded   = False

def _load():
    global _storms_cache, _cache_loaded
    if _cache_loaded:
        return _storms_cache
    if not os.path.exists(GEOJSON_PATH):
        raise FileNotFoundError(f"Chưa có dữ liệu. Chạy: python m1_process_data.py")
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    _storms_cache = data['features']
    _cache_loaded = True
    return _storms_cache

# ── Xử lý quỹ đạo ─────────────────────────────────────────────────────────────
def _resample(coords: list, n: int) -> list:
    """Resample track về đúng n điểm đều nhau."""
    if len(coords) <= 1:
        return coords
    if len(coords) == n:
        return coords
    indices = [round(i * (len(coords) - 1) / (n - 1)) for i in range(n)]
    return [coords[min(i, len(coords)-1)] for i in indices]

def _normalize(coords: list, n: int = N_RESAMPLE) -> Optional[np.ndarray]:
    """
    Chuẩn hóa quỹ đạo:
    - Resample về N_RESAMPLE điểm
    - Dịch về gốc tọa độ (0, 0) → so sánh hình dạng, không phụ thuộc vị trí
    """
    if len(coords) < 3:
        return None
    pts  = _resample(coords, n)
    arr  = np.array(pts, dtype=np.float32)     # shape (n, 2): [[lon, lat], ...]
    arr -= arr[0]                               # dịch về gốc
    return arr

def _first_month(props: dict) -> int:
    for pt in props.get("track_points", []) or []:
        raw = str(pt.get("time", ""))
        if len(raw) >= 7:
            try:
                return int(raw[5:7])
            except ValueError:
                continue
    return 0

def _month_diff(a: int, b: int) -> int:
    if not a or not b:
        return 0
    diff = abs(a - b)
    return min(diff, 12 - diff)

def _track_features(feature: dict) -> Optional[np.ndarray]:
    coords = feature.get("geometry", {}).get("coordinates", [])
    if len(coords) < 3:
        return None

    arr = np.array(coords, dtype=np.float32)
    start = arr[0]
    end = arr[-1]
    delta = end - start
    span = arr.max(axis=0) - arr.min(axis=0)
    centroid = arr.mean(axis=0)
    props = feature.get("properties", {})
    max_wind = float(props.get("max_wind_kt") or 0)
    month = _first_month(props)
    angle = (month / 12.0) * 2 * math.pi if month else 0.0

    return np.array([
        delta[0] / 30.0,
        delta[1] / 20.0,
        span[0] / 40.0,
        span[1] / 25.0,
        centroid[0] / 180.0,
        centroid[1] / 90.0,
        max_wind / 200.0,
        math.sin(angle),
        math.cos(angle),
    ], dtype=np.float32)

def _cosine_score(a: Optional[np.ndarray], b: Optional[np.ndarray]) -> float:
    if a is None or b is None:
        return 50.0
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return 50.0
    cosine = float(np.dot(a, b) / denom)
    cosine = max(-1.0, min(1.0, cosine))
    return round(((cosine + 1.0) / 2.0) * 100.0, 2)

def _distance_deg(a: list, b: list) -> float:
    return round(math.sqrt((float(a[0]) - float(b[0])) ** 2 + (float(a[1]) - float(b[1])) ** 2), 3)

# ── Thuật toán DTW ─────────────────────────────────────────────────────────────
def _dtw(a: np.ndarray, b: np.ndarray) -> float:
    """
    DTW distance giữa 2 quỹ đạo đã chuẩn hóa.
    Sử dụng numpy vectorized để tăng tốc.
    Kết quả được chuẩn hóa theo độ dài để so sánh công bằng.
    """
    n, m = len(a), len(b)
    D = np.full((n + 1, m + 1), np.inf, dtype=np.float32)
    D[0, 0] = 0.0

    for i in range(1, n + 1):
        diff = b - a[i-1]                       # broadcast: (m, 2)
        costs = np.sqrt((diff**2).sum(axis=1))  # Euclidean (m,)
        for j in range(1, m + 1):
            D[i, j] = costs[j-1] + min(D[i-1, j], D[i, j-1], D[i-1, j-1])

    return float(D[n, m]) / (n + m)

# ── API chính ──────────────────────────────────────────────────────────────────
def find_similar(storm_id: str, top_k: int = 5) -> dict:
    """
    Tìm top_k cơn bão lịch sử có quỹ đạo tương tự nhất với storm_id.

    Returns:
        {
          "target": { ... thông tin bão gốc ... },
          "similar": [
            {
              "rank": 1,
              "sid": "...", "name": "...", "season": ...,
              "max_wind_kt": ..., "max_category": {...},
              "similarity_pct": 92,
              "dtw_distance": 1.23,
              "coords": [[lon, lat], ...]
            },
            ...
          ],
          "elapsed_ms": 120
        }
    """
    t0     = time.time()
    storms = _load()

    # Tìm bão mục tiêu
    target = next((f for f in storms if f['properties']['sid'] == storm_id), None)
    if target is None:
        return {"error": f"Không tìm thấy bão: {storm_id}"}

    t_coords = target['geometry']['coordinates']
    t_norm   = _normalize(t_coords)
    if t_norm is None:
        return {"error": "Quỹ đạo bão quá ngắn để so sánh"}

    start_lon, start_lat = t_coords[0]

    # ── Pre-filter theo vùng xuất phát ──────────────────────────────────────
    candidates = []
    for f in storms:
        if f['properties']['sid'] == storm_id:
            continue
        coords = f['geometry']['coordinates']
        if len(coords) < 3:
            continue
        flon, flat = coords[0]
        if abs(flon - start_lon) > REGION_LON or abs(flat - start_lat) > REGION_LAT:
            continue
        norm = _get_norm_cached(f['properties']['sid'], coords)
        if norm is not None:
            candidates.append((f, norm))

    if not candidates:
        return {"error": "Không đủ dữ liệu trong vùng để so sánh", "similar": []}

    target_features = _track_features(target)
    target_month = _first_month(target['properties'])
    target_wind = float(target['properties'].get('max_wind_kt') or 0)

    # ── Tính DTW cho từng candidate ────────────────────────────────────────
    scored = []
    for f, norm in candidates:
        dist = _dtw(t_norm, norm)
        scored.append({"dtw_distance": dist, "feature": f})

    scored.sort(key=lambda x: x["dtw_distance"])

    # ── Tính % tương đồng (0–100) ──────────────────────────────────────────
    # Lấy ngưỡng từ top-30 để chuẩn hóa
    ref_dists  = [s["dtw_distance"] for s in scored[:30]]
    min_d      = scored[0]["dtw_distance"]
    max_d      = ref_dists[-1] if len(ref_dists) > 1 else min_d + 1
    range_d    = max_d - min_d if max_d > min_d else 1.0

    for item in scored:
        f = item["feature"]
        p = f["properties"]
        dist = item["dtw_distance"]
        dtw_score = 100 - ((dist - min_d) / range_d) * 65
        dtw_score = max(35.0, min(100.0, dtw_score))
        cosine_score = _cosine_score(target_features, _track_features(f))
        wind_diff = abs(float(p.get("max_wind_kt") or 0) - target_wind)
        candidate_month = _first_month(p)
        month_diff = _month_diff(target_month, candidate_month)
        start_distance = _distance_deg(t_coords[0], f["geometry"]["coordinates"][0])

        wind_score = max(0.0, 100.0 - min(wind_diff, 100.0))
        month_score = 100.0 - (month_diff / 6.0) * 100.0 if target_month and candidate_month else 70.0
        start_score = max(0.0, 100.0 - min(start_distance * 5.0, 100.0))
        combined = (
            dtw_score * 0.55
            + cosine_score * 0.25
            + wind_score * 0.10
            + month_score * 0.05
            + start_score * 0.05
        )

        item.update({
            "dtw_score": round(dtw_score, 2),
            "cosine_score": round(cosine_score, 2),
            "wind_diff_kt": round(wind_diff, 1),
            "month_diff": month_diff,
            "start_distance_deg": start_distance,
            "combined_score": round(combined, 2),
        })

    scored.sort(key=lambda x: (-x["combined_score"], x["dtw_distance"]))
    top = scored[:top_k]

    similar = []
    for rank, item in enumerate(top, 1):
        f = item["feature"]
        p = f['properties']
        sim_pct = round(item["combined_score"])
        sim_pct = max(35, min(100, sim_pct))
        similar.append({
            "rank":          rank,
            "sid":           p['sid'],
            "name":          p['name'],
            "season":        p['season'],
            "max_wind_kt":   p.get('max_wind_kt', 0),
            "max_category":  p.get('max_category', {}),
            "similarity_pct": sim_pct,
            "dtw_distance":  round(item["dtw_distance"], 4),
            "combined_score": item["combined_score"],
            "dtw_score": item["dtw_score"],
            "cosine_score": item["cosine_score"],
            "wind_diff_kt": item["wind_diff_kt"],
            "month_diff": item["month_diff"],
            "start_distance_deg": item["start_distance_deg"],
            "coords":        f['geometry']['coordinates'],
        })

    tp = target['properties']
    return {
        "target": {
            "sid":         tp['sid'],
            "name":        tp['name'],
            "season":      tp['season'],
            "max_wind_kt": tp.get('max_wind_kt', 0),
            "max_category": tp.get('max_category', {}),
            "coords":      t_coords,
        },
        "similar":      similar,
        "candidate_count": len(candidates),
        "elapsed_ms":   round((time.time() - t0) * 1000),
    }

def _get_norm_cached(sid: str, coords: list) -> Optional[np.ndarray]:
    if sid not in _norm_cache:
        _norm_cache[sid] = _normalize(coords)
    return _norm_cache[sid]
