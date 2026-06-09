import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from app import app, fetcher
from data.fetcher import StormRealtimeFetcher, classify
import data.similarity as similarity


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
    monkeypatch.setattr(f, "_fetch_tropycal", fail)

    data = f.get_active_storms(force_refresh=True)

    assert data["type"] == "FeatureCollection"
    assert data["features"]
    assert data["features"][0]["properties"]["is_sample"] is True


def test_api_smoke(monkeypatch):
    client = app.test_client()

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

    assert client.get("/api/status").status_code == 200
    assert client.get("/api/historical-storms").status_code == 200
    active = client.get("/api/active-storms")
    assert active.status_code == 200
    assert "features" in active.get_json()
    forecast = client.get("/api/forecast/sample")
    assert forecast.status_code == 200
    assert "cone_points" in forecast.get_json()
