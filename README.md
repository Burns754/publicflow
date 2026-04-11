# 🔍 PublicFlow - KI Ausschreibungs-Monitor

**Zugang zu 2 Billionen Euro öffentlicher Ausschreibungen. Automatisiert. Intelligent. Bezahlbar.**

*Nur 175€/Monat statt 500-2.000€* ✨

---

## 🎯 Was ist PublicFlow?

PublicFlow ist eine **KI-gestützte Matching-Plattform** für öffentliche Ausschreibungen:

- 📊 **94% der KMUs verpassen den Markt** → Zu viele Plattformen, zu kurze Fristen, zu viel manueller Aufwand
- 🤖 **PublicFlow scanat alle Plattformen täglich** und matched intelligent gegen dein Profil
- 💰 **Nur relevante Treffer** → Du siehst nur Ausschreibungen die zu dir passen
- ⚡ **Zero Aufwand** → Alles automatisch im Postfach

---

## ✨ Features (MVP)

| Feature | Status | Details |
|---------|--------|---------|
| 🏢 Unternehmen-Registrierung | ✅ | Profil mit Branche, Kompetenzen, Budget, Regionen |
| 📡 Multi-Source Scraping | ✅ | bund.de, TED (EU), [extensible] |
| 🤖 KI-Matching | ✅ | Rule-based + OpenAI GPT (optional) |
| 📧 Email-Notifications | 🔜 | Coming soon |
| 📊 Dashboard | 🔜 | Match-Historie, Analytics |
| 💳 Payment Integration | 🔜 | Stripe / Paddle |
| 🌍 Multi-Language | 🔜 | DE, EN, FR |

---

## 🚀 Quick Start (2 Minuten)

### Lokal (Desktop)

```bash
# 1. Repo klonen
git clone https://github.com/nicolasosel/publicflow.git
cd publicflow

# 2. Setup
bash start.sh

# 3. Browser öffnen
http://localhost:8000/frontend
```

### Mit Docker

```bash
docker-compose up
# → http://localhost:8000
```

---

## 🏗️ Architektur

**Frontend** (HTML/JS) → **API** (FastAPI) → **Scraper** (BeautifulSoup) + **Matcher** (OpenAI) → **DB** (SQLite)

```
┌─────────────────────────────────────────┐
│   🌐 Frontend (Browser)                │
│   User registriert, triggert Matching   │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│   🔵 Backend API (FastAPI)              │
│   GET/POST endpoints für alles          │
└────────────┬─────────────┬──────────────┘
             │             │
    ┌────────▼──────┐   ┌──▼────────────────┐
    │ Scraper       │   │ Matcher (KI)      │
    │ • bund.de     │   │ • Rule-based      │
    │ • TED         │   │ • AI-based        │
    └────────┬──────┘   └──┬────────────────┘
             │             │
    ┌────────▼─────────────▼──┐
    │ 🗄️ Database (SQLite)     │
    │ • Companies              │
    │ • Tenders                │
    │ • Matches                │
    └──────────────────────────┘
```

---

## 📚 Dokumentation

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** – Vollständiger Deploy Guide + Betrieb
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** – System Design, API, Datenmodelle
- **[API Docs](http://localhost:8000/docs)** – Swagger UI (live)

---

## 🔧 Tech Stack

| Layer | Tech | Warum? |
|-------|------|--------|
| **Frontend** | HTML5 + Vanilla JS | Einfach, keine Dependencies |
| **Backend** | FastAPI + Python | Modern, async, auto-docs |
| **Scraper** | BeautifulSoup4 + Requests | Einfach & zuverlässig |
| **KI** | OpenAI GPT-4 | State-of-the-art (optional) |
| **DB** | SQLite (MVP) / PostgreSQL (Prod) | Lightweight start, Scale later |
| **Deploy** | Docker + Heroku | Einfach & cloud-ready |

---

## 💼 Business Model

### Pricing

| Plan | Preis | Features |
|------|-------|----------|
| **Starter** | €99/Monat | 5 Ausschreibungen/Woche |
| **Professional** | **€175/Monat** ⭐ | Unlimited, 24h Priority |
| **Enterprise** | Custom | Custom integrationen |

vs. Wettbewerb: €500-2.000/Monat 😱

### Revenue Potential

- Target: 1.000 KMUs @ €175/Monat = **€175k MRR**
- Growth: 10% MoM
- Profitability: ~70% margins
- Breakeven: ~6 Monate

---

## 🎯 Use Cases

### Szenario 1: ITK-Agentur
```
Profile:
- Branche: IT & Software
- Skills: Cloud, DevOps, Python
- Budget: €50k-500k
- Region: Deutschland

Result: 
7 Matches gefunden diese Woche
✅ Bundesamt für Digitalisierung (€150k)
✅ Stadt Berlin (€80k)
```

### Szenario 2: Bauunternehmen
```
Profile:
- Branche: Bau & Infrastruktur
- Skills: Tiefbau, Straßenbau
- Budget: €500k-5M
- Region: Bayern

Result:
12 Matches
✅ Autobahn GmbH
✅ Stadt München
```

---

## 📖 API Übersicht

### Companies
```bash
POST   /companies               # Registrieren
GET    /companies/{id}          # Profil abrufen
```

### Tenders
```bash
GET    /tenders                 # Ausschreibungen anzeigen
POST   /scrape                  # Scraping triggern
```

### Matching
```bash
POST   /match/{company_id}      # Matching durchführen
GET    /matches/{company_id}    # Ergebnisse abrufen
```

Vollständige Docs: http://localhost:8000/docs

---

## 🔗 Integration

PublicFlow kann mit deinen Tools integrieren:

```python
# Webhooks (coming soon)
POST https://publicflow.io/webhooks/matches
{
  "company_id": "xyz",
  "match": {
    "tender_id": "bund-001",
    "score": 87,
    "title": "IT-Services"
  }
}

# Zapier / Make Integration (coming soon)
# → Send to Slack
# → Add to Airtable
# → Create Calendar Event
```

---

## 🧪 Entwicklung

### Setup Dev Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Tests

```bash
pytest tests/
pytest tests/ -v --cov=backend/
```

### Format Code

```bash
black backend/
flake8 backend/
```

---

## 🚀 Roadmap

### Q1 2026 (MVP Done ✅)
- [x] Basis-Scraper (bund.de, TED)
- [x] Rule-based Matching
- [x] Simple UI
- [x] Docker support

### Q2 2026 (Beta)
- [ ] Email Notifications
- [ ] PostgreSQL
- [ ] Advanced Filters
- [ ] User Accounts + Auth
- [ ] Payment Integration

### Q3 2026 (V1.0)
- [ ] Webhook System
- [ ] Zapier/Make Integration
- [ ] Multi-Language (EN, FR)
- [ ] Analytics Dashboard
- [ ] Team Collaboration

### Q4 2026+ (Scale)
- [ ] More Countries (France, UK, Italy)
- [ ] Advanced ML Models
- [ ] API für Partner
- [ ] White-Label Version

---

## 🤝 Contributing

Bitte bei Issues/Features einfach Notiz geben! Alles ist in early stage und sehr flexibel.

---

## 📄 Lizenz

MIT - Siehe LICENSE file

---

## 📞 Support / Feedback

- 💬 Telegram: @nicolasosel
- 📧 Email: nicolas@osel.group
- 📝 Notizen: Siehe MEMORY.md

---

**PublicFlow – Zugang statt Suche.** 🎯
