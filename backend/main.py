from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd
import os
import traceback

from fetch_data import fetch_forecast_data
from train_weather_model import train_model

# CORS for frontend API calls
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Forecast input schema
class ForecastRequest(BaseModel):
    year: int
    month: int
    day: int
    city: str
    state: str = ""  # ✅ state is now optional (default empty)
    country: str

@app.post("/forecast/")
def get_forecast(request: ForecastRequest):
    city_clean = request.city.replace(" ", "_")
    country_clean = request.country.replace(" ", "_")
    model_path = f"models/{city_clean}_{country_clean}_weather_model.pkl"

    try:
        if not os.path.exists(model_path):
            print(f"⚠ Model for {request.city}, {request.country} not found. Auto-generating...")

            # Fetch data — pass state only if provided
            fetch_forecast_data(request.city, request.state, request.country)
            train_model(request.city, request.country)

        model = joblib.load(model_path)

        X_pred = pd.DataFrame([{
            "year": request.year,
            "month": request.month,
            "day": request.day
        }])

        prediction = model.predict(X_pred)[0]

        return {
            "temperature_min": prediction[0],
            "precipitation": prediction[1],
            "wind_speed": prediction[2],
            "cloud_cover": prediction[3]
        }

    except Exception as e:
        print("❌ Error occurred:", str(e))
        traceback.print_exc()
        return {"error": f"Internal Server Error: {str(e)}"}

@app.get("/")
def root():
    return {"message": "🌤 SkyCast Fully Automated API is running!"}
