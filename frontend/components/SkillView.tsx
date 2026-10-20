"use client";

import { useState } from "react";

import type { BacktestReport } from "@/lib/api";

import { LineChart, type Series } from "./LineChart";

const LEADS = [1, 2, 3, 4, 5, 6, 7];
const METHODS = [
  { key: "gbm", name: "Skycast model", color: "#93B4FF" },
  { key: "persistence", name: "Persistence (tomorrow = today)", color: "#9B91E8", dashed: true },
  { key: "climatology", name: "Climatology (normal for the date)", color: "#7C8496", dashed: true },
] as const;
const NWP_COLOR = "#F2A65A";

// Round to a whole percent without printing "-0%" for tiny negative values.
const pct = (fraction: number) => `${Math.round(fraction * 100) || 0}%`;

export function SkillView({ report }: { report: BacktestReport }) {
  const [index, setIndex] = useState(0);
  const city = report.cities[index];
  const years = `${city.test_years[0]}–${city.test_years.at(-1)}`;

  const maeSeries: Series[] = [
    ...METHODS.map((m) => ({
      name: m.name, color: m.color, dashed: "dashed" in m,
      points: LEADS.map((l) => ({ x: l, y: city.methods[m.key][l].mae_tmax })),
    })),
    ...(city.nwp_lead1
      ? [{ name: "Open-Meteo NWP (≈1 day ahead)", color: NWP_COLOR, dotsOnly: true,
          points: [{ x: 1, y: city.nwp_lead1.mae_tmax }] }]
      : []),
  ];
  const rainSeries: Series[] = METHODS.filter((m) => m.key !== "climatology").map((m) => ({
    name: m.name, color: m.color, dashed: "dashed" in m,
    points: LEADS.map((l) => ({ x: l, y: city.methods[m.key][l].skill_rain * 100 })),
  }));
  const leadLabels = LEADS.map((l) => ({ x: l, label: `${l}d` }));

  return (
    <div className="stack">
      <div className="tabs" role="tablist" aria-label="City">
        {report.cities.map((c, i) => (
          <button key={c.location.name} role="tab" aria-selected={i === index} type="button"
            className={i === index ? "tab tab-active" : "tab"} onClick={() => setIndex(i)}>
            {c.location.name}
          </button>
        ))}
      </div>

      <div className="grid-2">
        <div>
          <h3>Max temperature error by lead time</h3>
          <LineChart series={maeSeries} xLabels={leadLabels} yLabel="Mean absolute error °C"
            ariaLabel={`Forecast error by lead time in ${city.location.name}`} />
        </div>
        <div>
          <h3>Rain forecast skill vs climatology</h3>
          <LineChart series={rainSeries} xLabels={leadLabels} yLabel="Brier skill %"
            ariaLabel={`Rain forecast skill by lead time in ${city.location.name}`} />
        </div>
      </div>
      <p className="note">
        Each year {years} was forecast day by day by a model trained only on earlier years
        ({city.history.days.toLocaleString()} days of history from {city.history.start}). Skill above 0% means better
        than climatology. The NWP point uses archived operational forecasts from {city.nwp_lead1?.years[0] ?? "2022"}{" "}
        on, which are stitched from each day&apos;s latest model run, so it is a ≤1-day-ahead comparison.
      </p>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">City</th>
              <th scope="col" className="num">Model MAE 1d</th>
              <th scope="col" className="num">NWP MAE ≈1d</th>
              <th scope="col" className="num">Climatology MAE</th>
              <th scope="col" className="num">Model skill 1d</th>
              <th scope="col" className="num">Model skill 7d</th>
            </tr>
          </thead>
          <tbody>
            {report.cities.map((c) => (
              <tr key={c.location.name}>
                <td>{c.location.name}</td>
                <td className="num mono">{c.methods.gbm[1].mae_tmax.toFixed(2)}°</td>
                <td className="num mono">{c.nwp_lead1 ? `${c.nwp_lead1.mae_tmax.toFixed(2)}°` : "—"}</td>
                <td className="num mono">{c.methods.climatology[1].mae_tmax.toFixed(2)}°</td>
                <td className="num mono">{pct(c.methods.gbm[1].skill_tmax)}</td>
                <td className="num mono">{pct(c.methods.gbm[7].skill_tmax)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
