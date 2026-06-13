"""Similarity engine for historical storm tracks."""

import json
import math
import os
import time
from typing import Optional

import numpy as np


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON_PATH = os.path.join(BASE_DIR, "data", "storms_vn.geojson")
N_RESAMPLE = 15
REGION_LON = 20.0
REGION_LAT = 15.0

_storms_cache = None
_norm_cache = {}
_cache_loaded = False


def clear_cache():
    global _storms_cache, _cache_loaded
    _storms_cache = None
    _cache_loaded = False
    _norm_cache.clear()


def _load():
    global _storms_cache, _cache_loaded
    if _cache_loaded:
        return _storms_cache
    if not os.path.exists(GEOJSON_PATH):
        raise FileNotFoundError("Chua co du lieu lich su. Chay: python scripts/m1_process_data.py")
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        _storms_cache = json.load(f)["features"]
    _cache_loaded = True
    return _storms_cache


def _resample(coords: list, n: int) -> list:
    if len(coords) <= 1 or len(coords) == n:
        return coords
    indices = [round(i * (len(coords) - 1) / (n - 1)) for i in range(n)]
    return [coords[min(i, len(coords) - 1)] for i in indices]


def _normalize(coords: list, n: int = N_RESAMPLE) -> Optional[np.ndarray]:
    """Resample a track and shift it to the origin for shape comparison."""
    if len(coords) < 3:
        return None
    arr = np.array(_resample(coords, n), dtype=np.float32)
    arr -= arr[0]
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
    cosine = max(-1.0, min(1.0, float(np.dot(a, b) / denom)))
    return round(((cosine + 1.0) / 2.0) * 100.0, 2)


def _distance_deg(a: list, b: list) -> float:
    return round(math.sqrt((float(a[0]) - float(b[0])) ** 2 + (float(a[1]) - float(b[1])) ** 2), 3)


def _dtw(a: np.ndarray, b: np.ndarray) -> float:
    """Dynamic Time Warping distance normalized by track length."""
    n, m = len(a), len(b)
    distances = np.full((n + 1, m + 1), np.inf, dtype=np.float32)
    distances[0, 0] = 0.0

    for i in range(1, n + 1):
        diff = b - a[i - 1]
        costs = np.sqrt((diff**2).sum(axis=1))
        for j in range(1, m + 1):
            distances[i, j] = costs[j - 1] + min(
                distances[i - 1, j],
                distances[i, j - 1],
                distances[i - 1, j - 1],
            )

    return float(distances[n, m]) / (n + m)


def _get_norm_cached(sid: str, coords: list) -> Optional[np.ndarray]:
    if sid not in _norm_cache:
        _norm_cache[sid] = _normalize(coords)
    return _norm_cache[sid]


def find_similar(storm_id: str, top_k: int = 5) -> dict:
    """Return top-k historical storms most similar to the target storm."""
    start_time = time.time()
    storms = _load()

    target = next((f for f in storms if f["properties"]["sid"] == storm_id), None)
    if target is None:
        return {"error": f"Khong tim thay bao: {storm_id}"}

    target_coords = target["geometry"]["coordinates"]
    target_norm = _normalize(target_coords)
    if target_norm is None:
        return {"error": "Quy dao bao qua ngan de so sanh"}

    start_lon, start_lat = target_coords[0]
    candidates = []
    for feature in storms:
        props = feature["properties"]
        if props["sid"] == storm_id:
            continue
        coords = feature["geometry"]["coordinates"]
        if len(coords) < 3:
            continue
        lon, lat = coords[0]
        if abs(lon - start_lon) > REGION_LON or abs(lat - start_lat) > REGION_LAT:
            continue
        norm = _get_norm_cached(props["sid"], coords)
        if norm is not None:
            candidates.append((feature, norm))

    if not candidates:
        return {"error": "Khong du du lieu trong vung de so sanh", "similar": []}

    target_features = _track_features(target)
    target_month = _first_month(target["properties"])
    target_wind = float(target["properties"].get("max_wind_kt") or 0)

    scored = []
    for feature, norm in candidates:
        scored.append({"dtw_distance": _dtw(target_norm, norm), "feature": feature})
    scored.sort(key=lambda x: x["dtw_distance"])

    ref_distances = [s["dtw_distance"] for s in scored[:30]]
    min_distance = scored[0]["dtw_distance"]
    max_distance = ref_distances[-1] if len(ref_distances) > 1 else min_distance + 1
    distance_range = max_distance - min_distance if max_distance > min_distance else 1.0

    for item in scored:
        feature = item["feature"]
        props = feature["properties"]
        dtw_score = 100 - ((item["dtw_distance"] - min_distance) / distance_range) * 65
        dtw_score = max(35.0, min(100.0, dtw_score))
        cosine_score = _cosine_score(target_features, _track_features(feature))
        wind_diff = abs(float(props.get("max_wind_kt") or 0) - target_wind)
        month_diff = _month_diff(target_month, _first_month(props))
        start_distance = _distance_deg(target_coords[0], feature["geometry"]["coordinates"][0])

        wind_score = max(0.0, 100.0 - min(wind_diff, 100.0))
        month_score = 100.0 - (month_diff / 6.0) * 100.0 if target_month else 70.0
        start_score = max(0.0, 100.0 - min(start_distance * 5.0, 100.0))
        combined = (
            dtw_score * 0.55
            + cosine_score * 0.25
            + wind_score * 0.10
            + month_score * 0.05
            + start_score * 0.05
        )

        item.update({
            "combined_score": round(combined, 2),
            "dtw_score": round(dtw_score, 2),
            "cosine_score": round(cosine_score, 2),
            "wind_diff_kt": round(wind_diff, 1),
            "month_diff": month_diff,
            "start_distance_deg": start_distance,
        })

    scored.sort(key=lambda x: (-x["combined_score"], x["dtw_distance"]))

    similar = []
    for rank, item in enumerate(scored[:top_k], 1):
        feature = item["feature"]
        props = feature["properties"]
        similar.append({
            "rank": rank,
            "sid": props["sid"],
            "name": props["name"],
            "season": props["season"],
            "max_wind_kt": props.get("max_wind_kt", 0),
            "max_category": props.get("max_category", {}),
            "similarity_pct": max(35, min(100, round(item["combined_score"]))),
            "dtw_distance": round(item["dtw_distance"], 4),
            "combined_score": item["combined_score"],
            "dtw_score": item["dtw_score"],
            "cosine_score": item["cosine_score"],
            "wind_diff_kt": item["wind_diff_kt"],
            "month_diff": item["month_diff"],
            "start_distance_deg": item["start_distance_deg"],
            "coords": feature["geometry"]["coordinates"],
        })

    props = target["properties"]
    return {
        "target": {
            "sid": props["sid"],
            "name": props["name"],
            "season": props["season"],
            "max_wind_kt": props.get("max_wind_kt", 0),
            "max_category": props.get("max_category", {}),
            "coords": target_coords,
        },
        "similar": similar,
        "candidate_count": len(candidates),
        "elapsed_ms": round((time.time() - start_time) * 1000),
    }
