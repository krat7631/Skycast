export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Place = {
  name: string;
  country: string;
  region: string | null;
  latitude: number;
  longitude: number;
  timezone: string;
};

export type DayForecast = {
  date: string;
  lead: number;
  model: { tmax: number; tmin: number; rain_probability: number };
  climatology: { tmax: number; tmin: number; rain_probability: number };
  nwp: { tmax: number | null; tmin: number | null; rain: boolean | null } | null;
};

export type ForecastResponse = {
  location: Place;
  issued_from: string;
  training_days: number;
  forecast: DayForecast[];
  recent_observations: { date: string; tmax: number; tmin: number; precip: number }[];
};

export type LeadScore = {
  n: number;
  mae_tmax: number;
  mae_tmin: number;
  brier_rain: number;
  auc_rain: number | null;
  skill_tmax: number;
  skill_rain: number;
};

export type CityBacktest = {
  location: Place;
  test_years: number[];
  history: { start: string; end: string; days: number };
  methods: Record<"gbm" | "persistence" | "climatology", Record<string, LeadScore>>;
  nwp_lead1: { years: number[]; n: number; mae_tmax: number; mae_tmin: number; brier_rain: number } | null;
};

export type BacktestReport = { generated_for_end_date: string; cities: CityBacktest[] };

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const query = params ? `?${new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]))}` : "";
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}${query}`);
  } catch {
    throw new Error(`Could not reach the Skycast API at ${API_BASE_URL}.`);
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body && typeof body.detail === "string" ? body.detail : `Request failed (HTTP ${response.status}).`;
    throw new Error(detail);
  }
  return body as T;
}

export const searchPlaces = (q: string) => get<Place[]>("/places", { q });

export const getForecast = (p: Place) =>
  get<ForecastResponse>("/forecast", {
    name: p.name, country: p.country, latitude: p.latitude, longitude: p.longitude, timezone: p.timezone,
  });

export const getBacktest = () => get<BacktestReport>("/backtest");
