# 🌤 Skycast — Machine Learning Weather Forecasting App

## 🎯 Project Goal

Skycast is an AI-powered weather forecasting application designed to predict key weather parameters for any given date and location. The system utilizes historical weather data and machine learning models to generate highly accurate forecasts. This project serves as both a practical demonstration of full-stack development skills and a showcase of modern ML deployment pipelines.

---

## 🔑 Key Features

- 📅 Predict weather for any future date using machine learning models.
- 🌎 Supports multiple cities and countries.
- 📊 Predicts:
  - Minimum Temperature
  - Precipitation
  - Wind Speed
  - Cloud Cover
- ⚙️ Fully automated backend that trains models on-the-fly if required.
- 🔄 Frontend communicates with backend via RESTful API.
- 🚀 Built with production-grade modern technologies.

---

## 🛠️ Technologies & Libraries Used

### 🔬 Machine Learning (Backend)

- **Prophet (Facebook Prophet):** Time-series forecasting model
- **Pandas:** Data manipulation & preprocessing
- **Pydantic:** Request validation and data parsing
- **Joblib:** Model serialization and storage
- **Requests:** API calls for fetching external weather data

### 🌐 Backend Framework

- **FastAPI:** High-performance Python web framework for APIs
- **Uvicorn:** ASGI server for running FastAPI apps

### 💻 Frontend Framework

- **Next.js 14:** React-based full-stack web framework
- **TypeScript:** Strongly-typed superset of JavaScript
- **Axios:** HTTP client for making API calls
- **TailwindCSS 4.0:** Utility-first CSS framework for rapid UI development

### ⚙️ Other Tooling

- **PostCSS:** CSS transformation pipeline
- **Autoprefixer:** Vendor prefixing for CSS compatibility

---

## 🔍 Summary

Skycast combines modern machine learning techniques with a full-stack web architecture to deliver real-time, automated weather forecasting. The app demonstrates integration of ML models into real-world applications while maintaining clean, scalable code across both frontend and backend stacks.
