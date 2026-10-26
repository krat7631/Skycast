# Skycast

How far ahead can a city's own weather history predict its weather? Skycast trains gradient-boosted models
on 25+ years of daily observations for any place, forecasts 1–7 days ahead, and backtests every forecast
against the baselines it has to beat — and against physics-based numerical weather prediction (NWP).

- **Data:** Open-Meteo's ERA5-based archive (daily max/min temperature, precipitation, wind since 2000),
  its archived NWP forecasts, and its geocoder. No API keys.
- **Model:** one gradient-boosted regressor per temperature and one classifier for rain (≥ 1 mm), per lead
  time, on the last week of weather, 7- and 30-day means, today's anomaly from normal, and seasonality.
- **Evaluation:** rolling-origin backtest, 2019–2025: every year is forecast day by day by a model trained only
  on earlier years, in six cities across six climates.
- **App:** FastAPI backend + Next.js frontend. Search any place; the model is trained on demand (~20 s,
  then cached) and shown next to climatology and the live NWP forecast.
- **Stack:** Python · scikit-learn · pandas · FastAPI · Next.js · TypeScript · pytest.

## Results

Mean absolute error of the daily maximum temperature, 2019–2025 (each year forecast by a model trained on
earlier years only):

| City | Climate | Skycast, 1 day | Persistence, 1 day | Climatology | **NWP, ≈1 day** | Skycast, 7 days |
|---|---|---|---|---|---|---|
| London | Oceanic | 1.67 °C | 1.78 | 2.63 | **0.75** | 2.60 |
| New York | Humid continental | 2.75 °C | 3.17 | 3.47 | **0.99** | 3.47 |
| Tokyo | Humid subtropical | 2.09 °C | 2.32 | 2.87 | **0.96** | 2.70 |
| Sydney | Humid subtropical (coastal) | 1.97 °C | 2.47 | 2.45 | **0.99** | 2.45 |
| Phoenix | Hot desert | 1.69 °C | 1.91 | 3.15 | **0.79** | 3.22 |
| Mumbai | Tropical monsoon | 0.84 °C | 0.86 | 1.43 | 1.01 | 1.40 |

NWP figures cover 2022–2025, the years with archived forecasts.

**What this shows**

1. **Skycast beats both statistical baselines one day ahead in every city**, with 19–46% lower error than
   climatology, and its rain probabilities beat climatology's at short range (Brier skill 4–29% at one day).
2. **That skill is almost gone by a week.** At seven days Skycast is within 0.2 °C of climatology everywhere —
   Tokyo keeps a 6% edge, and in Phoenix it is slightly worse (3.22 vs 3.15 °C), still leaning on recent
   weather that no longer says anything about next week. Most of the skill of local history alone is spent
   within two to three days.
3. **Physics-based NWP is 2–3× more accurate one day ahead** in five of six cities: it sees the whole
   atmosphere, not one place's past. Mumbai is the exception (NWP 1.01 °C vs Skycast 0.84 °C); I have not
   established why, so treat that row with care.

Full numbers by lead time, including minimum temperature and rain: [`backend/reports/backtest.json`](backend/reports/backtest.json).

### Checks on the comparison itself

- **No look-ahead.** Features for a forecast issued on day *t* use only data up to *t*, and the climatology
  baseline is fitted on the training years only. Both are unit-tested: changing every observation after *t*
  must leave the features at *t* unchanged.
- **NWP is compared on temperature only.** For Sydney and Mumbai, Open-Meteo's archived forecast precipitation
  is identical, day for day, to the archive's "observed" precipitation, so the two are not independent and a
  rain comparison would be circular. Temperatures agree on only 1–7% of days, consistent with independent
  sources. On rainy days the archived forecast's precipitation equals the "observed" value exactly 100% of the
  time for Sydney and Mumbai and about 1% elsewhere; the report records this share for each city.
- **The NWP comparison favours NWP somewhat.** Archived forecasts are stitched from each day's latest model
  run (lead ≤ 1 day), and the "observations" are themselves reanalysis — a model product — rather than
  station readings.

## How it works

```
backend/
  skycast/openmeteo.py    geocoding, archive, archived NWP and live forecast clients with on-disk caching
  skycast/forecasting.py  features, climatology, persistence, gradient-boosted models (21 per place)
  skycast/backtest.py     rolling-origin evaluation: MAE, Brier score and skill, ROC-AUC per lead time
  skycast/service.py      train-or-load per place per day, forecast, attach baselines and live NWP
  main.py                 FastAPI: /places, /forecast, /backtest
  scripts/run_backtests.py
frontend/                 Next.js: place search, 7-day forecast with baselines, backtest explorer
```

| Method | Forecast for day *t* + lead |
|---|---|
| Persistence | the weather on day *t* |
| Climatology | the "normal" for that calendar date: the training years' mean, smoothed over 15 days |
| Skycast | gradient-boosted trees trained for that lead time |
| NWP | Open-Meteo's operational forecast (archived, ≈1 day ahead) |

## Run it

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --port 8000          # API at http://localhost:8000
```

```bash
cd frontend && npm install && cp .env.example .env.local && npm run dev   # http://localhost:3000
```

Reproduce the backtest (about 6 minutes on a laptop; downloads ~0.4 MB per city):

```bash
cd backend && python scripts/run_backtests.py
```

Tests (no network needed; they use synthetic weather):

```bash
cd backend && pip install -r requirements-dev.txt && pytest -q && ruff check .
```

## Limitations

- A statistical model of one place's history cannot see weather systems approaching from elsewhere; beyond a
  few days it reverts to climatology. Skycast is a study of that limit, not a replacement for NWP.
- Observations are the ERA5 grid cell for each place (~25 km), not a single station, and the archive's most
  recent days are model estimates until reanalysis catches up.
- Six cities and seven years: differences of a tenth of a degree between methods are within noise.

Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
