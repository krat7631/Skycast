"use client";

import { motion } from "framer-motion";

export default function WeatherResult({ forecast }: { forecast: any }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 p-4 border rounded bg-white shadow"
    >
      <h2 className="text-xl font-semibold mb-2">🌤️ Forecast Result</h2>
      <p>Temp Min: {forecast.temp_min} °C</p>
      <p>Precipitation: {forecast.precipitation} mm</p>
      <p>Wind Speed: {forecast.wind_speed} km/h</p>
      <p>Cloud Cover: {forecast.cloud_cover} %</p>
    </motion.div>
  );
}