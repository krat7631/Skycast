"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { ForecastView } from "@/components/ForecastView";
import { SkillView } from "@/components/SkillView";
import { type BacktestReport, type ForecastResponse, getBacktest, getForecast, type Place, searchPlaces } from "@/lib/api";

type Status =
  | { kind: "idle" }
  | { kind: "error"; message: string }
  | { kind: "loading"; place: Place; started: number }
  | { kind: "done"; data: ForecastResponse };

const SUGGESTIONS = ["London", "Tokyo", "Mumbai", "Phoenix", "Sydney"];

export default function Home() {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<Place[]>([]);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [report, setReport] = useState<BacktestReport | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getBacktest().then(setReport).catch((e: Error) => setReportError(e.message));
  }, []);

  useEffect(() => {
    if (status.kind !== "loading") return;
    timer.current = setInterval(() => setElapsed(Math.round((Date.now() - status.started) / 1000)), 500);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [status]);

  async function search(event?: FormEvent, text = query) {
    event?.preventDefault();
    if (text.trim().length < 2) return;
    try {
      const found = await searchPlaces(text.trim());
      setMatches(found);
      if (found.length === 1) await choose(found[0]);
    } catch (e) {
      setMatches([]);
      setStatus({ kind: "error", message: (e as Error).message });
    }
  }

  async function choose(place: Place) {
    setMatches([]);
    setElapsed(0);
    setStatus({ kind: "loading", place, started: Date.now() });
    try {
      setStatus({ kind: "done", data: await getForecast(place) });
    } catch (e) {
      setStatus({ kind: "error", message: (e as Error).message });
    }
  }

  return (
    <main>
      <header className="masthead">
        <p className="eyebrow mono">Skycast · forecast skill explorer</p>
        <h1>How far ahead can a city&apos;s own weather history see?</h1>
        <p className="lede">
          Skycast trains gradient-boosted models on more than 25 years of daily observations for any place, forecasts the next
          seven days, and shows every forecast next to the two baselines it has to beat and a physics-based weather
          model it usually cannot.
        </p>
      </header>

      <section className="panel" aria-labelledby="forecast-heading">
        <h2 id="forecast-heading">Forecast a place</h2>
        <form className="search" onSubmit={search}>
          <label htmlFor="place" className="visually-hidden">City</label>
          <input id="place" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search a city…"
            autoComplete="off" maxLength={80} />
          <button type="submit" className="primary" disabled={status.kind === "loading"}>Search</button>
        </form>
        <div className="chips">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" className="chip" onClick={() => { setQuery(s); search(undefined, s); }}>{s}</button>
          ))}
        </div>

        {matches.length > 1 && (
          <ul className="matches" aria-label="Matching places">
            {matches.map((m) => (
              <li key={`${m.latitude},${m.longitude}`}>
                <button type="button" onClick={() => choose(m)}>
                  {m.name}<span className="muted">{[m.region, m.country].filter(Boolean).join(", ")}</span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <div aria-live="polite">
          {status.kind === "error" && <p className="error">{status.message}</p>}
          {status.kind === "loading" && (
            <p className="note">
              Downloading 25+ years of observations for {status.place.name} and training 21 models… {elapsed}s
              <br />
              <span className="muted">The first request for a place takes about 20 seconds; later ones are cached.</span>
            </p>
          )}
          {status.kind === "done" && (
            <>
              <h3 className="place">
                {status.data.location.name}
                <span className="muted"> {status.data.location.country}</span>
              </h3>
              <ForecastView data={status.data} />
            </>
          )}
        </div>
      </section>

      <section className="panel" aria-labelledby="skill-heading">
        <h2 id="skill-heading">How good is it? Seven years of backtests</h2>
        {report ? <SkillView report={report} /> : <p className="muted">{reportError ?? "Loading backtest…"}</p>}
      </section>

      <section className="section" aria-labelledby="limits-heading">
        <h2 id="limits-heading">Limitations</h2>
        <ul className="limits">
          <li>Beyond about three days, the model is barely better than the climatological normal: local history alone
            carries little information about the weather a week away.</li>
          <li>Physics-based numerical weather prediction, which sees the whole atmosphere, is far more accurate at short
            range. Skycast is a study of what statistical learning can and cannot do, not a replacement for it.</li>
          <li>&ldquo;Observations&rdquo; are the ERA5 reanalysis grid cell for each place, not a single weather station.</li>
        </ul>
        <p className="muted small">Weather data by Open-Meteo.com (CC BY 4.0).</p>
      </section>
    </main>
  );
}
