"""Forecast for any place: fetch its history, train (or load the day's cached model), predict 1-7 days.

Forecasts are issued from the latest complete day in the archive (normally yesterday), so lead 1
is today. Each forecast day is returned with the climatology for that date and, where available,
the operational NWP forecast, so the model is always shown next to its baselines rather than on
its own.
"""

import pickle

import pandas as pd

from .forecasting import RAIN_MM, ForecastModel
from .openmeteo import CACHE_DIR, Location, fetch_history, fetch_live_forecast

MODEL_DIR = CACHE_DIR.parent / "models"


def trained_model(location: Location, history: pd.DataFrame) -> ForecastModel:
    """Train once per place per day; later requests load the pickled model."""
    path = MODEL_DIR / f"{location.slug}-{history.index.max().date().isoformat()}.pkl"
    if path.exists():
        with path.open("rb") as fh:
            return pickle.load(fh)
    model = ForecastModel().fit(history)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump(model, fh)
    return model


def _round(value: float | None, digits: int = 1) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value), digits)


def forecast(location: Location) -> dict:
    history = fetch_history(location)
    model = trained_model(location, history)
    issued_from = history.index.max()
    preds = model.predict(history, pd.DatetimeIndex([issued_from]))
    target_dates = issued_from + pd.to_timedelta(preds["lead"], unit="D")
    clim = model.climatology.at(pd.DatetimeIndex(target_dates))

    try:
        nwp = fetch_live_forecast(location)
    except Exception:  # the forecast still stands on its own if the NWP request fails
        nwp = pd.DataFrame(columns=["tmax", "tmin", "precip"])

    days = []
    for (_, row), target, (_, c) in zip(preds.iterrows(), target_dates, clim.iterrows(), strict=True):
        n = nwp.loc[target] if target in nwp.index else None
        days.append({
            "date": target.date().isoformat(),
            "lead": int(row["lead"]),
            "model": {"tmax": _round(row["tmax"]), "tmin": _round(row["tmin"]),
                      "rain_probability": _round(row["rain_probability"], 3)},
            "climatology": {"tmax": _round(c["tmax"]), "tmin": _round(c["tmin"]),
                            "rain_probability": _round(c["rain"], 3)},
            "nwp": None if n is None else {"tmax": _round(n["tmax"]), "tmin": _round(n["tmin"]),
                                           "rain": None if pd.isna(n["precip"]) else bool(n["precip"] >= RAIN_MM)},
        })

    recent = history.iloc[-14:]
    return {
        "location": location.as_dict(),
        "issued_from": issued_from.date().isoformat(),
        "training_days": int(len(history)),
        "forecast": days,
        "recent_observations": [{"date": d.date().isoformat(), "tmax": _round(r["tmax"]), "tmin": _round(r["tmin"]),
                                 "precip": _round(r["precip"])} for d, r in recent.iterrows()],
    }
