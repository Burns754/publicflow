# PublicFlow Project Structure

```
publicflow/
├── README.md                    # 📖 Projekt-Übersicht
├── DEPLOYMENT.md                # 🚀 Deploy & Betrieb
├── requirements.txt             # 📦 Python Dependencies
├── .env.example                 # ⚙️  Konfiguration Template
│
├── backend/
│   ├── app.py                  # 🔵 FastAPI Haupt-App
│   ├── models.py               # 🗄️  SQLAlchemy ORM Models
│   ├── scraper.py              # 🕷️  Web Scraper für Ausschreibungen
│   └── matcher.py              # 🤖 KI-Matching Engine
│
├── frontend/
│   └── index.html              # 🌐 Single-Page UI
│
├── docker-compose.yml          # 🐳 Docker Orchestration
├── Dockerfile                  # 🐳 Docker Image
└── start.sh                    # ⚡ Quick Start Script

```

## 🎯 Architektur

```
┌─────────────────────────────────────────────────────┐
│                    PUBLICFLOW SYSTEM                │
└─────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────────┐
│   Frontend UI    │         │   API Gateway        │
│  (HTML/JS)       │────────▶│   (FastAPI)          │
│                  │         │  :8000               │
└──────────────────┘         └──────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
              ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
              │  Scraper  │   │  Matcher  │   │ Database  │
              │  Module   │   │  Module   │   │ (SQLite)  │
              │           │   │           │   │           │
              │ • bund.de │   │• Rule-    │   │ Tenders   │
              │ • TED     │   │  Based    │   │ Companies │
              │ • [More]  │   │• AI-Based │   │ Matches   │
              │           │   │ (OpenAI)  │   │           │
              └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Notification   │
                          │  Service        │
                          │ (Email/Webhook) │
                          └─────────────────┘

```

## 🔄 Daten-Flow

```
1. UNTERNEHMEN REGISTRIEREN
   └─ Frontend Form → Backend /companies → DB (Company)

2. AUSSCHREIBUNGEN SCANNEN
   └─ /scrape → Scraper Orchestrator → bund.de, TED → DB (Tender)

3. MATCHING DURCHFÜHREN
   └─ /match/{company_id} → Matcher → KI Score → DB (Match)

4. BENACHRICHTIGUNG
   └─ /notify/{company_id} → Email Service → Company Email
```

## 📊 Datenmodelle

### Company
```python
{
  "id": "info_example_com",
  "name": "Example Corp",
  "email": "info@example.com",
  "industry": "IT",
  "experience_keywords": "Cloud,DevOps,Security",
  "cpv_focus": "72000000",
  "min_budget": 50000,
  "max_budget": 500000,
  "regions": "Deutschland,EU",
  "active": true,
  "created_at": "2026-04-01T19:00:00Z"
}
```

### Tender
```python
{
  "id": "bund-001",
  "title": "IT-Dienstleistungen für Bundesagentur",
  "description": "Cloud-Hosting und DevOps-Services",
  "source": "bund.de",
  "source_url": "https://bund.de/...",
  "deadline": "2026-05-15T00:00:00Z",
  "buyer_name": "Bundesagentur für Arbeit",
  "buyer_category": "Behörde",
  "budget_min": 50000,
  "budget_max": 200000,
  "cpv_codes": "72000000",
  "scraped_at": "2026-04-01T19:00:00Z"
}
```

### Match
```python
{
  "id": 1,
  "company_id": "info_example_com",
  "tender_id": "bund-001",
  "match_score": 78.5,
  "reasoning": "✅ Cloud-Erfahrung vorhanden, Budget passt, Region OK",
  "matched_at": "2026-04-01T19:05:00Z",
  "notified": false
}
```

## 🔌 API Endpoints

### Companies
```
POST   /companies               # Register company
GET    /companies/{id}          # Get company profile
PUT    /companies/{id}          # Update profile
DELETE /companies/{id}          # Delete profile
```

### Tenders
```
GET    /tenders                 # List all tenders
GET    /tenders/{id}            # Get tender details
POST   /scrape                  # Trigger scrape
```

### Matching
```
POST   /match/{company_id}      # Run matching
GET    /matches/{company_id}    # Get all matches
POST   /notify/{company_id}     # Send notification
```

### System
```
GET    /                        # Health check
GET    /health                  # Status
GET    /docs                    # Swagger UI
```

## 🔐 Security

- [ ] Input validation (Pydantic)
- [ ] Rate limiting (SlowAPI)
- [ ] Authentication (JWT)
- [ ] CORS configuration
- [ ] SQL injection prevention (SQLAlchemy ORM)

## 📈 Performance

- **Database**: SQLite (MVP) → PostgreSQL (Prod)
- **Caching**: Redis (optional, für Prod)
- **Async**: FastAPI mit asyncio
- **Scraping**: Parallel requests (httpx)

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# API tests
pytest tests/api/

# Load testing
locust -f tests/load.py
```

## 📝 Logging

```python
# Configure in app.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Logs in: `/app/data/publicflow.log`

## 🚀 CI/CD (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker image
        run: docker build -t publicflow:${{ github.sha }} .
      - name: Deploy to Heroku
        run: |
          echo ${{ secrets.HEROKU_AUTH_TOKEN }} | \
            docker login --username=_ --password-stdin registry.heroku.com
```

---

## 📖 Weitere Infos

- **OpenAI Docs**: https://platform.openai.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy**: https://www.sqlalchemy.org
- **BeautifulSoup4**: https://www.crummy.com/software/BeautifulSoup

---

**Status:** MVP ✅ | Production Ready: Q2 2026
