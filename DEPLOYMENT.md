# PublicFlow - Deployment & Nutzung

## 🚀 Schnellstart (Local)

```bash
# 1. Repository clonen
cd publicflow

# 2. Start script ausführen
bash start.sh

# 3. Öffne im Browser
http://localhost:8000/frontend
```

## 📋 Was funktioniert jetzt

### MVP Features ✅

- **Unternehmen registrieren** → Profil mit Branche, Kompetenzen, Budget, Regionen
- **Ausschreibungen abrufen** → Scannt bund.de und TED (Mock-Daten für MVP)
- **KI-Matching** → Bewertet Relevanz automatisch (40+ Punkte)
- **Matching-Ergebnisse** → Zeigt Score und Begründung

### Backend API 📡

```
GET  /                          # Health Check
GET  /health                    # Status
POST /companies                 # Unternehmen registrieren
GET  /companies/{id}            # Unternehmen abrufen
POST /scrape                    # Ausschreibungen abrufen
GET  /tenders                   # Ausschreibungen anzeigen
POST /match/{company_id}        # Matching durchführen
GET  /matches/{company_id}      # Matches abrufen
POST /notify/{company_id}       # Benachrichtigung senden
```

Swagger Docs: http://localhost:8000/docs

## 🔧 Konfiguration

### .env anpassen

```bash
cp .env.example .env
```

Dann bearbeite `.env`:

```env
# OpenAI API Key (optional - nutzt sonst Regel-basiertes Matching)
OPENAI_API_KEY=sk-your-key-here

# Andere Settings
DATABASE_URL=sqlite:///./publicflow.db
HOST=0.0.0.0
PORT=8000
```

## 🧠 Wie das KI-Matching funktioniert

### Option 1: Rule-Based (immer verfügbar)

- Keyword-Matching in Branche
- Budget-Range Überlap
- Region-Interesse
- CPV-Code Alignment

**Score:** 0-100 basierend auf Gewichtung

### Option 2: AI-Based (mit OpenAI)

- Nutzt GPT-4 für tiefes Verständnis
- Analysiert: Kompetenzen vs. Anforderungen
- Bewertet: Likelihood of Success
- Erklärt: Konkrete Gründe für Match

**Score:** 0-100 basierend auf KI-Analyse

## 📊 Nächste Schritte

### Phase 2 (Production Ready)

- [ ] Database: SQLite → PostgreSQL
- [ ] Real Scraper: Mock → Live bund.de API
- [ ] Email Service: Integration (SendGrid/AWS SES)
- [ ] Scheduling: APScheduler für tägliche Scans
- [ ] Frontend: React SPA mit Dashboard
- [ ] Auth: User Accounts mit OAuth
- [ ] Payment: Stripe Integration (€175/Monat)

### Phase 3 (Scale)

- [ ] Multi-Language Support (DE, EN, FR)
- [ ] More Platforms: France, UK, Italy
- [ ] Advanced Filters: Gebot-History, Success Rate
- [ ] Collaboration: Team Sharing & Roles
- [ ] Analytics: Dashboard mit KPIs

## 🐳 Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

CMD ["python3", "app.py"]
```

```bash
# Build
docker build -t publicflow:latest .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  publicflow:latest
```

## ☁️ Cloud Deployment (Heroku)

```bash
# Heroku CLI installieren
heroku login

# App erstellen
heroku create publicflow-demo

# Environment variable setzen
heroku config:set OPENAI_API_KEY=sk-...

# Deploy
git push heroku main

# Logs anschauen
heroku logs --tail
```

## 🧪 Testing

```bash
# Unit Tests (später)
pytest tests/

# API Tests
curl http://localhost:8000/health

# Full Integration
bash tests/integration.sh
```

## 📞 Support

- Issues: Notizen in MEMORY.md
- Questions: Frag direkt
- Bugs: Stack Trace in README

## 📈 Metriken

Nach Launch tracken:

- **Unique Companies**: Registrierte Nutzer
- **Tenders Matched**: Ausschreibungen gefunden
- **Match Success Rate**: % der gebotenen Ausschreibungen
- **Revenue**: Monthly Recurring
- **Churn Rate**: Cancellations

## 🎯 Business Model

**Pricing:**
- Basic: €175/Monat (bis 10 Ausschreibungen/Woche)
- Pro: €299/Monat (unlimited)
- Enterprise: Custom

**Revenue Potential:**
- Target: 1.000 KMUs → €175k/Monat
- Growth: 10% MoM
- Profitability: 70% margins

---

**Ready to deploy? Let's go! 🚀**
