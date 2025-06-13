"use client";

import { useState } from "react";
import WeatherResult from "./WeatherResult";

export default function WeatherForm() {
  const [forecast, setForecast] = useState<any>(null);
  const [form, setForm] = useState({
    year: "",
    month: "",
    day: "",
    city: "",
    state: "",
    country: ""
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const dummyData = {
      temp_min: 26.5,
      precipitation: 9.2,
      wind_speed: 25.6,
      cloud_cover: 98.1
    };

    setForecast(dummyData);
  };

  return (
    <div className="max-w-md w-full space-y-4">
      <h1 className="text-2xl font-bold">Skycast 🌤️</h1>
      <form className="space-y-2" onSubmit={handleSubmit}>
        {["year", "month", "day", "city", "state", "country"].map(field => (
          <input
            key={field}
            name={field}
            value={(form as any)[field]}
            onChange={handleChange}
            placeholder={field}
            className="w-full p-2 border rounded"
            required
          />
        ))}
        <button className="px-4 py-2 bg-blue-500 text-white rounded">Get Forecast</button>
      </form>

      {forecast && <WeatherResult forecast={forecast} />}
    </div>
  );
}