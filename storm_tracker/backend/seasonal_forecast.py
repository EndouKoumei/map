"""Simple seasonal storm outlook model for the 2026 typhoon season."""

import csv
import json
import math
import os
from collections import defaultdict


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GEOJSON = os.path.join(BASE_DIR, "data", "storms_vn.geojson")
DEFAULT_CLIMATE = os.path.join(BASE_DIR, "data", "climate_scenario_2026.csv")

GENESIS_REGIONS = {
    "bien_dong": "Biển Đông",
    "philippines": "Vùng biển Philippines",
    "other_wp": "Tây Bắc Thái Bình Dương khác",
}

LANDFALL_REGIONS = {
    "bac_bo": "Bắc Bộ",
    "trung_bo": "Trung Bộ",
    "nam_bo": "Nam Bộ",
    "no_vn": "Không vào vùng ven biển VN",
}


def _safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_features(path=DEFAULT_GEOJSON):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("features", [])


def _load_climate(year=2026, path=DEFAULT_CLIMATE):
    rows = {}
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if int(row.get("year") or 0) != year:
                continue
            month = int(row.get("month") or 0)
            rows[month] = {
                "year": year,
                "month": month,
                "enso_phase": row.get("enso_phase") or "Neutral",
                "oni": _safe_float(row.get("oni")),
                "very_strong_el_nino_probability": _safe_float(row.get("very_strong_el_nino_probability")),
                "sst_scs_anom_c": _safe_float(row.get("sst_scs_anom_c")),
                "sst_phil_anom_c": _safe_float(row.get("sst_phil_anom_c")),
                "source_note": row.get("source_note") or "",
            }
    return rows


def _first_track_point(feature):
    props = feature.get("properties", {})
    points = props.get("track_points") or []
    if points:
        return points[0]
    coords = feature.get("geometry", {}).get("coordinates") or []
    if coords:
        lon, lat = coords[0]
        return {"lat": lat, "lon": lon, "time": ""}
    return None


def _storm_month(feature):
    pt = _first_track_point(feature)
    raw_time = str((pt or {}).get("time") or "")
    if len(raw_time) >= 7:
        try:
            return int(raw_time[5:7])
        except ValueError:
            pass
    return None


def _genesis_region(lat, lon):
    if 5.0 <= lat <= 23.0 and 105.0 <= lon <= 120.0:
        return "bien_dong"
    if 5.0 <= lat <= 25.0 and 120.0 < lon <= 150.0:
        return "philippines"
    return "other_wp"


def _landfall_region(track_points):
    hits = []
    for pt in track_points or []:
        lat = pt.get("lat")
        lon = pt.get("lon")
        if lat is None or lon is None:
            continue
        lat = _safe_float(lat)
        lon = _safe_float(lon)
        if 8.0 <= lat <= 24.5 and 102.0 <= lon <= 116.5:
            hits.append(lat)
    if not hits:
        return "no_vn"
    avg_lat = sum(hits) / len(hits)
    if avg_lat >= 18.0:
        return "bac_bo"
    if avg_lat >= 12.0:
        return "trung_bo"
    return "nam_bo"


def _build_training_rows(features, start_year=1981, end_year=2025):
    rows = {(year, month): {
        "storm_count": 0,
        "genesis": defaultdict(int),
        "landfall": defaultdict(int),
    } for year in range(start_year, end_year + 1) for month in range(1, 13)}

    for feature in features:
        props = feature.get("properties", {})
        year = int(props.get("season") or 0)
        month = _storm_month(feature)
        if not (start_year <= year <= end_year and month):
            continue

        first = _first_track_point(feature)
        lat = _safe_float(first.get("lat"))
        lon = _safe_float(first.get("lon"))
        key = (year, month)
        rows[key]["storm_count"] += 1
        rows[key]["genesis"][_genesis_region(lat, lon)] += 1
        rows[key]["landfall"][_landfall_region(props.get("track_points") or [])] += 1

    return rows


def _poisson_probs(lam):
    lam = max(0.05, float(lam))
    p0 = math.exp(-lam)
    p1 = p0 * lam
    p2 = p1 * lam / 2.0
    p3plus = max(0.0, 1.0 - p0 - p1 - p2)
    return {
        "0": round(p0, 3),
        "1": round(p1, 3),
        "2": round(p2, 3),
        "3+": round(p3plus, 3),
    }


def _normalize(weights):
    total = sum(max(0.0, v) for v in weights.values())
    if total <= 0:
        n = len(weights) or 1
        return {k: round(1.0 / n, 3) for k in weights}
    return {k: round(max(0.0, v) / total, 3) for k, v in weights.items()}


def _monthly_base(rows, month):
    monthly = [row for (year, mo), row in rows.items() if mo == month]
    count_mean = sum(r["storm_count"] for r in monthly) / max(1, len(monthly))

    genesis = {k: 1.0 for k in GENESIS_REGIONS}
    landfall = {k: 1.0 for k in LANDFALL_REGIONS}
    for row in monthly:
        for key, value in row["genesis"].items():
            genesis[key] += value
        for key, value in row["landfall"].items():
            landfall[key] += value

    return count_mean, _normalize(genesis), _normalize(landfall)


def _enso_count_factor(climate):
    phase = (climate.get("enso_phase") or "").lower()
    oni = climate.get("oni", 0.0)
    if "nino" not in phase:
        return 1.0
    # El Nino often shifts WNP activity eastward; keep count adjustment conservative.
    return max(0.78, 1.0 - min(max(oni, 0.0), 2.2) * 0.07)


def _sst_count_factor(climate):
    scs = climate.get("sst_scs_anom_c", 0.0)
    phil = climate.get("sst_phil_anom_c", 0.0)
    mean_anom = (scs + phil) / 2.0
    return min(1.25, max(0.80, 1.0 + mean_anom * 0.10))


def _adjust_genesis(base, climate):
    phase = (climate.get("enso_phase") or "").lower()
    gradient = climate.get("sst_phil_anom_c", 0.0) - climate.get("sst_scs_anom_c", 0.0)
    weights = dict(base)
    if "nino" in phase:
        weights["philippines"] *= 1.20
        weights["bien_dong"] *= 0.88
    weights["philippines"] *= 1.0 + max(-0.25, min(0.35, gradient * 0.20))
    weights["bien_dong"] *= 1.0 - max(-0.20, min(0.25, gradient * 0.12))
    return _normalize(weights)


def _adjust_landfall(base, climate):
    phase = (climate.get("enso_phase") or "").lower()
    weights = dict(base)
    if "nino" in phase:
        weights["no_vn"] *= 1.12
        weights["nam_bo"] *= 0.92
        weights["trung_bo"] *= 0.96
    return _normalize(weights)


def build_seasonal_forecast(year=2026, features=None, climate_rows=None):
    """Build a month-by-month probabilistic outlook for the given year."""
    features = features if features is not None else _load_features()
    climate_rows = climate_rows if climate_rows is not None else _load_climate(year)
    training = _build_training_rows(features)

    months = []
    for month in range(1, 13):
        climate = climate_rows.get(month, {
            "year": year,
            "month": month,
            "enso_phase": "Neutral",
            "oni": 0.0,
            "very_strong_el_nino_probability": 0.0,
            "sst_scs_anom_c": 0.0,
            "sst_phil_anom_c": 0.0,
            "source_note": "No climate scenario row; neutral fallback.",
        })
        base_count, base_genesis, base_landfall = _monthly_base(training, month)
        expected_count = base_count * _enso_count_factor(climate) * _sst_count_factor(climate)
        genesis_probs = _adjust_genesis(base_genesis, climate)
        landfall_probs = _adjust_landfall(base_landfall, climate)

        months.append({
            "month": month,
            "expected_storms": round(expected_count, 2),
            "count_probabilities": _poisson_probs(expected_count),
            "genesis_region_probabilities": {
                key: {"label": GENESIS_REGIONS[key], "probability": value}
                for key, value in genesis_probs.items()
            },
            "landfall_region_probabilities": {
                key: {"label": LANDFALL_REGIONS[key], "probability": value}
                for key, value in landfall_probs.items()
            },
            "climate": climate,
        })

    return {
        "year": year,
        "method": "historical_climatology_plus_enso_sst_scenario_v1",
        "training_period": "1981-2025",
        "sources": [
            "IBTrACS/NOAA historical tracks from data/storms_vn.geojson",
            "NOAA CPC ENSO Diagnostic Discussion 2026-06-11 for El Nino scenario",
            "Optional SST anomaly inputs from data/climate_scenario_2026.csv",
        ],
        "limitations": [
            "This is an experimental seasonal outlook, not an official weather forecast.",
            "SST anomaly fields are scenario inputs; replace them with OISST/NMME regional values when available.",
            "Landfall regions are approximated from track points near Vietnam seas, not exact coastline crossings.",
        ],
        "months": months,
    }
