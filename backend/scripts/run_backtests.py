"""Run the rolling-origin backtest for the showcase cities and write reports/backtest.json.

Six cities in different climates (temperate maritime, humid continental, humid subtropical,
oceanic, hot desert, tropical monsoon). Test years 2019-2025, each forecast by a model trained
only on earlier years. About 10 minutes on a laptop CPU.

Usage (from backend/):
    python scripts/run_backtests.py
    python scripts/run_backtests.py --cities London --years 2025   # quick check
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skycast.backtest import backtest  # noqa: E402
from skycast.openmeteo import geocode  # noqa: E402

# (query, expected country) — the country check guards against the geocoder picking a namesake.
CITIES = [("London", "United Kingdom"), ("New York", "United States"), ("Tokyo", "Japan"),
          ("Sydney", "Australia"), ("Phoenix", "United States"), ("Mumbai", "India")]
END = date(2025, 12, 31)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cities", nargs="*")
    parser.add_argument("--years", nargs="*", type=int, default=list(range(2019, 2026)))
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "backtest.json")
    args = parser.parse_args()

    cities = [c for c in CITIES if not args.cities or c[0] in args.cities]
    reports, started = [], time.time()
    for query, country in cities:
        location = next(loc for loc in geocode(query) if loc.country == country)
        city_started = time.time()
        report = backtest(location, args.years, END)
        reports.append(report)
        gbm, clim = report["methods"]["gbm"], report["methods"]["climatology"]
        print(f"{location.name}: MAE tmax lead1 {gbm[1]['mae_tmax']:.2f} vs clim {clim[1]['mae_tmax']:.2f}, "
              f"lead7 {gbm[7]['mae_tmax']:.2f} vs {clim[7]['mae_tmax']:.2f} "
              f"({time.time() - city_started:.0f}s, total {time.time() - started:.0f}s)", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"generated_for_end_date": END.isoformat(), "cities": reports}, indent=2))
    print(f"Wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
