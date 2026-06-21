import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

import app as app_module
from app import app, fetcher
from backend.fetcher import StormRealtimeFetcher, classify
import backend.fetcher as fetcher_module
from backend.seasonal_forecast import build_seasonal_forecast
import backend.similarity as similarity


def _feature(sid, coords, wind=50, month=9):
    return {
        "type": "Feature",
        "properties": {
            "sid": sid,
            "name": sid,
            "season": 2024,
            "max_wind_kt": wind,
            "max_category": classify(wind),
            "track_points": [
                {"time": f"2024-{month:02d}-01 00:00:00"},
                {"time": f"2024-{month:02d}-02 00:00:00"},
                {"time": f"2024-{month:02d}-03 00:00:00"},
            ],
        },
        "geometry": {"type": "LineString", "coordinates": coords},
    }


def _season_feature(sid, year, month, coords):
    return {
        "type": "Feature",
        "properties": {
            "sid": sid,
            "name": sid,
            "season": year,
            "track_points": [
                {"time": f"{year}-{month:02d}-01 00:00:00", "lat": coords[0][1], "lon": coords[0][0]},
                {"time": f"{year}-{month:02d}-02 00:00:00", "lat": coords[-1][1], "lon": coords[-1][0]},
            ],
        },
        "geometry": {"type": "LineString", "coordinates": coords},
    }


@pytest.mark.parametrize(
    ("wind", "code"),
    [(33, "TD"), (34, "TS"), (47, "TS"), (48, "STS"), (63, "STS"), (64, "TY"), (98, "TY"), (99, "STY")],
)
def test_classify_thresholds(wind, code):
    assert classify(wind)["code"] == code


def test_similarity_returns_multifactor_scores(monkeypatch):
    storms = [
        _feature("target", [[120, 10], [119, 11], [118, 12], [117, 13]], 80, 9),
        _feature("same_shape", [[121, 10], [120, 11], [119, 12], [118, 13]], 75, 9),
        _feature("different_shape", [[120, 10], [121, 10], [122, 9], [123, 8]], 35, 1),
    ]
    monkeypatch.setattr(similarity, "_storms_cache", storms)
    monkeypatch.setattr(similarity, "_cache_loaded", True)
    similarity._norm_cache.clear()

    data = similarity.find_similar("target", top_k=2)

    assert "error" not in data
    assert len(data["similar"]) == 2
    assert all(item["sid"] != "target" for item in data["similar"])
    for field in [
        "combined_score",
        "dtw_score",
        "cosine_score",
        "wind_diff_kt",
        "month_diff",
        "start_distance_deg",
    ]:
        assert field in data["similar"][0]


def test_fetcher_falls_back_to_sample(monkeypatch):
    f = StormRealtimeFetcher()

    def fail():
        raise RuntimeError("offline")

    monkeypatch.setattr(f, "_fetch_jma", fail)
    monkeypatch.setattr(f, "_fetch_ibtracs_nrt", fail)

    data = f.get_active_storms(force_refresh=True)

    assert data["type"] == "FeatureCollection"
    assert data["features"]
    assert data["features"][0]["properties"]["is_sample"] is True


def test_fetcher_reads_current_jma_resources(monkeypatch):
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    payload = [
        {
            "part": "title",
            "issue": {"UTC": "2026-06-21T12:45:00Z"},
            "name": {"en": "Mekkhala"},
        },
        {
            "part": {"en": "Analysis"},
            "advancedHours": 0,
            "validtime": {"UTC": "2026-06-21T12:00:00Z"},
            "center": [16.7, 130.4],
            "track": {"preTyphoon": [[15.9, 132.2]], "typhoon": [[16.7, 130.4]]},
        },
        {
            "part": {"en": "Forecast for 12 hours ahead"},
            "advancedHours": 12,
            "validtime": {"UTC": "2026-06-22T00:00:00Z"},
            "center": [17.1, 129.5],
        },
    ]

    def fake_get(url, **_kwargs):
        if url.endswith("targetTc.json"):
            return Response([{"tropicalCyclone": "TC2608", "category": "TY"}])
        if url.endswith("TC2608/forecast.json"):
            return Response(payload)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(fetcher_module.requests, "get", fake_get)
    f = StormRealtimeFetcher()
    data = f._fetch_jma()

    assert data["source"] == "JMA Typhoon Map"
    feature = data["features"][0]
    assert feature["properties"]["name"] == "Mekkhala"
    assert feature["properties"]["wind_kt"] is None
    assert feature["properties"]["pressure_mb"] is None
    assert feature["properties"]["category"]["code"] == "JMA"
    assert feature["geometry"]["coordinates"][-1] == [130.4, 16.7]

    forecast = f.get_forecast("TC2608")
    assert [point["hour"] for point in forecast["cone_points"]] == [0, 12]
    assert forecast["cone_points"][0]["wind_kt"] is None


def test_seasonal_forecast_returns_probabilities():
    features = [
        _season_feature("a", 1981, 9, [[130, 14], [112, 19]]),
        _season_feature("b", 1982, 9, [[118, 12], [108, 15]]),
        _season_feature("c", 1983, 10, [[125, 15], [110, 17]]),
    ]
    climate = {
        9: {
            "year": 2026,
            "month": 9,
            "enso_phase": "El Nino",
            "oni": 1.2,
            "very_strong_el_nino_probability": 0.63,
            "sst_scs_anom_c": 0.2,
            "sst_phil_anom_c": 0.5,
            "source_note": "test",
        }
    }

    data = build_seasonal_forecast(year=2026, features=features, climate_rows=climate)
    row = data["months"][8]

    assert data["method"].startswith("historical_climatology")
    assert row["expected_storms"] > 0
    assert "genesis_region_probabilities" in row
    assert "landfall_region_probabilities" in row
    assert abs(sum(row["count_probabilities"].values()) - 1.0) < 0.01


def test_api_smoke(monkeypatch):
    client = app.test_client()

    monkeypatch.setattr(app_module, "ensure_historical_data", lambda force=False: {
        "checked": True,
        "updated": False,
        "used_fallback": False,
        "message": "test",
    })
    monkeypatch.setattr(fetcher, "get_active_storms", lambda force_refresh=False: {
        "type": "FeatureCollection",
        "source": "test",
        "features": [],
    })
    monkeypatch.setattr(fetcher, "get_forecast", lambda storm_id: {
        "storm_id": storm_id,
        "no_forecast": True,
        "cone_points": [],
    })
    monkeypatch.setattr(app_module, "build_dashboard_stats", lambda: {
        "summary": {"total_storms": 0},
        "by_decade": [],
        "by_month": [],
        "by_category": [],
        "by_region": [],
        "era_comparison": [],
        "top_strongest": [],
    })
    monkeypatch.setattr(app_module, "build_seasonal_forecast", lambda year=2026: {
        "year": year,
        "method": "test",
        "months": [],
        "sources": [],
        "limitations": [],
    })

    assert client.get("/api/status").status_code == 200
    assert client.get("/dashboard").status_code == 200
    assert client.get("/seasonal-forecast").status_code == 200
    assert client.get("/api/historical-storms").status_code == 200
    active = client.get("/api/active-storms")
    assert active.status_code == 200
    assert "features" in active.get_json()
    forecast = client.get("/api/forecast/sample")
    assert forecast.status_code == 200
    assert "cone_points" in forecast.get_json()
    dashboard = client.get("/api/dashboard-stats")
    assert dashboard.status_code == 200
    assert "summary" in dashboard.get_json()
    seasonal = client.get("/api/seasonal-forecast?year=2026")
    assert seasonal.status_code == 200
    assert seasonal.get_json()["year"] == 2026


def test_historical_endpoint_serves_existing_file_without_refresh(monkeypatch):
    client = app.test_client()
    calls = []

    def fail_if_called(force=False):
        calls.append(force)
        raise AssertionError("Historical data must not refresh during a normal map request")

    monkeypatch.setattr(app_module, "ensure_historical_data", fail_if_called)

    response = client.get("/api/historical-storms")

    assert response.status_code == 200
    assert calls == []


def test_update_historical_endpoint(monkeypatch):
    client = app.test_client()
    fake_geojson = ROOT / "tests" / "_tmp_storms_vn.geojson"
    fake_csv = ROOT / "tests" / "_tmp_ibtracs.csv"
    fake_geojson.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

    try:
        monkeypatch.setattr(app_module, "HISTORICAL_PATH", str(fake_geojson))
        monkeypatch.setattr(app_module.process_historical_data, "CACHE_FILE", str(fake_csv))
        monkeypatch.setattr(app_module, "ensure_historical_data", lambda force=False: {
            "checked": True,
            "updated": force,
            "used_fallback": False,
            "message": "mock update",
        })

        res = client.get("/api/update-historical?force=1")
        assert res.status_code == 200
        data = res.get_json()
        assert data["checked"] is True
        assert data["updated"] is True
        assert data["force"] is True
    finally:
        fake_geojson.unlink(missing_ok=True)
        fake_csv.unlink(missing_ok=True)
