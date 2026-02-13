# Malim 🔋

**EV Battery Health API for the Swiss Market**

Malim analyzes electric vehicle battery health from charging data and generates Battery Value Passports for used car sales. Built for Swiss data sovereignty requirements.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Problem

When buying a used EV, the battery is the most expensive component (40-60% of vehicle value), but there's no standardized way to verify its health. Buyers face uncertainty, sellers can't prove quality.

## 💡 Solution

Malim provides:
- **SoH Analysis**: Calculate State of Health from real charging data
- **Health Grading**: Excellent → Critical classification with confidence scores
- **Degradation Prediction**: ML-based forecasting for 1-10 years
- **Battery Passport**: Verifiable certificate for used car transactions
- **Value Impact**: CHF-based price adjustment recommendations

## 🚀 Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/yourusername/malim.git
cd malim

# Start services
docker-compose up -d

# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
cp .env.example .env
# Edit .env with your settings

# Run
uvicorn src.main:app --reload
```

## 📊 API Endpoints

### Vehicles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/vehicles` | Register a vehicle |
| `GET` | `/api/v1/vehicles` | List all vehicles |
| `GET` | `/api/v1/vehicles/{id}` | Get vehicle details |
| `DELETE` | `/api/v1/vehicles/{id}` | Remove vehicle |

### Charging Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/vehicles/{id}/charging-sessions` | Add single session |
| `POST` | `/api/v1/vehicles/{id}/charging-sessions/bulk` | Bulk import sessions |
| `GET` | `/api/v1/vehicles/{id}/charging-sessions` | List sessions |

### Battery Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/reports/analyze` | Analyze battery health |
| `GET` | `/api/v1/reports/{id}` | Get report details |
| `POST` | `/api/v1/reports/passport/{vehicle_id}` | Generate passport |
| `GET` | `/api/v1/reports/passport/{id}/verify` | Verify passport |

### RAG Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat` | Ask battery questions |
| `POST` | `/api/v1/chat/knowledge` | Add knowledge document |
| `POST` | `/api/v1/chat/knowledge/seed` | Seed default knowledge |

## 📝 Example Usage

### 1. Register a Vehicle

```bash
curl -X POST http://localhost:8000/api/v1/vehicles \
  -H "Content-Type: application/json" \
  -d '{
    "make": "Tesla",
    "model": "Model 3",
    "year": 2022,
    "battery_capacity_kwh": 60,
    "battery_type": "NMC",
    "mileage_km": 45000
  }'
```

### 2. Add Charging Data

```bash
curl -X POST http://localhost:8000/api/v1/vehicles/{vehicle_id}/charging-sessions/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {
      "timestamp": "2024-01-15T10:00:00",
      "start_soc": 0.2,
      "end_soc": 0.8,
      "energy_kwh": 35,
      "duration_minutes": 60,
      "charger_power_kw": 11,
      "temperature_c": 20,
      "is_fast_charge": false
    }
  ]'
```

### 3. Analyze Battery Health

```bash
curl -X POST http://localhost:8000/api/v1/reports/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "{vehicle_id}",
    "include_prediction": true,
    "prediction_years": 5
  }'
```

**Response:**
```json
{
  "report_id": "e0ef9dd0-16ca-4d45-a943-4ec93e44146f",
  "soh_percent": 92.0,
  "health_grade": "good",
  "health_summary": "Guter Zustand (92%). Normale Alterung, volle Alltagstauglichkeit.",
  "estimated_capacity_kwh": 55.2,
  "risk_factors": ["Häufiges Laden über 85% erhöht Zellstress"],
  "recommendations": ["Ladelimit auf 80% setzen für Alltagsnutzung"],
  "value_impact_chf": -2400,
  "prediction": {
    "soh_1_year": 89.5,
    "soh_3_year": 84.2,
    "soh_5_year": 79.1
  }
}
```

### 4. Generate Battery Passport

```bash
curl -X POST http://localhost:8000/api/v1/reports/passport/{vehicle_id}
```

**Response:**
```json
{
  "passport_id": "20c8175c-1f5e-46ce-a9a3-b94aaeaa8022",
  "make": "Tesla",
  "model": "Model 3",
  "soh_percent": 92.0,
  "health_grade": "good",
  "certification_hash": "59D4BA260221DB65",
  "valid_until": "2027-12-31"
}
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      FastAPI                            │
├─────────────┬─────────────┬─────────────┬──────────────┤
│  Vehicles   │  Sessions   │   Reports   │    Chat      │
├─────────────┴─────────────┴─────────────┴──────────────┤
│                    Services Layer                       │
├─────────────┬─────────────┬─────────────┬──────────────┤
│ SoH Calc    │ Degradation │ Passport    │ RAG Engine   │
├─────────────┴─────────────┴─────────────┴──────────────┤
│                   Adapters (Plug & Play)                │
├─────────────────────────────┬──────────────────────────┤
│   PostgreSQL + pgvector     │    Azure AI Search       │
│   (Self-hosted)             │    (Switzerland North)   │
└─────────────────────────────┴──────────────────────────┘
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | development / production | development |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `VECTOR_STORE` | `pgvector` or `azure` | pgvector |
| `LLM_PROVIDER` | `openai`, `azure`, or `ollama` | openai |
| `OPENAI_API_KEY` | OpenAI API key (for RAG chat) | Optional |

### Vector Store Options

**pgvector (Default)** - Self-hosted, full data control
```env
VECTOR_STORE=pgvector
DATABASE_URL=postgresql://user:pass@localhost:5432/malim
```

**Azure AI Search** - Managed service, Switzerland North region
```env
VECTOR_STORE=azure
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-key
```

### LLM Provider Options

**OpenAI**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**Azure OpenAI**
```env
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

**Ollama (Local)**
```env
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
```

## 🔬 Health Grading System

| Grade | SoH Range | Description |
|-------|-----------|-------------|
| 🟢 Excellent | ≥95% | Like new, full warranty value |
| 🟢 Good | 85-94% | Normal aging, full daily usability |
| 🟡 Fair | 75-84% | Noticeable degradation, reduced range |
| 🟠 Poor | 65-74% | Significant wear, limited use |
| 🔴 Critical | <65% | Replacement recommended |

## 🧪 Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

## 🚢 Deployment

### Render.com

1. Connect your GitHub repo
2. Render auto-detects `render.yaml`
3. Set environment variables in dashboard
4. Deploy!

### Docker Production

```bash
# Build
docker build -t malim:latest .

# Run with external database
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e OPENAI_API_KEY=sk-... \
  malim:latest
```

## 🇨🇭 Swiss Market Focus

- **Data Sovereignty**: All data stays in Switzerland (pgvector self-hosted or Azure Switzerland North)
- **Language**: German responses by default
- **Currency**: CHF value impact calculations
- **Compliance**: GDPR-ready, audit logging

## 📈 Roadmap

- [ ] OBD-II direct data import
- [ ] Tesla API integration
- [ ] PDF passport export
- [ ] Mobile app
- [ ] Dealer portal
- [ ] Insurance API integration

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines first.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with ❤️ in Switzerland 🇨🇭
