import type { ForecastResponse } from "@/lib/api";

import { LineChart, type Series } from "./LineChart";

const COLORS = { observed: "#F4F3F0", model: "#93B4FF", nwp: "#F2A65A", climatology: "#7C8496" };

function shortDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export function ForecastView({ data }: { data: ForecastResponse }) {
  const observed = data.recent_observations;
  const offset = observed.length; // x = 0..13 observed, 14.. forecast days
  const xOf = (i: number) => i;
  const series: Series[] = [
    { name: "Observed", color: COLORS.observed, points: observed.map((o, i) => ({ x: xOf(i), y: o.tmax })) },
    { name: "Skycast model", color: COLORS.model,
      points: [{ x: offset - 1, y: observed.at(-1)?.tmax ?? null },
        ...data.forecast.map((d, i) => ({ x: offset + i, y: d.model.tmax }))] },
    { name: "Open-Meteo NWP forecast", color: COLORS.nwp, dashed: true,
      points: data.forecast.map((d, i) => ({ x: offset + i, y: d.nwp?.tmax ?? null })) },
    { name: "Climatology", color: COLORS.climatology, dashed: true,
      points: data.forecast.map((d, i) => ({ x: offset + i, y: d.climatology.tmax })) },
  ];
  const labels = [...observed.map((o) => o.date), ...data.forecast.map((d) => d.date)]
    .map((iso, i) => ({ x: i, label: shortDate(iso) }))
    .filter((_, i) => i % 3 === 0);

  return (
    <div className="stack">
      <p className="note">
        Issued from <strong>{shortDate(data.issued_from)}</strong>, the latest complete day in the archive, by a
        model trained on {data.training_days.toLocaleString()} days of history. The archive&apos;s most recent days
        are model estimates until reanalysis catches up. The NWP line is today&apos;s operational forecast, shown for
        comparison.
      </p>

      <div className="days">
        {data.forecast.map((d) => (
          <article key={d.date} className="day">
            <header>
              <span className="mono">+{d.lead}d</span>
              <span>{shortDate(d.date)}</span>
            </header>
            <p className="temps">
              <strong>{Math.round(d.model.tmax)}°</strong> <span className="muted">{Math.round(d.model.tmin)}°</span>
            </p>
            <p className="rain">{Math.round(d.model.rain_probability * 100)}% rain</p>
            <dl>
              <dt>NWP</dt>
              <dd>{d.nwp?.tmax == null ? "—" : `${Math.round(d.nwp.tmax)}° / ${Math.round(d.nwp.tmin ?? 0)}°`}</dd>
              <dt>Normal</dt>
              <dd>{Math.round(d.climatology.tmax)}° / {Math.round(d.climatology.tmin)}°</dd>
            </dl>
          </article>
        ))}
      </div>

      <LineChart series={series} xLabels={labels} yLabel="Daily max °C" highlightFrom={offset - 0.5}
        highlightLabel="forecast" ariaLabel="Recent observed maximum temperatures followed by the 7-day forecast" />
    </div>
  );
}
