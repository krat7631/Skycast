import pandas as pd
from fastapi.testclient import TestClient

import main
import skycast.service as service
from skycast.openmeteo import Location, LocationNotFound
from tests.test_forecasting import synthetic_history

client = TestClient(main.app)
PLACE = {"name": "Testville", "country": "Nowhere", "latitude": 10.0, "longitude": 20.0, "timezone": "UTC"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_places_returns_matches(monkeypatch):
    monkeypatch.setattr(main, "geocode", lambda q: [Location(**PLACE)])
    response = client.get("/places", params={"q": "Test"})
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Testville"


def test_places_not_found(monkeypatch):
    def nothing(q):
        raise LocationNotFound("No place found")

    monkeypatch.setattr(main, "geocode", nothing)
    assert client.get("/places", params={"q": "Atlantis"}).status_code == 404


def test_places_requires_a_query():
    assert client.get("/places", params={"q": "x"}).status_code == 422


def test_forecast_end_to_end_with_synthetic_history(monkeypatch, tmp_path):
    history = synthetic_history(years=4)
    monkeypatch.setattr(service, "fetch_history", lambda location: history)
    no_nwp = pd.DataFrame(columns=["tmax", "tmin", "precip"])
    monkeypatch.setattr(service, "fetch_live_forecast", lambda location: no_nwp)
    monkeypatch.setattr(service, "MODEL_DIR", tmp_path)

    response = client.get("/forecast", params=PLACE)

    assert response.status_code == 200
    body = response.json()
    assert body["issued_from"] == str(history.index.max().date())
    assert [d["lead"] for d in body["forecast"]] == list(range(1, 8))
    first = body["forecast"][0]
    assert first["date"] == str((history.index.max() + pd.Timedelta(days=1)).date())
    assert 0 <= first["model"]["rain_probability"] <= 1
    assert first["climatology"]["tmax"] is not None
    assert len(body["recent_observations"]) == 14
    assert list(tmp_path.glob("*.pkl")), "trained model should be cached"


def test_forecast_rejects_invalid_coordinates():
    assert client.get("/forecast", params={**PLACE, "latitude": 120}).status_code == 422
