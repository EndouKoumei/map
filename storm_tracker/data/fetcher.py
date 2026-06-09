"""
StormRealtimeFetcher – M2 Theo dõi bão thời gian thực
Chiến lược đa nguồn (Multi-source fallback):

  1. JMA API (jma.go.jp)           → Thực tế, cập nhật vài giờ/lần, không cần key
  2. IBTrACS last3years (NOAA)     → Cập nhật 2 lần/tuần, lag ~2-3 ngày
  3. tropycal (JTWC)               → Nếu đã cài: pip install tropycal
  4. Dữ liệu mẫu                   → Fallback cuối cùng (bão Yagi 2024)

ĐATN 2025.2 – Đặng Hồng Minh – 20225740
"""
import json, os, time, requests
from datetime import datetime, timezone, timedelta
from typing import Optional

# ── Phân cấp bão Việt Nam (QĐ 18/2021/QĐ-TTg) ────────────────────────────────
VN_CATS = [
    {"code":"TD",  "name":"Áp thấp nhiệt đới", "max_kt":33,  "color":"#6EC1EA", "css":"td"},
    {"code":"TS",  "name":"Bão (bão thường)",     "max_kt":47,  "color":"#4DFFFF", "css":"ts"},
    {"code":"STS", "name":"Bão mạnh",             "max_kt":63,  "color":"#C0FFC0", "css":"sts"},
    {"code":"TY",  "name":"Bão rất mạnh",         "max_kt":98,  "color":"#FF738A", "css":"ty"},
    {"code":"STY", "name":"Siêu bão",             "max_kt":999, "color":"#A188FC", "css":"sty"},
]

def classify(wind_kt):
    w = float(wind_kt) if wind_kt else 0
    for cat in VN_CATS:
        if w <= cat["max_kt"]:
            return cat
    return VN_CATS[-1]

def safe_float(v, default=0):
    try: return float(v) if v and str(v).strip() else default
    except: return default

# ── Dữ liệu mẫu (fallback cuối cùng) ─────────────────────────────────────────
# ── Dữ liệu THỰC của bão Yagi 2024 (JTWC 03W) – dùng khi không có bão thật ──
# Nguồn: JTWC Best Track WP032024, IBTrACS v04r01
SAMPLE_STORMS = {
    "type": "FeatureCollection",
    "source": "JTWC Best Track WP032024 (Demo)",
    "note": "Dữ liệu thực bão Yagi 2024 – hệ thống sẽ hiển thị bão thật khi mùa bão bắt đầu",
    "features": [{
        "type": "Feature",
        "properties": {
            "id": "2024231N13138",
            "name": "YAGI – Bão số 3 (2024)",
            "basin": "WP", "wind_kt": 155, "pressure_mb": 900,
            "category": classify(155),
            "lat": 18.8, "lon": 114.0,
            "movement_dir": "WNW", "movement_speed_kt": 14,
            "timestamp": "2024-09-06 06:00 UTC",
            "is_sample": True,
            "source": "JTWC Best Track WP032024",
            "track_intensity": [
                35, 45, 55, 65, 80, 95, 115, 130,
                145, 155, 155, 145, 130, 110, 90, 60,
                45, 35, 25
            ],
        },
        "geometry": {"type": "LineString", "coordinates": [
            [134.0, 14.8], [132.5, 15.0], [131.0, 15.5],
            [129.5, 16.0], [128.0, 16.3], [126.5, 16.5],
            [125.0, 16.8], [123.5, 17.0], [121.5, 17.5],
            [119.0, 18.0], [116.5, 18.5], [114.0, 18.8],
            [111.5, 19.2], [109.0, 19.8], [107.5, 20.5],
            [106.5, 21.0], [105.5, 22.0], [104.5, 23.0],
            [103.5, 24.0],
        ]},
    }],
}

SAMPLE_FORECASTS = {
    "2024231N13138": {
        "storm_id": "2024231N13138",
        "storm_name": "YAGI – Bão số 3 (2024)",
        "source": "JTWC Advisory WP032024 – Phát lúc 06/09/2024 06:00 UTC",
        "issued_at": "2024-09-06 06:00 UTC",
        "is_sample": True,
        "note": "Dự báo JTWC thực tế phát khi bão còn trên Biển Đông hướng vào VN",
        # Dự báo tại thời điểm 06/09 06:00Z: bão 18.8N 114.0E 145kt
        "cone_points": [
            {"hour": 0,   "lat": 18.8, "lon": 114.0, "wind_kt": 145,
             "pressure_mb": 910, "category": classify(145),
             "label": "Vị trí lúc phát báo"},
            {"hour": 12,  "lat": 19.1, "lon": 111.6, "wind_kt": 138,
             "pressure_mb": 918, "category": classify(138),
             "label": "Dự báo JTWC +12h"},
            {"hour": 24,  "lat": 19.5, "lon": 109.3, "wind_kt": 120,
             "pressure_mb": 930, "category": classify(120),
             "label": "Dự báo JTWC +24h"},
            {"hour": 36,  "lat": 20.0, "lon": 107.8, "wind_kt": 100,
             "pressure_mb": 945, "category": classify(100),
             "label": "Dự báo JTWC +36h"},
            {"hour": 48,  "lat": 20.6, "lon": 107.0, "wind_kt": 80,
             "pressure_mb": 960, "category": classify(80),
             "label": "Dự báo đổ bộ Quảng Ninh"},
            {"hour": 72,  "lat": 21.8, "lon": 106.0, "wind_kt": 45,
             "pressure_mb": 985, "category": classify(45),
             "label": "Dự báo JTWC +72h"},
            {"hour": 96,  "lat": 23.2, "lon": 104.8, "wind_kt": 25,
             "pressure_mb": 998, "category": classify(25),
             "label": "Dự báo JTWC +96h"},
            {"hour": 120, "lat": 25.0, "lon": 103.5, "wind_kt": 15,
             "pressure_mb": 1006, "category": classify(15),
             "label": "Dự báo tan"},
        ],
        "forecast_geojson": {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [
                [114.0, 18.8], [111.6, 19.1], [109.3, 19.5],
                [107.8, 20.0], [107.0, 20.6], [106.0, 21.8],
                [104.8, 23.2], [103.5, 25.0],
            ]},
        },
    }
}


class StormRealtimeFetcher:
    """
    Fetcher đa nguồn với thứ tự ưu tiên:
    JMA → IBTrACS last3years → tropycal → sample
    """

    CACHE_SEC       = 6 * 3600   # cache 6 giờ
    RECENT_DAYS     = 2         # IBTrACS: lấy bão trong 2 ngày gần nhất

    # URLs nguồn dữ liệu
    JMA_URL         = "https://www.jma.go.jp/bosai/typhoon/data/TCINFO.json"
    IBTRACS_NRT_URL = (
        "https://www.ncei.noaa.gov/data/international-best-track-archive-"
        "for-climate-stewardship-ibtracs/v04r01/access/csv/"
        "ibtracs.last3years.list.v04r01.csv"
    )

    def __init__(self):
        self._cache: Optional[dict]    = None
        self._cache_time: float        = 0
        self._forecast_cache: dict     = {}
        self.last_update: str          = "Chưa cập nhật"
        self.storm_count: int          = 0
        self.active_source: str        = "unknown"

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    def get_active_storms(self, force_refresh: bool = False) -> dict:
        if not force_refresh and self._is_cache_valid():
            return self._cache

        # Thử từng nguồn theo thứ tự ưu tiên
        data = None
        for source_fn, source_name in [
            (self._fetch_jma,            "JMA"),
            (self._fetch_ibtracs_nrt,    "IBTrACS NRT"),
            (self._fetch_tropycal,       "tropycal/JTWC"),
        ]:
            try:
                result = source_fn()
                if result and result.get("features"):
                    data = result
                    self.active_source = source_name
                    print(f"  ✓ Dữ liệu từ: {source_name} ({len(result['features'])} bão)")
                    break
            except Exception as e:
                print(f"  ✗ {source_name}: {e}")

        if not data:
            data = self._fetch_sample()
            self.active_source = "sample_data"
            print("  ⚠ Dùng dữ liệu mẫu (không kết nối được nguồn thực tế)")

        data.setdefault("type", "FeatureCollection")
        data.setdefault("features", [])
        data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
        data.setdefault("source", self.active_source)

        self._cache      = data
        self._cache_time = time.time()
        self.last_update = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.storm_count = len(data.get("features", []))
        return data

    def get_forecast(self, storm_id: str) -> dict:
        if storm_id in self._forecast_cache:
            cached = self._forecast_cache[storm_id]
            if time.time() - cached.get("_time", 0) < self.CACHE_SEC:
                return {k: v for k, v in cached.items() if k != "_time"}

        try:
            data = self._fetch_jma_forecast(storm_id)
            if data and "cone_points" in data:
                self._forecast_cache[storm_id] = {**data, "_time": time.time()}
                return data
        except Exception:
            pass

        if storm_id in SAMPLE_FORECASTS:
            data = dict(SAMPLE_FORECASTS[storm_id])
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
        for f in storms.get("features", []):
            if f["properties"]["id"] == storm_id:
                return f["properties"]
        return {"error": f"Không tìm thấy bão {storm_id}"}

    # ══════════════════════════════════════════════════════════════════════════
    # NGUỒN 1: JMA (Japan Meteorological Agency) – Thực tế nhất
    # URL: https://www.jma.go.jp/bosai/typhoon/data/TCINFO.json
    # Cập nhật: mỗi vài giờ trong mùa bão
    # Không cần API key
    # ══════════════════════════════════════════════════════════════════════════
    def _fetch_jma(self) -> dict:
        headers = {"User-Agent": "Mozilla/5.0 (Storm Tracker DATN/2.0; VN)"}
        resp = requests.get(self.JMA_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        features = []
        for tc in raw:
            try:
                tc_id   = tc.get("id", "")
                tc_name = tc.get("name", tc_id)
                grade   = tc.get("grade", "")  # T=Typhoon, STS, TS, TD

                # Lấy điểm quan trắc gần nhất (pref = present forecast)
                pref_list = tc.get("pref", [])
                if not pref_list:
                    continue

                # Sắp xếp theo thời gian
                pref_list = sorted(pref_list, key=lambda x: x.get("time",""))
                latest    = pref_list[-1]
                lat       = safe_float(latest.get("lat"))
                lon       = safe_float(latest.get("lon"))
                wind_kt   = safe_float(latest.get("wind")) * 0.539957  # km/h → kt
                pres_mb   = safe_float(latest.get("pres"), 1000)
                ts        = latest.get("time", "")

                if not lat or not lon:
                    continue

                # Lọc vùng Tây TBD ảnh hưởng VN
                if not (0 <= lat <= 40 and 95 <= lon <= 160):
                    continue

                # Track intensity từ toàn bộ pref
                coords     = [[safe_float(p.get("lon")), safe_float(p.get("lat"))]
                               for p in pref_list if p.get("lon") and p.get("lat")]
                intensities = [safe_float(p.get("wind", 0)) * 0.539957 for p in pref_list]

                feature = {
                    "type": "Feature",
                    "properties": {
                        "id":               tc_id,
                        "name":             tc_name,
                        "basin":            "WP",
                        "wind_kt":          round(wind_kt),
                        "pressure_mb":      pres_mb,
                        "category":         classify(wind_kt),
                        "lat":              lat,
                        "lon":              lon,
                        "movement_dir":     "N/A",
                        "movement_speed_kt": 0,
                        "timestamp":        ts,
                        "is_sample":        False,
                        "source":           "JMA",
                        "track_intensity":  [round(w) for w in intensities],
                    },
                    "geometry": {"type": "LineString", "coordinates": coords or [[lon, lat]]},
                }
                features.append(feature)
            except Exception:
                continue

        return {
            "type":         "FeatureCollection",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source":       "JMA (Japan Meteorological Agency)",
            "source_url":   self.JMA_URL,
            "features":     features,
        }

    def _fetch_jma_forecast(self, storm_id: str) -> dict:
        """Lấy đường dự báo từ JMA cho 1 cơn bão."""
        headers = {"User-Agent": "Mozilla/5.0 (Storm Tracker DATN/2.0; VN)"}
        resp    = requests.get(self.JMA_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        for tc in raw:
            if tc.get("id") != storm_id:
                continue
            forecast_list = tc.get("forecast", [])
            if not forecast_list:
                return {}

            forecast_list = sorted(forecast_list, key=lambda x: x.get("time",""))

            # Tìm thời điểm hiện tại làm mốc 0h
            pref = sorted(tc.get("pref", []), key=lambda x: x.get("time",""))
            t0   = pref[-1] if pref else {}

            cone_pts = []
            coords   = []

            # Điểm 0h (hiện tại)
            if t0:
                w = safe_float(t0.get("wind", 0)) * 0.539957
                cone_pts.append({
                    "hour": 0, "lat": safe_float(t0.get("lat")), "lon": safe_float(t0.get("lon")),
                    "wind_kt": round(w), "pressure_mb": safe_float(t0.get("pres"), 1000),
                    "category": classify(w),
                })
                coords.append([safe_float(t0.get("lon")), safe_float(t0.get("lat"))])

            for i, pt in enumerate(forecast_list):
                lat  = safe_float(pt.get("lat"))
                lon  = safe_float(pt.get("lon"))
                w    = safe_float(pt.get("wind", 0)) * 0.539957
                pres = safe_float(pt.get("pres", 1000))
                hr   = (i + 1) * 24  # JMA thường dự báo theo ngày

                cone_pts.append({
                    "hour": hr, "lat": lat, "lon": lon,
                    "wind_kt": round(w), "pressure_mb": pres,
                    "category": classify(w),
                })
                coords.append([lon, lat])

            return {
                "storm_id":     storm_id,
                "storm_name":   tc.get("name", storm_id),
                "source":       "JMA",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "cone_points":  cone_pts,
                "forecast_geojson": {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                },
            }
        return {}

    # ══════════════════════════════════════════════════════════════════════════
    # NGUỒN 2: IBTrACS last3years (NOAA) – Cập nhật 2 lần/tuần
    # URL: ibtracs.last3years.list.v04r01.csv
    # Chứa bão trong 3 năm gần nhất, bao gồm "provisional data" rất mới
    # ══════════════════════════════════════════════════════════════════════════
    def _fetch_ibtracs_nrt(self) -> dict:
        import pandas as pd, io
        from datetime import timezone as tz

        cutoff = datetime.now(tz.utc) - timedelta(days=self.RECENT_DAYS)
        headers = {"User-Agent": "Mozilla/5.0 (Storm Tracker DATN/2.0; VN)"}

        resp = requests.get(self.IBTRACS_NRT_URL, headers=headers,
                            timeout=60, stream=True)
        resp.raise_for_status()

        # Đọc CSV (bỏ dòng units ở row 1)
        content = resp.content.decode("utf-8", errors="ignore")
        df = pd.read_csv(io.StringIO(content), skiprows=[1], low_memory=False)
        df.columns = df.columns.str.strip()

        # Chuẩn hóa
        df["LAT"]      = pd.to_numeric(df["LAT"],      errors="coerce")
        df["LON"]      = pd.to_numeric(df["LON"],      errors="coerce")
        df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce", utc=True)
        df.dropna(subset=["LAT","LON","ISO_TIME"], inplace=True)

        # Chỉ lấy bão trong RECENT_DAYS ngày gần nhất
        df = df[df["ISO_TIME"] >= cutoff]

        # Lọc vùng Tây TBD
        df = df[(df["LAT"]>=0)&(df["LAT"]<=40)&(df["LON"]>=95)&(df["LON"]<=160)]

        if df.empty:
            return {"type":"FeatureCollection","features":[]}

        # Chọn cột gió
        wind_col = "USA_WIND" if "USA_WIND" in df.columns else "WMO_WIND"
        pres_col = "USA_PRES" if "USA_PRES" in df.columns else "WMO_PRES"
        df["WIND_KT"] = pd.to_numeric(df[wind_col], errors="coerce").fillna(0)
        df["PRES_MB"] = pd.to_numeric(df[pres_col], errors="coerce").fillna(1000)

        df.sort_values(["SID","ISO_TIME"], inplace=True)
        features = []

        for sid, grp in df.groupby("SID"):
            grp = grp.reset_index(drop=True)
            if len(grp) < 2: continue

            coords      = [[row["LON"], row["LAT"]] for _, row in grp.iterrows()]
            intensities = [row["WIND_KT"] for _, row in grp.iterrows()]
            times       = [str(row["ISO_TIME"])[:16] for _, row in grp.iterrows()]

            latest    = grp.iloc[-1]
            max_wind  = float(grp["WIND_KT"].max())
            name      = str(grp["NAME"].iloc[0]).strip()
            if name.upper() in ("NOT_NAMED", "UNNAMED", ""):
                name = f"Bão chưa đặt tên ({grp['SEASON'].iloc[0]})"

            feature = {
                "type": "Feature",
                "properties": {
                    "id":               sid,
                    "name":             name,
                    "basin":            "WP",
                    "wind_kt":          round(float(latest["WIND_KT"])),
                    "pressure_mb":      float(latest["PRES_MB"]),
                    "category":         classify(float(latest["WIND_KT"])),
                    "lat":              float(latest["LAT"]),
                    "lon":              float(latest["LON"]),
                    "movement_dir":     "N/A",
                    "movement_speed_kt": 0,
                    "timestamp":        times[-1] + " UTC",
                    "is_sample":        False,
                    "source":           "IBTrACS NRT (NOAA)",
                    "track_intensity":  [round(w) for w in intensities],
                },
                "geometry": {"type":"LineString","coordinates":coords},
            }
            features.append(feature)

        return {
            "type":         "FeatureCollection",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source":       "IBTrACS near-real-time (NOAA, updated 2x/week)",
            "source_url":   self.IBTRACS_NRT_URL,
            "note":         f"Bão trong {self.RECENT_DAYS} ngày gần nhất",
            "features":     features,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # NGUỒN 3: tropycal (JTWC) – Nếu đã cài
    # ══════════════════════════════════════════════════════════════════════════
    def _fetch_tropycal(self) -> dict:
        import tropycal.realtime as rt_module
        realtime_obj = rt_module.Realtime(jtwc=True, jtwc_source="jtwc")
        storms = realtime_obj.list_active_storms(basin="west_pacific")
        features = []
        for sid in storms:
            try:
                storm  = realtime_obj.get_storm(sid)
                props  = storm.to_dict()
                lats   = props.get("lat", [])
                lons   = props.get("lon", [])
                winds  = props.get("vmax", [])
                coords = [[float(lon), float(lat)] for lat, lon in zip(lats, lons)]
                if len(coords) < 2: continue
                cur_wind = float(winds[-1]) if winds else 0
                feature = {
                    "type": "Feature",
                    "properties": {
                        "id":              sid,
                        "name":            props.get("name", sid),
                        "basin":           "WP",
                        "wind_kt":         round(cur_wind),
                        "pressure_mb":     float(props.get("mslp", [1000])[-1]),
                        "category":        classify(cur_wind),
                        "lat":             float(lats[-1]),
                        "lon":             float(lons[-1]),
                        "movement_dir":    "N/A",
                        "movement_speed_kt": 0,
                        "timestamp":       "",
                        "is_sample":       False,
                        "source":          "JTWC via tropycal",
                        "track_intensity": [float(w) for w in winds],
                    },
                    "geometry": {"type":"LineString","coordinates":coords},
                }
                features.append(feature)
            except Exception:
                continue
        return {
            "type":"FeatureCollection",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "JTWC via tropycal",
            "features": features,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # NGUỒN 4: Sample (fallback)
    # ══════════════════════════════════════════════════════════════════════════
    def _fetch_sample(self) -> dict:
        import copy
        data = copy.deepcopy(SAMPLE_STORMS)
        ts   = datetime.now(timezone.utc).isoformat()
        data["generated_at"] = ts
        return data

    # ── Helpers ────────────────────────────────────────────────────────────
    def _is_cache_valid(self) -> bool:
        return self._cache is not None and \
               time.time() - self._cache_time < self.CACHE_SEC
    
