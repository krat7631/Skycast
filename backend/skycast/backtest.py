"""Rolling-origin backtest: for each test year, train on every earlier year and forecast the
test year day by day, exactly as the model would have been used at the time.

Metrics per method and lead time
- MAE of daily max and min temperature (°C).
- Brier score of the rain probability (mean squared error of a probability; lower is better),
  and its skill relative to climatology: 1 - Brier / Brier_climatology.
- ROC-AUC of the rain probability.

The NWP column uses Open-Meteo's archived forecasts, available from 2022. They are stitched
from each day's latest model run, so they are compared at lead 1 only, and for temperature
only: for some locations (Sydney and Mumbai among the showcase cities) the archived forecast
precipitation is identical, day for day, to the archive's "observed" precipitation, so the two
are not independent and a rain comparison would be circular. Temperatures match on only a few
percent of days, consistent with independent sources.
"""

from datetime import date

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .forecasting import LEADS, RAIN_MM, ForecastModel, climatology_forecast, persistence, targets
from .openmeteo import Location, fetch_archived_forecast, fetch_history

NWP_START_YEAR = 2022


def _score(pred: pd.DataFrame, history: pd.DataFrame) -> dict:
    rows = {}
    for lead in LEADS:
        p = pred[pred["lead"] == lead].set_index("issue_date")
        y = targets(history, lead).reindex(p.index)
        ok = y.notna().all(axis=1) & p[["tmax", "tmin", "rain_probability"]].notna().all(axis=1)
        p, y = p[ok], y[ok]
        rows[lead] = {
            "n": int(len(p)),
            "mae_tmax": float(np.abs(p["tmax"] - y["tmax"]).mean()),
            "mae_tmin": float(np.abs(p["tmin"] - y["tmin"]).mean()),
            "brier_rain": float(((p["rain_probability"] - y["rain"]) ** 2).mean()),
            "auc_rain": float(roc_auc_score(y["rain"], p["rain_probability"])) if y["rain"].nunique() == 2 else None,
        }
    return rows


def _nwp_lead1(location: Location, history: pd.DataFrame, years: list[int]) -> dict | None:
    years = [y for y in years if y >= NWP_START_YEAR]
    if not years:
        return None
    nwp = fetch_archived_forecast(location, date(years[0], 1, 1), date(years[-1], 12, 31))
    observed = history.reindex(nwp.index)
    ok = nwp[["tmax", "tmin"]].notna().all(axis=1) & observed[["tmax", "tmin"]].notna().all(axis=1)
    nwp, observed = nwp[ok], observed[ok]
    rainy = (nwp["precip"] >= RAIN_MM) | (observed["precip"] >= RAIN_MM)
    return {
        "years": years,
        "n": int(len(nwp)),
        "mae_tmax": float(np.abs(nwp["tmax"] - observed["tmax"]).mean()),
        "mae_tmin": float(np.abs(nwp["tmin"] - observed["tmin"]).mean()),
        # Recorded so the circularity is visible in the report: on rainy days, how often the
        # archived forecast's precipitation equals the "observed" value exactly.
        "rainy_day_precip_identical_share": float((nwp["precip"][rainy] == observed["precip"][rainy]).mean()),
    }


def _pooled(per_year: list[dict]) -> dict:
    """Combine yearly scores, weighting each year by its number of forecasts."""
    out = {}
    for lead in LEADS:
        parts = [y[lead] for y in per_year]
        n = sum(p["n"] for p in parts)
        out[lead] = {"n": n}
        for metric in ("mae_tmax", "mae_tmin", "brier_rain", "auc_rain"):
            values = [(p[metric], p["n"]) for p in parts if p[metric] is not None]
            out[lead][metric] = round(sum(v * w for v, w in values) / sum(w for _, w in values), 4) if values else None
    return out


def backtest(location: Location, test_years: list[int], end: date) -> dict:
    history = fetch_history(location, end=end)
    per_method: dict[str, list[dict]] = {"persistence": [], "climatology": [], "gbm": []}
    for year in test_years:
        train = history.loc[: f"{year - 1}-12-31"]
        issue = history.loc[f"{year}-01-01": f"{year}-12-31"].index
        model = ForecastModel().fit(train)
        per_method["gbm"].append(_score(model.predict(history, issue), history))
        per_method["persistence"].append(_score(persistence(history, issue), history))
        per_method["climatology"].append(_score(climatology_forecast(model.climatology, issue), history))

    pooled = {method: _pooled(scores) for method, scores in per_method.items()}
    for method in pooled:
        for lead in LEADS:
            clim = pooled["climatology"][lead]
            score = pooled[method][lead]
            score["skill_tmax"] = round(1 - score["mae_tmax"] / clim["mae_tmax"], 4)
            score["skill_rain"] = round(1 - score["brier_rain"] / clim["brier_rain"], 4)
    return {
        "location": location.as_dict(),
        "test_years": test_years,
        "history": {"start": str(history.index.min().date()), "end": str(history.index.max().date()),
                    "days": int(len(history))},
        "methods": pooled,
        "nwp_lead1": _nwp_lead1(location, history, test_years),
    }
