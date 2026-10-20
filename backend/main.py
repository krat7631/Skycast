"""Skycast API.

Run from backend/:  uvicorn main:app --reload --port 8000
"""

import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from skycast.openmeteo import Location, LocationNotFound, geocode
from skycast.service import forecast

REPORT = Path(__file__).parent / "reports" / "backtest.json"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app = FastAPI(title="Skycast", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/places")
def places(q: str = Query(..., min_length=2, max_length=80)):
    try:
        return [loc.as_dict() for loc in geocode(q)]
    except LocationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Geocoding service unavailable.") from exc


@app.get("/forecast")
def forecast_endpoint(
    name: str = Query(..., max_length=80),
    country: str = Query("", max_length=80),
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    timezone: str = Query("auto", max_length=64),
):
    location = Location(name=name, country=country, latitude=latitude, longitude=longitude, timezone=timezone)
    try:
        return forecast(location)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Weather data service unavailable.") from exc


@app.get("/backtest")
def backtest_report():
    if not REPORT.exists():
        raise HTTPException(status_code=404, detail="Run scripts/run_backtests.py to generate the backtest report.")
    return json.loads(REPORT.read_text())
