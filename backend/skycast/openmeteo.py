"""Open-Meteo clients: geocoding, historical observations, archived and live NWP forecasts.

All endpoints are free for non-commercial use, need no API key, and are licensed CC BY 4.0
(attribution: Open-Meteo.com). Historical observations come from the ERA5-based archive. In
practice it returns values up to the current day, so the most recent days cannot be finished
reanalysis; Skycast uses them as the best available estimate and stops at yesterday, the last
complete day.
"""

import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx
import pandas as pd

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HISTORICAL_FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DAILY = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max"]
COLUMNS = {"temperature_2m_max": "tmax", "temperature_2m_min": "tmin",
           "precipitation_sum": "precip", "wind_speed_10m_max": "wind"}
HISTORY_START = date(2000, 1, 1)
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"
CACHE_MAX_AGE_SECONDS = 24 * 3600


class LocationNotFound(LookupError):
    pass


@dataclass(frozen=True)
class Location:
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    region: str | None = None

    @property
    def slug(self) -> str:
        key = f"{self.name}-{self.country}-{self.latitude:.2f}-{self.longitude:.2f}"
        return re.sub(r"[^a-z0-9]+", "-", key.lower())

    def as_dict(self) -> dict:
        return {"name": self.name, "country": self.country, "region": self.region,
                "latitude": self.latitude, "longitude": self.longitude, "timezone": self.timezone}


def _get(url: str, params: dict) -> dict:
    for attempt in range(3):
        response = httpx.get(url, params=params, timeout=30)
        if response.status_code == 429 and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("Open-Meteo rate limit exceeded")


def geocode(query: str, count: int = 5) -> list[Location]:
    data = _get(GEOCODING_URL, {"name": query, "count": count, "language": "en", "format": "json"})
    results = data.get("results") or []
    if not results:
        raise LocationNotFound(f"No place found for {query!r}.")
    return [Location(name=r["name"], country=r.get("country", ""), latitude=r["latitude"], longitude=r["longitude"],
                     timezone=r.get("timezone", "auto"), region=r.get("admin1")) for r in results]


def _daily_frame(payload: dict) -> pd.DataFrame:
    daily = payload.get("daily") or {}
    frame = pd.DataFrame(daily).rename(columns={"time": "date", **COLUMNS})
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date").sort_index()


def _cached(name: str, fetch) -> pd.DataFrame:
    path = CACHE_DIR / f"{name}.csv"
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_MAX_AGE_SECONDS:
        return pd.read_csv(path, index_col="date", parse_dates=["date"])
    frame = fetch()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path)
    return frame


def fetch_history(location: Location, end: date | None = None) -> pd.DataFrame:
    """Daily observations from 2000 to `end`. The default is yesterday: the archive also returns the
    current, unfinished day, whose max/min would be partial. Trailing days not yet in the archive
    are dropped."""
    end = end or date.today() - timedelta(days=1)

    def fetch() -> pd.DataFrame:
        payload = _get(ARCHIVE_URL, {"latitude": location.latitude, "longitude": location.longitude,
                                     "start_date": HISTORY_START.isoformat(), "end_date": end.isoformat(),
                                     "daily": ",".join(DAILY), "timezone": location.timezone})
        frame = _daily_frame(payload)
        last_complete = frame.dropna().index.max()
        return frame.loc[:last_complete]

    return _cached(f"{location.slug}-history-{end.isoformat()}", fetch)


def fetch_archived_forecast(location: Location, start: date, end: date) -> pd.DataFrame:
    """Archived NWP forecasts stitched from each day's most recent model run, so effectively a
    lead time of about one day. Used as the physics-based benchmark at lead 1 only."""
    def fetch() -> pd.DataFrame:
        payload = _get(HISTORICAL_FORECAST_URL, {"latitude": location.latitude, "longitude": location.longitude,
                                                 "start_date": start.isoformat(), "end_date": end.isoformat(),
                                                 "daily": ",".join(DAILY[:3]), "timezone": location.timezone})
        return _daily_frame(payload)

    return _cached(f"{location.slug}-nwp-{start.isoformat()}-{end.isoformat()}", fetch)


def fetch_live_forecast(location: Location, days: int = 14) -> pd.DataFrame:
    """Today's operational NWP forecast, for side-by-side display."""
    payload = _get(FORECAST_URL, {"latitude": location.latitude, "longitude": location.longitude,
                                  "daily": ",".join(DAILY[:3]), "forecast_days": days, "past_days": 7,
                                  "timezone": location.timezone})
    return _daily_frame(payload)


