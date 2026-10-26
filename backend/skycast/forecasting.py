"""Features, baselines and models for 1-7 day forecasts of daily max/min temperature and rain.

Every forecast is issued on day t from observations up to and including day t, for target day
t + lead. Nothing in the feature set looks past day t, and the climatology is fitted on the
training period only, so a backtest cannot see its own future.

Methods
- persistence:  the target day will look like today (rain probability is today's 0 or 1).
- climatology:  the long-run average for the target calendar day (rain = how often it rained).
- gbm:          gradient-boosted trees (one model per target and lead) on the last week of
                weather, 7- and 30-day means, today's anomaly from climatology, and seasonality.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

LEADS = range(1, 8)
RAIN_MM = 1.0  # a "rain day" has at least 1 mm of precipitation
TEMPS = ("tmax", "tmin")
LAG_DAYS = 7
CLIM_WINDOW = 15  # days in the circular smoothing window for climatology


def day_of_year(index: pd.DatetimeIndex) -> np.ndarray:
    """1-366, with 29 February folded onto 28 February so leap years line up."""
    doy = index.dayofyear.to_numpy().copy()
    leap_after_feb = index.is_leap_year & (index.month > 2)
    doy[leap_after_feb] -= 1
    return doy


@dataclass
class Climatology:
    """Smoothed day-of-year means of tmax and tmin and the frequency of rain days."""

    table: pd.DataFrame = field(default_factory=pd.DataFrame)

    def fit(self, history: pd.DataFrame) -> "Climatology":
        frame = pd.DataFrame({"tmax": history["tmax"], "tmin": history["tmin"],
                              "rain": (history["precip"] >= RAIN_MM).astype(float)})
        frame["doy"] = day_of_year(history.index)
        daily = frame.groupby("doy").mean().reindex(range(1, 366)).interpolate(limit_direction="both")
        # Circular rolling mean so 31 December and 1 January smooth into each other.
        pad = CLIM_WINDOW // 2
        wrapped = pd.concat([daily.iloc[-pad:], daily, daily.iloc[:pad]])
        self.table = wrapped.rolling(CLIM_WINDOW, center=True).mean().iloc[pad:-pad]
        return self

    def at(self, dates: pd.DatetimeIndex) -> pd.DataFrame:
        values = self.table.loc[day_of_year(dates)].to_numpy()
        return pd.DataFrame(values, index=dates, columns=self.table.columns)


def build_features(history: pd.DataFrame, climatology: Climatology) -> pd.DataFrame:
    """One row per issue day t, using only observations up to t."""
    f = pd.DataFrame(index=history.index)
    for col in ("tmax", "tmin", "precip", "wind"):
        for lag in range(LAG_DAYS):
            f[f"{col}_lag{lag}"] = history[col].shift(lag)
    for col in TEMPS:
        f[f"{col}_mean7"] = history[col].rolling(7).mean()
        f[f"{col}_mean30"] = history[col].rolling(30).mean()
    f["precip_sum7"] = history["precip"].rolling(7).sum()
    f["rain_days7"] = (history["precip"] >= RAIN_MM).rolling(7).sum()
    clim_today = climatology.at(history.index)
    for col in TEMPS:
        f[f"{col}_anomaly"] = history[col] - clim_today[col]
    doy = day_of_year(history.index)
    f["season_sin"] = np.sin(2 * np.pi * doy / 365)
    f["season_cos"] = np.cos(2 * np.pi * doy / 365)
    return f


def add_target_climatology(features: pd.DataFrame, climatology: Climatology, lead: int) -> pd.DataFrame:
    """The target day's calendar date is known when the forecast is issued, so its climatology is fair input."""
    clim = climatology.at(features.index + pd.Timedelta(days=lead))
    out = features.copy()
    out["clim_tmax_target"] = clim["tmax"].to_numpy()
    out["clim_tmin_target"] = clim["tmin"].to_numpy()
    out["clim_rain_target"] = clim["rain"].to_numpy()
    return out


def targets(history: pd.DataFrame, lead: int) -> pd.DataFrame:
    future = history.shift(-lead)
    return pd.DataFrame({"tmax": future["tmax"], "tmin": future["tmin"],
                         "rain": (future["precip"] >= RAIN_MM).astype(float).where(future["precip"].notna())},
                        index=history.index)


@dataclass
class ForecastModel:
    """Gradient-boosted trees: one regressor per temperature and one classifier for rain, per lead."""

    seed: int = 42
    climatology: Climatology = field(default_factory=Climatology)
    models: dict = field(default_factory=dict)

    def fit(self, history: pd.DataFrame) -> "ForecastModel":
        self.climatology = Climatology().fit(history)
        base = build_features(history, self.climatology)
        for lead in LEADS:
            X = add_target_climatology(base, self.climatology, lead)
            y = targets(history, lead)
            ok = X.notna().all(axis=1) & y.notna().all(axis=1)
            for col in TEMPS:
                self.models[(col, lead)] = HistGradientBoostingRegressor(
                    max_iter=300, learning_rate=0.05, early_stopping=True, random_state=self.seed,
                ).fit(X[ok], y.loc[ok, col])
            self.models[("rain", lead)] = HistGradientBoostingClassifier(
                max_iter=300, learning_rate=0.05, early_stopping=True, random_state=self.seed,
            ).fit(X[ok], y.loc[ok, "rain"].astype(int))
        return self

    def predict(self, history: pd.DataFrame, issue_dates: pd.DatetimeIndex) -> pd.DataFrame:
        """Rows: (issue_date, lead). Columns: tmax, tmin, rain_probability."""
        base = build_features(history, self.climatology).loc[issue_dates]
        rows = []
        for lead in LEADS:
            X = add_target_climatology(base, self.climatology, lead)
            ok = X.notna().all(axis=1)
            frame = pd.DataFrame(index=X.index[ok])
            frame["lead"] = lead
            for col in TEMPS:
                frame[col] = self.models[(col, lead)].predict(X[ok])
            frame["rain_probability"] = self.models[("rain", lead)].predict_proba(X[ok])[:, 1]
            rows.append(frame)
        return pd.concat(rows).rename_axis("issue_date").reset_index()


def persistence(history: pd.DataFrame, issue_dates: pd.DatetimeIndex) -> pd.DataFrame:
    today = history.loc[issue_dates]
    return pd.concat([pd.DataFrame({"issue_date": issue_dates, "lead": lead, "tmax": today["tmax"].to_numpy(),
                                    "tmin": today["tmin"].to_numpy(),
                                    "rain_probability": (today["precip"] >= RAIN_MM).astype(float).to_numpy()})
                      for lead in LEADS], ignore_index=True)


def climatology_forecast(climatology: Climatology, issue_dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for lead in LEADS:
        clim = climatology.at(issue_dates + pd.Timedelta(days=lead))
        rows.append(pd.DataFrame({"issue_date": issue_dates, "lead": lead, "tmax": clim["tmax"].to_numpy(),
                                  "tmin": clim["tmin"].to_numpy(), "rain_probability": clim["rain"].to_numpy()}))
    return pd.concat(rows, ignore_index=True)
