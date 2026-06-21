"""Realtime storm fetcher with stable fallback data."""

import copy
import io
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import requests


VN_CATS = [
    {"code": "TD", "name": "Áp thấp nhiệt đới", "max_kt": 33, "color": "#6EC1EA", "css": "td"},
    {"code": "TS", "name": "Bão (bão thường)", "max_kt": 47, "color": "#4DFFFF", "css": "ts"},
    {"code": "STS", "name": "Bão mạnh", "max_kt": 63, "color": "#C0FFC0", "css": "sts"},
    {"code": "TY", "name": "Bão rất mạnh", "max_kt": 98, "color": "#FF738A", "css": "ty"},
    {"code": "STY", "name": "Siêu bão", "max_kt": 999, "color": "#A188FC", "css": "sty"},
]


def classify(wind_kt):
    wind = float(wind_kt) if wind_kt else 0
    for cat in VN_CATS:
        if wind <= cat["max_kt"]:
            return cat
    return VN_CATS[-1]


def safe_float(value, default=0):
    try:
        return float(value) if value and str(value).strip() else default
    except (TypeError, ValueError):
        return default


SAMPLE_STORMS = {
    "type": "FeatureCollection",
    "source": "JTWC Best Track WP032024 (Demo)",
    "note": "Dữ liệu mẫu từ bão Yagi 2024, dùng khi nguồn realtime không có bão hoặc bị lỗi.",
    "features": [{
        "type": "Feature",
        "properties": {
            "id": "2024231N13138",
            "name": "YAGI - Bão số 3 (2024)",
            "basin": "WP",
            "wind_kt": 155,
            "pressure_mb": 900,
            "category": classify(155),
            "lat": 18.8,
            "lon": 114.0,
            "movement_dir": "WNW",
            "movement_speed_kt": 14,
            "timestamp": "2024-09-06 06:00 UTC",
            "is_sample": True,
            "source": "JTWC Best Track WP032024",
            "track_intensity": [35, 45, 55, 65, 80, 95, 115, 130, 145, 155, 155, 145, 130, 110, 90, 60, 45, 35, 25],
        },
        "geometry": {"type": "LineString", "coordinates": [
            [134.0, 14.8], [132.5, 15.0], [131.0, 15.5], [129.5, 16.0], [128.0, 16.3],
            [126.5, 16.5], [125.0, 16.8], [123.5, 17.0], [121.5, 17.5], [119.0, 18.0],
            [116.5, 18.5], [114.0, 18.8], [111.5, 19.2], [109.0, 19.8], [107.5, 20.5],
            [106.5, 21.0], [105.5, 22.0], [104.5, 23.0], [103.5, 24.0],
        ]},
    }],
}

SAMPLE_FORECASTS = {
    "2024231N13138": {
        "storm_id": "2024231N13138",
        "storm_name": "YAGI - Bão số 3 (2024)",
        "source": "JTWC Advisory WP032024 - 2024-09-06 06:00 UTC",
        "issued_at": "2024-09-06 06:00 UTC",
        "is_sample": True,
        "note": "Dữ liệu dự báo mẫu phục vụ demo khi không có bão realtime.",
        "cone_points": [
            {"hour": 0, "lat": 18.8, "lon": 114.0, "wind_kt": 145, "pressure_mb": 910, "category": classify(145), "label": "+0h"},
            {"hour": 12, "lat": 19.1, "lon": 111.6, "wind_kt": 138, "pressure_mb": 918, "category": classify(138), "label": "+12h"},
            {"hour": 24, "lat": 19.5, "lon": 109.3, "wind_kt": 120, "pressure_mb": 930, "category": classify(120), "label": "+24h"},
            {"hour": 36, "lat": 20.0, "lon": 107.8, "wind_kt": 100, "pressure_mb": 945, "category": classify(100), "label": "+36h"},
            {"hour": 48, "lat": 20.6, "lon": 107.0, "wind_kt": 80, "pressure_mb": 960, "category": classify(80), "label": "+48h"},
            {"hour": 72, "lat": 21.8, "lon": 106.0, "wind_kt": 45, "pressure_mb": 985, "category": classify(45), "label": "+72h"},
            {"hour": 96, "lat": 23.2, "lon": 104.8, "wind_kt": 25, "pressure_mb": 998, "category": classify(25), "label": "+96h"},
            {"hour": 120, "lat": 25.0, "lon": 103.5, "wind_kt": 15, "pressure_mb": 1006, "category": classify(15), "label": "+120h"},
        ],
        "forecast_geojson": {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [
                [114.0, 18.8], [111.6, 19.1], [109.3, 19.5], [107.8, 20.0],
                [107.0, 20.6], [106.0, 21.8], [104.8, 23.2], [103.5, 25.0],
            ]},
        },
    }
}


class StormRealtimeFetcher:
    CACHE_SEC = 6 * 3600
    RECENT_DAYS = 2
    JMA_TIMEOUT_SEC = 5
    IBTRACS_TIMEOUT_SEC = 12

    JMA_BASE_URL = "https://www.jma.go.jp/bosai/typhoon/data"
    JMA_TARGET_URL = f"{JMA_BASE_URL}/targetTc.json"
    IBTRACS_NRT_URL = (
        "https://www.ncei.noaa.gov/data/international-best-track-archive-"
        "for-climate-stewardship-ibtracs/v04r01/access/csv/"
        "ibtracs.last3years.list.v04r01.csv"
    )

    def __init__(self):
        self._cache: Optional[dict] = None
        self._cache_time = 0.0
        self._forecast_cache = {}
        self._fetch_lock = threading.Lock()
        self.last_update = "Chưa cập nhật"
        self.storm_count = 0
        self.active_source = "unknown"

    def get_active_storms(self, force_refresh: bool = False) -> dict:
        if not force_refresh and self._is_cache_valid():
            return self._cache

        with self._fetch_lock:
            if not force_refresh and self._is_cache_valid():
                return self._cache

            data = None
            for source_fn, source_name in [
                (self._fetch_jma, "JMA"),
                (self._fetch_ibtracs_nrt, "IBTrACS NRT"),
            ]:
                try:
                    result = source_fn()
                    if result and result.get("features"):
                        data = result
                        self.active_source = source_name
                        print(f"Data source: {source_name} ({len(result['features'])} storms)")
                        break
                except Exception as exc:
                    print(f"{source_name} error: {exc}")

            if not data:
                data = self._fetch_sample()
                self.active_source = "sample_data"
                print("Using sample data because realtime sources are unavailable or empty.")

            data.setdefault("type", "FeatureCollection")
            data.setdefault("features", [])
            data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
            data.setdefault("source", self.active_source)

            self._cache = data
            self._cache_time = time.time()
            self.last_update = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            self.storm_count = len(data.get("features", []))
            return data

    def get_forecast(self, storm_id: str) -> dict:
        cached = self._forecast_cache.get(storm_id)
        if cached and time.time() - cached.get("_time", 0) < self.CACHE_SEC:
            return {k: v for k, v in cached.items() if k != "_time"}

        try:
            data = self._fetch_jma_forecast(storm_id)
            if data and "cone_points" in data:
                self._forecast_cache[storm_id] = {**data, "_time": time.time()}
                return data
        except Exception:
            pass

        if storm_id in SAMPLE_FORECASTS:
            data = copy.deepcopy(SAMPLE_FORECASTS[storm_id])
            data["generated_at"] = datetime.now(timezone.utc).isoformat()
            self._forecast_cache[storm_id] = {**data, "_time": time.time()}
            return data

        return {
            "storm_id": storm_id,
            "no_forecast": True,
            "reason": "Không có dữ liệu dự báo cho cơn bão này.",
            "cone_points": [],
            "forecast_geojson": {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": []},
            },
        }

    def get_storm_detail(self, storm_id: str) -> dict:
        storms = self.get_active_storms()
        for feature in storms.get("features", []):
            if feature["properties"]["id"] == storm_id:
                return feature["properties"]
        return {"error": f"Không tìm thấy bão {storm_id}"}

    def _jma_category(self, code):
        labels = {
            "TD": "Áp thấp nhiệt đới (JMA)",
            "TS": "Bão nhiệt đới (JMA)",
            "STS": "Bão rất mạnh (JMA)",
            "TY": "Typhoon (JMA)",
        }
        return {
            "code": "JMA",
            "name": labels.get(code, f"Phân cấp JMA: {code or 'N/A'}"),
            "css": "jma",
            "color": "#60a5fa",
        }

    def _jma_forecast_url(self, storm_id):
        return f"{self.JMA_BASE_URL}/{storm_id}/forecast.json"

    def _request_jma_forecast(self, storm_id):
        headers = {"User-Agent": "Mozilla/5.0 (Storm Tracker VN/2.3)"}
        resp = requests.get(
            self._jma_forecast_url(storm_id),
            headers=headers,
            timeout=self.JMA_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        return resp.json()

    def _parse_jma_forecast(self, storm_id, payload, category_code=None):
        title = next((item for item in payload if item.get("part") == "title"), {})
        analysis = next((item for item in payload if item.get("advancedHours") == 0), {})
        category = self._jma_category(category_code)
        cone_points = []

        for item in payload:
            if "advancedHours" not in item or not item.get("center"):
                continue
            lat, lon = item["center"]
            cone_points.append({
                "hour": int(item["advancedHours"]),
                "lat": safe_float(lat),
                "lon": safe_float(lon),
                "wind_kt": None,
                "pressure_mb": None,
                "category": category,
                "label": (item.get("part") or {}).get("en", f"+{item['advancedHours']}h"),
                "valid_time": (item.get("validtime") or {}).get("UTC"),
            })

        cone_points.sort(key=lambda point: point["hour"])
        coords = [[point["lon"], point["lat"]] for point in cone_points]
        name = ((title.get("name") or {}).get("en") or storm_id).strip()
        issue = (title.get("issue") or {}).get("UTC")

        return {
            "storm_id": storm_id,
            "storm_name": name,
            "source": "JMA Typhoon Map",
            "issued_at": issue,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_note": "JMA forecast JSON does not provide wind or pressure in this adapter.",
            "cone_points": cone_points,
            "forecast_geojson": {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
            },
            "_analysis": analysis,
        }

    def _jma_track_coordinates(self, analysis):
        track = (analysis or {}).get("track") or {}
        points = list(track.get("preTyphoon") or []) + list(track.get("typhoon") or [])
        coords = []
        for lat, lon in points:
            coord = [safe_float(lon), safe_float(lat)]
            if not coords or coords[-1] != coord:
                coords.append(coord)
        return coords

    def _fetch_jma(self) -> dict:
        headers = {"User-Agent": "Mozilla/5.0 (Storm Tracker VN/2.3)"}
        resp = requests.get(self.JMA_TARGET_URL, headers=headers, timeout=self.JMA_TIMEOUT_SEC)
        resp.raise_for_status()

        features = []
        for target in resp.json():
            storm_id = target.get("tropicalCyclone")
            if not storm_id:
                continue
            try:
                forecast = self._parse_jma_forecast(
                    storm_id,
                    self._request_jma_forecast(storm_id),
                    target.get("category"),
                )
                analysis = forecast.pop("_analysis", {})
                current = next((point for point in forecast["cone_points"] if point["hour"] == 0), None)
                if not current:
                    continue
                lat = current["lat"]
                lon = current["lon"]
                if not (0 <= lat <= 40 and 95 <= lon <= 160):
                    continue
                coords = self._jma_track_coordinates(analysis) or [[lon, lat]]
                self._forecast_cache[storm_id] = {**forecast, "_time": time.time()}
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": storm_id,
                        "name": forecast["storm_name"],
                        "basin": "WP",
                        "wind_kt": None,
                        "pressure_mb": None,
                        "category": current["category"],
                        "lat": lat,
                        "lon": lon,
                        "movement_dir": "N/A",
                        "movement_speed_kt": None,
                        "timestamp": current.get("valid_time") or forecast.get("issued_at"),
                        "is_sample": False,
                        "source": "JMA Typhoon Map",
                        "data_note": forecast["data_note"],
                        "track_intensity": [],
                    },
                    "geometry": {"type": "LineString", "coordinates": coords},
                })
            except Exception as exc:
                print(f"JMA storm {storm_id} error: {exc}")

        return {
            "type": "FeatureCollection",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "JMA Typhoon Map",
            "source_url": self.JMA_TARGET_URL,
            "features": features,
        }

    def _fetch_jma_forecast(self, storm_id: str) -> dict:
        payload = self._request_jma_forecast(storm_id)
        return self._parse_jma_forecast(storm_id, payload)

    def _fetch_ibtracs_nrt(self) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.RECENT_DAYS)
        headers = {"User-Agent": "Mozilla/5.0 (Storm Tracker DATN/2.0; VN)"}
        resp = requests.get(
            self.IBTRACS_NRT_URL,
            headers=headers,
            timeout=self.IBTRACS_TIMEOUT_SEC,
            stream=True,
        )
        resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.content.decode("utf-8", errors="ignore")), skiprows=[1], low_memory=False)
        df.columns = df.columns.str.strip()
        df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
        df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
        df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce", utc=True)
        df.dropna(subset=["LAT", "LON", "ISO_TIME"], inplace=True)
        df = df[df["ISO_TIME"] >= cutoff]
        df = df[(df["LAT"] >= 0) & (df["LAT"] <= 40) & (df["LON"] >= 95) & (df["LON"] <= 160)]

        if df.empty:
            return {"type": "FeatureCollection", "features": []}

        wind_col = "USA_WIND" if "USA_WIND" in df.columns else "WMO_WIND"
        pres_col = "USA_PRES" if "USA_PRES" in df.columns else "WMO_PRES"
        df["WIND_KT"] = pd.to_numeric(df[wind_col], errors="coerce").fillna(0)
        df["PRES_MB"] = pd.to_numeric(df[pres_col], errors="coerce").fillna(1000)
        df.sort_values(["SID", "ISO_TIME"], inplace=True)

        features = []
        for sid, group in df.groupby("SID"):
            group = group.reset_index(drop=True)
            if len(group) < 2:
                continue
            latest = group.iloc[-1]
            name = str(group["NAME"].iloc[0]).strip()
            if name.upper() in ("NOT_NAMED", "UNNAMED", ""):
                name = f"Bão chưa đặt tên ({group['SEASON'].iloc[0]})"

            features.append({
                "type": "Feature",
                "properties": {
                    "id": sid,
                    "name": name,
                    "basin": "WP",
                    "wind_kt": round(float(latest["WIND_KT"])),
                    "pressure_mb": float(latest["PRES_MB"]),
                    "category": classify(float(latest["WIND_KT"])),
                    "lat": float(latest["LAT"]),
                    "lon": float(latest["LON"]),
                    "movement_dir": "N/A",
                    "movement_speed_kt": 0,
                    "timestamp": str(latest["ISO_TIME"])[:16] + " UTC",
                    "is_sample": False,
                    "source": "IBTrACS NRT (NOAA)",
                    "track_intensity": [round(w) for w in group["WIND_KT"]],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[row["LON"], row["LAT"]] for _, row in group.iterrows()],
                },
            })

        return {
            "type": "FeatureCollection",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "IBTrACS near-real-time (NOAA)",
            "source_url": self.IBTRACS_NRT_URL,
            "note": f"Bão trong {self.RECENT_DAYS} ngày gần nhất",
            "features": features,
        }

    def _fetch_sample(self) -> dict:
        data = copy.deepcopy(SAMPLE_STORMS)
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        return data

    def _is_cache_valid(self) -> bool:
        return self._cache is not None and time.time() - self._cache_time < self.CACHE_SEC
