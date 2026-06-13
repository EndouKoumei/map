"""Flask routes and API endpoints for Storm Tracker VN."""

import json
import os
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

import backend.similarity as similarity
from backend.fetcher import StormRealtimeFetcher
from backend.similarity import find_similar
from scripts import m1_process_data


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORICAL_PATH = os.path.join(BASE_DIR, "data", "storms_vn.geojson")
HISTORICAL_CACHE_DAYS = 7
HISTORICAL_RETRY_SEC = 3600

app = Flask(__name__, template_folder="frontend")
CORS(app)

fetcher = StormRealtimeFetcher()
_historical_update_lock = threading.Lock()
_historical_last_attempt = 0
_historical_last_result = {
    "checked": False,
    "updated": False,
    "used_fallback": False,
    "message": "Chua kiem tra cap nhat du lieu lich su.",
}


def _file_age_days(path):
    if not os.path.exists(path):
        return None
    return (time.time() - os.path.getmtime(path)) / 86400


def _historical_needs_update(force=False):
    if force:
        return True
    age_days = _file_age_days(HISTORICAL_PATH)
    return age_days is None or age_days >= HISTORICAL_CACHE_DAYS


def ensure_historical_data(force=False):
    """Refresh historical GeoJSON lazily, keeping old data as fallback."""
    global _historical_last_attempt, _historical_last_result

    if not _historical_needs_update(force=force):
        age_days = _file_age_days(HISTORICAL_PATH)
        _historical_last_result = {
            "checked": True,
            "updated": False,
            "used_fallback": False,
            "message": f"Du lieu lich su con moi ({age_days:.2f} ngay).",
        }
        return _historical_last_result

    now = time.time()
    if (
        not force
        and os.path.exists(HISTORICAL_PATH)
        and now - _historical_last_attempt < HISTORICAL_RETRY_SEC
    ):
        age_days = _file_age_days(HISTORICAL_PATH)
        _historical_last_result = {
            "checked": True,
            "updated": False,
            "used_fallback": True,
            "message": f"Dung du lieu cu {age_days:.2f} ngay; tam hoan goi NOAA lai trong 1 gio.",
        }
        return _historical_last_result

    with _historical_update_lock:
        if not _historical_needs_update(force=force):
            age_days = _file_age_days(HISTORICAL_PATH)
            _historical_last_result = {
                "checked": True,
                "updated": False,
                "used_fallback": False,
                "message": f"Du lieu lich su con moi ({age_days:.2f} ngay).",
            }
            return _historical_last_result

        _historical_last_attempt = time.time()
        try:
            csv_path = m1_process_data.download_from_noaa(force=force)
            os.makedirs(os.path.dirname(HISTORICAL_PATH), exist_ok=True)
            m1_process_data.process(csv_path, HISTORICAL_PATH)
            similarity.clear_cache()
            _historical_last_result = {
                "checked": True,
                "updated": True,
                "used_fallback": False,
                "message": "Da cap nhat du lieu lich su tu NOAA IBTrACS.",
            }
        except BaseException as exc:
            if os.path.exists(HISTORICAL_PATH):
                _historical_last_result = {
                    "checked": True,
                    "updated": False,
                    "used_fallback": True,
                    "message": f"Cap nhat NOAA loi, dung GeoJSON cu: {exc}",
                }
            else:
                _historical_last_result = {
                    "checked": True,
                    "updated": False,
                    "used_fallback": False,
                    "message": f"Khong co du lieu lich su va cap nhat NOAA loi: {exc}",
                }
                raise RuntimeError(_historical_last_result["message"]) from exc

        return _historical_last_result


def _load_historical_features():
    ensure_historical_data(force=False)
    if not os.path.exists(HISTORICAL_PATH):
        return []
    with open(HISTORICAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("features", [])


def _storm_region(track_points):
    """Approximate Vietnam region by points near Vietnam seas."""
    hits = []
    for pt in track_points or []:
        lat = pt.get("lat")
        lon = pt.get("lon")
        if lat is None or lon is None:
            continue
        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            continue
        if 8.0 <= lat <= 24.5 and 102.0 <= lon <= 116.5:
            hits.append(lat)

    if not hits:
        return "Ngoai vung ven bien VN"
    avg_lat = sum(hits) / len(hits)
    if avg_lat >= 18:
        return "Bac Bo"
    if avg_lat >= 12:
        return "Trung Bo"
    return "Nam Bo"


def build_dashboard_stats():
    features = _load_historical_features()
    by_decade = {}
    by_month = {str(i): 0 for i in range(1, 13)}
    by_category = {"TD": 0, "TS": 0, "STS": 0, "TY": 0, "STY": 0}
    by_region = {
        "Bac Bo": 0,
        "Trung Bo": 0,
        "Nam Bo": 0,
        "Ngoai vung ven bien VN": 0,
    }
    eras = {
        "1884-1999": {"count": 0, "sty": 0, "wind_sum": 0},
        "2000-2026": {"count": 0, "sty": 0, "wind_sum": 0},
    }
    top = []
    years = []

    for feature in features:
        props = feature.get("properties", {})
        season = int(props.get("season") or 0)
        if season:
            years.append(season)
        max_wind = float(props.get("max_wind_kt") or 0)
        cat = (props.get("max_category") or {}).get("code", "TD")
        if cat not in by_category:
            cat = "TD"

        decade = f"{season // 10 * 10}s" if season else "unknown"
        bucket = by_decade.setdefault(decade, {"count": 0, "wind_sum": 0, "max_wind": 0, "sty": 0})
        bucket["count"] += 1
        bucket["wind_sum"] += max_wind
        bucket["max_wind"] = max(bucket["max_wind"], max_wind)
        if cat == "STY":
            bucket["sty"] += 1
        by_category[cat] += 1

        region = _storm_region(props.get("track_points") or [])
        by_region[region] = by_region.get(region, 0) + 1

        era_key = "2000-2026" if season >= 2000 else "1884-1999"
        eras[era_key]["count"] += 1
        eras[era_key]["wind_sum"] += max_wind
        if cat == "STY":
            eras[era_key]["sty"] += 1

        seen_months = set()
        for pt in props.get("track_points") or []:
            raw_time = str(pt.get("time") or "")
            if len(raw_time) >= 7:
                try:
                    seen_months.add(int(raw_time[5:7]))
                except ValueError:
                    pass
        for month in seen_months:
            if 1 <= month <= 12:
                by_month[str(month)] += 1

        top.append({
            "sid": props.get("sid"),
            "name": props.get("name"),
            "season": season,
            "max_wind_kt": round(max_wind),
            "category": cat,
            "point_count": props.get("point_count", 0),
        })

    decade_rows = []
    for decade in sorted(by_decade):
        item = by_decade[decade]
        count = item["count"] or 1
        decade_rows.append({
            "decade": decade,
            "count": item["count"],
            "avg_wind_kt": round(item["wind_sum"] / count, 1),
            "max_wind_kt": round(item["max_wind"]),
            "super_typhoon_count": item["sty"],
        })

    era_rows = []
    for name, item in eras.items():
        count = item["count"] or 1
        era_rows.append({
            "period": name,
            "count": item["count"],
            "avg_wind_kt": round(item["wind_sum"] / count, 1),
            "super_typhoon_count": item["sty"],
            "super_typhoon_pct": round(item["sty"] / count * 100, 1),
        })

    return {
        "summary": {
            "total_storms": len(features),
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
            "year_count": len(set(years)),
            "max_wind_kt": max((x["max_wind_kt"] for x in top), default=0),
        },
        "by_decade": decade_rows,
        "by_month": [{"month": int(k), "count": v} for k, v in by_month.items()],
        "by_category": [{"category": k, "count": v} for k, v in by_category.items()],
        "by_region": [{"region": k, "count": v} for k, v in by_region.items()],
        "era_comparison": era_rows,
        "top_strongest": sorted(top, key=lambda x: x["max_wind_kt"], reverse=True)[:10],
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


@app.route("/")
def home():
    return render_template("m1_map.html")


@app.route("/historical")
def historical():
    return render_template("m1_map.html")


@app.route("/realtime")
def realtime():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("m4_dashboard.html")


@app.route("/api/historical-storms")
def historical_storms():
    try:
        ensure_historical_data(force=request.args.get("refresh") == "1")
    except RuntimeError as exc:
        return jsonify({
            "error": str(exc),
            "fix": "Kiem tra internet hoac chay: python scripts/m1_process_data.py",
        }), 503

    if not os.path.exists(HISTORICAL_PATH):
        return jsonify({
            "error": "Chua co du lieu lich su.",
            "fix": "Chay lenh: python scripts/m1_process_data.py",
        }), 404

    return send_file(HISTORICAL_PATH, mimetype="application/json", as_attachment=False)


@app.route("/api/update-historical", methods=["GET", "POST"])
def update_historical():
    try:
        force = request.args.get("force") == "1"
        result = ensure_historical_data(force=force)
        status_code = 200 if os.path.exists(HISTORICAL_PATH) else 503
        return jsonify({
            **result,
            "force": force,
            "geojson_path": HISTORICAL_PATH,
            "geojson_age_days": _file_age_days(HISTORICAL_PATH),
            "csv_cache_path": m1_process_data.CACHE_FILE,
            "csv_cache_age_days": _file_age_days(m1_process_data.CACHE_FILE),
        }), status_code
    except RuntimeError as exc:
        return jsonify({
            "checked": True,
            "updated": False,
            "used_fallback": False,
            "error": str(exc),
        }), 503


@app.route("/api/active-storms")
def active_storms():
    try:
        force_refresh = request.args.get("refresh") == "1"
        return jsonify(fetcher.get_active_storms(force_refresh=force_refresh))
    except Exception as exc:
        return jsonify({
            "type": "FeatureCollection",
            "error": str(exc),
            "features": [],
        }), 500


@app.route("/api/forecast/<storm_id>")
def storm_forecast(storm_id):
    try:
        return jsonify(fetcher.get_forecast(storm_id))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/storm/<storm_id>")
def storm_detail(storm_id):
    try:
        return jsonify(fetcher.get_storm_detail(storm_id))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/similar-storms/<storm_id>")
def similar_storms(storm_id):
    try:
        top_k = int(request.args.get("k", 5))
        return jsonify(find_similar(storm_id, top_k=top_k))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/dashboard-stats")
def dashboard_stats():
    try:
        return jsonify(build_dashboard_stats())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/status")
def status():
    historical_ok = os.path.exists(HISTORICAL_PATH)
    historical_size = (
        round(os.path.getsize(HISTORICAL_PATH) / 1024 / 1024, 1)
        if historical_ok else 0
    )
    return jsonify({
        "system": "Storm Tracker VN",
        "version": "2.2 (M1+M2+M3+M4)",
        "modules": {
            "M1_historical": {
                "status": "ready" if historical_ok else "no_data",
                "file_size_mb": historical_size,
                "geojson_age_days": _file_age_days(HISTORICAL_PATH),
                "csv_cache_age_days": _file_age_days(m1_process_data.CACHE_FILE),
                "cache_days": HISTORICAL_CACHE_DAYS,
                "auto_update": "lazy_on_api_request",
                "last_update_check": _historical_last_result,
                "endpoint": "/api/historical-storms",
            },
            "M2_realtime": {
                "status": "ready",
                "last_update": fetcher.last_update,
                "storm_count": fetcher.storm_count,
                "source": "JMA / IBTrACS NRT with sample fallback",
                "cache_seconds": fetcher.CACHE_SEC,
                "endpoint": "/api/active-storms",
            },
            "M3_similarity": {
                "status": "ready" if historical_ok else "no_data",
                "method": "DTW + cosine multi-factor score",
                "endpoint": "/api/similar-storms/<storm_id>",
            },
            "M4_dashboard": {
                "status": "ready" if historical_ok else "no_data",
                "endpoint": "/api/dashboard-stats",
                "page": "/dashboard",
            },
        },
    })


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Storm Tracker VN - v2.2 (M1 + M2 + M3 + M4)")
    print("=" * 50)
    print("  M1 historical: http://localhost:5000/")
    print("  M2 realtime:   http://localhost:5000/realtime")
    print("  M4 dashboard:  http://localhost:5000/dashboard")
    print("  API status:    http://localhost:5000/api/status")
    print("=" * 50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
