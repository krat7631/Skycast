import os
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib

def train_model(city, country):
    # Clean file names
    city_clean = city.replace(" ", "_")
    country_clean = country.replace(" ", "_")

    filename = f"data/{city_clean}_{country_clean}.csv"
    if not os.path.exists(filename):
        raise FileNotFoundError(f"❌ Dataset not found: {filename}")

    # Load dataset
    df = pd.read_csv(filename)

    if df.empty:
        raise ValueError(f"❌ Empty dataset for: {filename}")

    # Extract features from date
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    if df["date"].isnull().any():
        raise ValueError("❌ Invalid dates found in dataset!")

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day

    # ✅ ADD THIS: drop rows with any NaN values
    df = df.dropna()

    # (Optional: check if after dropping we have data left)
    if df.empty:
        raise ValueError("❌ No data left after dropping NaNs.")

    # Prepare features and targets
    X = df[["year", "month", "day"]]
    y = df[["temperature_min", "precipitation", "wind_speed", "cloud_cover"]]

    # Simple train/test split (can improve later)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Save model
    os.makedirs("models", exist_ok=True)
    model_filename = f"models/{city_clean}_{country_clean}_weather_model.pkl"
    joblib.dump(model, model_filename)
    print(f"✅ Model trained and saved to {model_filename}")

# Manual test
if __name__ == "__main__":
    train_model(city="Vadodara", country="India")
