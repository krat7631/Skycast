import numpy as np
import pandas as pd
import pytest

from skycast.forecasting import (
    LEADS,
    Climatology,
    ForecastModel,
    build_features,
    climatology_forecast,
    day_of_year,
    persistence,
    targets,
)


def synthetic_history(years: int = 6, seed: int = 0) -> pd.DataFrame:
    """Seasonal temperatures with autocorrelated noise, so there is real signal to learn."""
    rng = np.random.default_rng(seed)
    index = pd.date_range("2010-01-01", periods=365 * years, freq="D")
    season = 10 * np.sin(2 * np.pi * (index.dayofyear - 110) / 365)
    noise = np.zeros(len(index))
    for i in range(1, len(index)):
        noise[i] = 0.8 * noise[i - 1] + rng.normal(0, 1.5)
    tmax = 15 + season + noise
    return pd.DataFrame({"tmax": tmax, "tmin": tmax - 8 + rng.normal(0, 1, len(index)),
                         "precip": np.where(rng.random(len(index)) < 0.3, rng.exponential(5, len(index)), 0.0),
                         "wind": 15 + rng.normal(0, 4, len(index))}, index=index)


def test_day_of_year_folds_leap_day():
    dates = pd.DatetimeIndex(["2024-02-28", "2024-02-29", "2024-03-01", "2023-03-01", "2024-12-31"])
    assert day_of_year(dates).tolist() == [59, 60, 60, 60, 365]


def test_features_never_use_future_observations():
    history = synthetic_history()
    clim = Climatology().fit(history)
    cutoff = history.index[1000]
    altered = history.copy()
    altered.loc[altered.index > cutoff, ["tmax", "tmin", "precip", "wind"]] += 50
    original = build_features(history, clim).loc[:cutoff]
    changed = build_features(altered, clim).loc[:cutoff]
    pd.testing.assert_frame_equal(original, changed)


def test_targets_are_the_future_day():
    history = synthetic_history(years=1)
    t = targets(history, lead=3)
    assert t["tmax"].iloc[0] == history["tmax"].iloc[3]
    assert t["tmax"].iloc[-3:].isna().all()


def test_climatology_is_fitted_only_on_its_input():
    history = synthetic_history()
    train = history.loc[:"2013-12-31"]
    future_changed = history.copy()
    future_changed.loc["2014":, "tmax"] += 30
    a = Climatology().fit(train).table
    b = Climatology().fit(future_changed.loc[:"2013-12-31"]).table
    pd.testing.assert_frame_equal(a, b)


def test_climatology_wraps_around_the_new_year():
    table = Climatology().fit(synthetic_history()).table
    assert len(table) == 365 and table.notna().all().all()
    assert abs(table["tmax"].iloc[0] - table["tmax"].iloc[-1]) < 1.0


def test_baselines_cover_every_lead():
    history = synthetic_history(years=2)
    issue = history.index[400:410]
    assert set(persistence(history, issue)["lead"]) == set(LEADS)
    assert len(climatology_forecast(Climatology().fit(history), issue)) == len(issue) * len(LEADS)


@pytest.fixture(scope="module")
def fitted():
    history = synthetic_history()
    train, test = history.loc[:"2014-12-31"], history.loc["2015-01-01":"2015-12-24"]
    return history, ForecastModel().fit(train), test.index


def test_model_beats_climatology_at_short_leads(fitted):
    history, model, issue = fitted
    pred = model.predict(history, issue)
    clim = climatology_forecast(model.climatology, issue)
    for lead in (1, 2):
        y = targets(history, lead).loc[issue]
        mae_model = np.abs(pred[pred.lead == lead].set_index("issue_date")["tmax"] - y["tmax"]).mean()
        mae_clim = np.abs(clim[clim.lead == lead].set_index("issue_date")["tmax"] - y["tmax"]).mean()
        assert mae_model < mae_clim


def test_rain_probabilities_are_probabilities(fitted):
    history, model, issue = fitted
    p = model.predict(history, issue)["rain_probability"]
    assert ((p >= 0) & (p <= 1)).all()
