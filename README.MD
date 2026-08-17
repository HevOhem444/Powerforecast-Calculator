# PowerForecast ⚡

**PowerForecast** is a high-precision Philippine Meralco Electricity Rates API and Interactive Web Calculator. It parses official Meralco PDF rate bulletins to provide real-time, itemized breakdowns of monthly electricity bills—including Generation, Transmission, System Loss, Distribution tiers, Subsidies, VAT, and local franchise taxes.

---

## ✨ Features

- ⚡ **Dynamic Meralco Rate Parser**: Automatically fetches and extracts effective rates and Base Generation Charges from official Meralco PDF bulletins.
- 🌐 **Vercel Serverless API**: Ready for Vercel deployment with CORS-enabled endpoints (`/api/rates`, `/api/appliances`, `/api/calculate`).
- 📊 **Interactive Web Calculator**: Modern glassmorphic front-end displaying itemized bill breakdowns, stacked cost distribution bars, and consumption sliders.
- 🧪 **Interactive API Playground**: Includes a live documentation page (`docs.html`) with executable code snippets in **JavaScript**, **cURL**, and **Python**.
- 🐍 **Standalone Python Backend**: Ships with a functional Python server (`server.py`) for local execution and development.

---

## 🚀 Quick Start (Local Development)

### 1. Clone the Repository
```bash
git clone https://github.com/HevOhem444/Powerforecast_meralco_api.git
cd Powerforecast_meralco_api
```

### 2. Install Dependencies
Ensure Python 3.9+ is installed:
```bash
pip install -r requirements.txt
```

### 3. Start the PowerForecast Server
Run the unified Python web & API server:
```bash
python server.py 8000
```

Access locally at:
- **Web Calculator**: [http://localhost:8000](http://localhost:8000)
- **API Documentation & Playground**: [http://localhost:8000/docs.html](http://localhost:8000/docs.html)

---

## ☁️ Deploying to Vercel

PowerForecast is pre-configured for instant Vercel deployment with Serverless Functions (`vercel.json`).

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to Vercel
vercel --prod
```

### 🔑 AI Vision API Key & Fallback Configuration (Vercel & Local)

PowerForecast features an **automatic multi-key fallback system**. You can configure more than 1 Gemini API key in your Vercel Project Settings (`Settings > Environment Variables`) or local `.env.local` file. If the primary key hits quota, rate limits, or errors, the server automatically rotates to the next available fallback key seamlessly:

| Environment Variable | Description | Example |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Primary Gemini API Key | `AIzaSy...` |
| `GEMINI_API_KEY_2` | Second Fallback API Key | `AIzaSy...` |
| `GEMINI_API_KEY_3` | Third Fallback API Key | `AIzaSy...` |
| `GEMINI_API_KEY_FALLBACK` | Named Fallback API Key | `AIzaSy...` |
| `GEMINI_API_KEYS` | Comma-separated list of multiple keys | `key1,key2,key3` |

---

## 📡 API Endpoints

All endpoints support CORS (`Access-Control-Allow-Origin: *`).

### 1. `GET /api/rates`
Returns the latest parsed rate schedule per consumption bracket (kWh).

### 2. `GET /api/appliances`
Returns average wattage metrics and operational ranges for common Philippine household appliances.

### 3. `POST /api/calculate`
Calculates a fully itemized Meralco bill.

#### Request Body:
```json
{
  "kwh": 300,
  "generation_rate": 9.2504,
  "other_charges": 0.00
}
```

---

## 📂 Project Structure

* `index.html` — Interactive Web Calculator front-end.
* `docs.html` — Interactive API Documentation & Testing Playground.
* `API.md` — Technical API documentation and JSON schemas.
* `vercel.json` — Vercel deployment, rewrites, and CORS headers.
* `server.py` — Functional Python web and API server.
* `meralco_parser.py` — Meralco PDF rate parsing engine.
* `rates.json` — Local cache of latest parsed rate components.
* `appliance_db.json` — Philippine appliance wattage database.
* `api/` — Serverless Python functions (`rates.py`, `appliances.py`, `calculate.py`).

---

## ⚖️ Disclaimer
This application is not affiliated with, endorsed by, or associated with Manila Electric Company (MERALCO). Calculations are estimates based on parsed rate schedules and standard billing formulas.
