# 🔋 Malim - EV Battery Health Platform

<p align="center">
  <img src="https://img.shields.io/badge/Made%20in-Switzerland%20🇨🇭-red" alt="Swiss Made">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
</p>

<p align="center">
  <strong>Intelligente Batteriegesundheits-Analyse für Elektrofahrzeuge</strong><br>
  <em>智能电动汽车电池健康分析平台</em>
</p>

---

## 🎯 Was ist Malim?

Malim ist eine SaaS-Plattform zur Analyse der Batteriegesundheit von Elektrofahrzeugen. Sie hilft EV-Besitzern, Händlern und Flottenmanagern, den Zustand und Wert ihrer Fahrzeugbatterien zu verstehen.

**Malim 是什么？**
Malim 是一个电动汽车电池健康分析 SaaS 平台，帮助车主、经销商和车队管理者了解电池状态和价值。

---

## ✨ Features / 功能

### 🔍 SoH-Analyse (State of Health)
- Berechnung des Batteriezustands aus Ladedaten
- 从充电数据计算电池健康状态
- Unterstützt NMC, LFP, NCA Batterietypen
- 支持 NMC、LFP、NCA 电池类型

### 📊 Gesundheitsbewertung
| Grade | SoH | Beschreibung |
|-------|-----|--------------|
| 🟢 Excellent | 95-100% | Wie neu / 如新 |
| 🟢 Good | 85-94% | Sehr gut / 非常好 |
| 🟡 Fair | 75-84% | Akzeptabel / 可接受 |
| 🟠 Poor | 65-74% | Eingeschränkt / 受限 |
| 🔴 Critical | <65% | Ersatz empfohlen / 建议更换 |

### 🎫 Battery Passport
- Zertifizierter Gesundheitsnachweis
- 认证的健康证明
- Blockchain-ready Hash-Verifizierung
- 区块链就绪的哈希验证
- PDF-Export für Verkauf/Versicherung
- PDF 导出用于销售/保险

### 📈 Degradations-Vorhersage
- ML-basierte Lebensdauer-Prognose
- 基于机器学习的寿命预测
- Wartungsempfehlungen
- 维护建议

### 💬 RAG Chat (Coming Soon)
- KI-Assistent für Batteriefragen
- 电池问题 AI 助手
- Basiert auf Fahrzeugdokumentation
- 基于车辆文档

### 💰 Wertberechnung
- CHF-Werteinfluss der Batteriegesundheit
- 电池健康对 CHF 价值的影响
- Schweizer Marktpreise
- 瑞士市场价格

---

## 🏗️ Technische Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue.js)                       │
│                   Swiss Green Theme 🇨🇭                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Vehicles   │  │   Reports   │  │    Chat     │         │
│  │    API      │  │     API     │  │    API      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  SoH Engine   │    │  Degradation  │    │  RAG Engine   │
│  Calculator   │    │   Predictor   │    │  (pgvector)   │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL + pgvector                     │
│         Vehicles │ Sessions │ Reports │ Embeddings          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technologie |
|-------|-------------|
| **Frontend** | Vue.js 3, Tailwind CSS |
| **Backend** | Python 3.11, FastAPI, Pydantic |
| **Database** | PostgreSQL 15, pgvector |
| **ML/AI** | NumPy, scikit-learn |
| **RAG** | OpenAI Embeddings, pgvector |
| **Deployment** | Docker, Render, GitHub Actions |
| **Infrastructure** | Terraform (Azure/AWS ready) |

---

## 📁 Projektstruktur

```
Malim/
├── src/
│   ├── api/                 # REST API Endpoints
│   │   ├── vehicles.py      # Fahrzeug-CRUD
│   │   ├── reports.py       # Analyse & Passport
│   │   ├── chat.py          # RAG Chat
│   │   └── health.py        # Health Check
│   ├── analysis/            # Analyse-Engine
│   │   ├── soh_calculator.py    # SoH Berechnung
│   │   ├── degradation.py       # ML Vorhersage
│   │   └── rag_engine.py        # RAG Chat Engine
│   ├── db/                  # Datenbank
│   │   ├── models.py        # SQLAlchemy Models
│   │   ├── session.py       # DB Session
│   │   └── migrations.py    # Schema Migration
│   ├── repositories/        # Data Access Layer
│   ├── services/            # Business Logic
│   ├── adapters/            # Vector Store Adapters
│   ├── config.py            # Konfiguration
│   └── main.py              # FastAPI App
├── frontend/
│   └── index.html           # Vue.js SPA
├── tests/                   # Pytest Tests
├── infra/                   # Terraform IaC
├── scripts/                 # Deploy Scripts
├── docker-compose.yml       # Local Development
├── Dockerfile               # Production Image
├── render.yaml              # Render Deployment
└── requirements.txt         # Python Dependencies
```

---

## 🚀 Quick Start

### Voraussetzungen / 前提条件
- Python 3.11+
- PostgreSQL 15+ (mit pgvector)
- Docker (optional)

### 1. Repository klonen
```bash
git clone https://github.com/AIB612/malim.git
cd malim
```

### 2. Umgebung einrichten
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Umgebungsvariablen
```bash
cp .env.example .env
# Bearbeite .env mit deinen Werten
```

### 4. Datenbank starten
```bash
# Mit Docker
docker-compose up -d db

# Oder lokale PostgreSQL mit pgvector
```

### 5. Server starten
```bash
uvicorn src.main:app --reload --port 8000
```

### 6. Frontend öffnen
```bash
open frontend/index.html
# Oder: http://localhost:8000 (static files)
```

---

## 🐳 Docker Deployment

```bash
# Alles starten
docker-compose up -d

# Nur API
docker build -t malim .
docker run -p 8000:8000 malim
```

---

## 📡 API Endpoints

### Vehicles
| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/api/v1/vehicles` | Alle Fahrzeuge |
| POST | `/api/v1/vehicles` | Fahrzeug erstellen |
| GET | `/api/v1/vehicles/{id}` | Fahrzeug Details |
| PUT | `/api/v1/vehicles/{id}` | Fahrzeug aktualisieren |
| DELETE | `/api/v1/vehicles/{id}` | Fahrzeug löschen |
| POST | `/api/v1/vehicles/{id}/charging-sessions` | Ladevorgang hinzufügen |

### Reports
| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| POST | `/api/v1/reports/analyze` | SoH Analyse starten |
| GET | `/api/v1/reports/{id}` | Report abrufen |
| POST | `/api/v1/reports/passport/{vehicle_id}` | Passport generieren |
| GET | `/api/v1/reports/passport/{id}/pdf` | Passport als PDF |

### Chat
| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| POST | `/api/v1/chat` | RAG Chat Anfrage |
| POST | `/api/v1/chat/ingest` | Dokumente indexieren |

### Health
| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/health` | Health Check |
| GET | `/health/ready` | Readiness Check |

---

## 🧪 Tests

```bash
# Alle Tests
pytest

# Mit Coverage
pytest --cov=src --cov-report=html

# Nur Unit Tests
pytest tests/test_soh.py -v
```

---

## 🔧 Konfiguration

| Variable | Beschreibung | Default |
|----------|--------------|---------|
| `DATABASE_URL` | PostgreSQL Connection | `postgresql://...` |
| `OPENAI_API_KEY` | OpenAI für RAG | - |
| `VECTOR_STORE` | `pgvector` oder `azure` | `pgvector` |
| `LOG_LEVEL` | Logging Level | `INFO` |

---

## 🗺️ Roadmap

- [x] SoH Berechnung aus Ladedaten
- [x] Gesundheitsbewertung (A-F Grade)
- [x] Battery Passport Generation
- [x] Vue.js Frontend
- [x] Swiss Green Theme 🇨🇭
- [ ] RAG Chat Integration
- [ ] PDF Export
- [ ] Mobile App (React Native)
- [ ] OBD-II Integration
- [ ] Tesla API Integration
- [ ] Blockchain Passport Verification

---

## 🤝 Contributing

Beiträge sind willkommen! / 欢迎贡献！

1. Fork das Repository
2. Feature Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen committen (`git commit -m 'Add AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request öffnen

---

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) für Details.

---

## 👩‍💻 Autor

**Sherry (Chenxue Branny)**
- 🌐 Basel, Switzerland
- 💼 [LinkedIn](https://linkedin.com/in/chenxuebranny)
- 🐙 [GitHub](https://github.com/AIB612)

---

<p align="center">
  Made with 💚 in Switzerland 🇨🇭
</p>
