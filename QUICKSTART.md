# 🚀 PublicFlow - Schritt-für-Schritt Setup

## Schritt 1: Vorbereitung

```bash
# Stelle sicher dass Python 3.9+ installiert ist
python3 --version
# Python 3.11.5 (oder höher)

# Gehe ins Projektverzeichnis
cd publicflow
```

## Schritt 2: Virtual Environment

```bash
# Erstelle Virtual Environment
python3 -m venv venv

# Aktiviere es
# Linux/Mac:
source venv/bin/activate

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

## Schritt 3: Dependencies installieren

```bash
# Installiere requirements
pip install -r requirements.txt

# Das installiert:
# ✅ fastapi==0.104.1
# ✅ uvicorn==0.24.0
# ✅ pydantic==2.5.0
# ✅ sqlalchemy==2.0.23
# ✅ beautifulsoup4==4.12.2
# ✅ requests==2.31.0
# ✅ openai==1.3.0
# ✅ python-dotenv==1.0.0
# ✅ aiohttp==3.9.1
# ✅ lxml==4.9.3

# Das dauert ca. 2-3 Minuten
```

## Schritt 4: Environment konfigurieren

```bash
# Kopiere .env template
cp .env.example .env

# Öffne .env in deinem Editor
nano .env  # oder vim, VSCode, etc.

# Setze (optional):
# OPENAI_API_KEY=sk-your-key-here
# Falls leer → Nutzt Regel-basiertes Matching (funktioniert auch!)
```

## Schritt 5: Starte den Server

### Option A: Mit start.sh (empfohlen)

```bash
bash start.sh
```

Du siehst:
```
🚀 PublicFlow Backend starting...
📊 Database: sqlite:///./publicflow.db
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Option B: Mit make

```bash
make run
```

### Option C: Manual

```bash
cd backend
python3 app.py
```

## Schritt 6: Öffne im Browser

```
Frontend:    http://localhost:8000/frontend
API Docs:    http://localhost:8000/docs
Health:      http://localhost:8000/health
```

## 📝 Teste die Funktionalität

### 1️⃣ Unternehmen registrieren

**Form ausfüllen:**
```
Unternehmensname: "TechCorp GmbH"
Email: "info@techcorp.de"
Branche: "IT & Software"
Kompetenzen: "Cloud-Hosting,DevOps,Python,Docker,Security"
Budget: 50.000 - 500.000 €
Regionen: "Deutschland,EU"
```

Button: "📊 Profil erstellen"

Du siehst: ✅ Unternehmen registriert! ID: info_techcorp_de

### 2️⃣ Ausschreibungen abrufen

Button: "📡 Ausschreibungen abrufen"

Du siehst:
```
✅ 4 Ausschreibungen gefunden!

Aktuelle Ausschreibungen:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 IT-Dienstleistungen für Bundesagentur
   bund.de | 💰 €50.000 - €200.000
   📅 Deadline: 15.05.2026
   Gesucht werden Cloud-Hosting und DevOps-Services...

📌 Cyber Security Services für EU Institutions
   ted.europa.eu | 💰 €200.000 - €800.000
   📅 Deadline: 15.06.2026
   Advanced cyber threat detection...
```

### 3️⃣ Matching durchführen

Button: "🤖 Matching durchführen"

Du siehst:
```
✅ 3 Relevante Matches gefunden!

Matching-Ergebnisse:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

bund-001
✨ Score: 78% 
✅ Cloud-Erfahrung vorhanden
💰 Budget-Range passt: €50.000 - €200.000
📍 Region-Interesse erkannt
📋 CPV-Codes relevant

ted-001
✨ Score: 65%
⚠️ Cyber Security ist thematisch relevant
💰 Budget über deiner Range (€200k-€800k)
```

## 🔗 API testen (curl)

```bash
# Health Check
curl http://localhost:8000/health

# Tenders abrufen
curl http://localhost:8000/tenders

# Scraping triggern
curl -X POST http://localhost:8000/scrape

# Matching für Company
curl -X POST http://localhost:8000/match/info_techcorp_de
```

## 🐳 Alternative: Mit Docker

```bash
# Stelle sicher dass Docker läuft
docker --version

# Start
docker-compose up

# Das auch startet:
# ✅ API auf :8000
# ✅ Und zeigt Logs

# Drücke Ctrl+C zum stoppen
```

## ✅ Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"

```bash
# Dependencies nicht installiert
pip install -r requirements.txt
```

### "Port 8000 already in use"

```bash
# Finde Prozess
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Töte ihn
kill -9 <PID>

# Oder nutze anderen Port
PORT=8001 python backend/app.py
```

### "OPENAI_API_KEY error"

Das ist ok! Der Code fallback zu Rule-based Matching.
Falls du GPT nutzen willst:
```bash
# Von https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here
```

### Database error

```bash
# Reset database
rm publicflow.db
python backend/app.py
# Neustart erstellt DB
```

## 📊 File Structure Check

Stelle sicher dass du diese Files hast:

```
publicflow/
✅ backend/app.py
✅ backend/scraper.py
✅ backend/matcher.py
✅ backend/models.py
✅ frontend/index.html
✅ requirements.txt
✅ .env.example
✅ Dockerfile
✅ docker-compose.yml
✅ Makefile
✅ README.md
✅ DEPLOYMENT.md
```

Sind alle da? → Super! 🎉

## 📈 Was funktioniert nach Setup

| Feature | Status | Test-Link |
|---------|--------|-----------|
| Health Check | ✅ | http://localhost:8000/health |
| API Docs | ✅ | http://localhost:8000/docs |
| Frontend UI | ✅ | http://localhost:8000/frontend |
| Company Registration | ✅ | UI Form |
| Tender Scraping | ✅ | UI Button |
| KI Matching | ✅ | UI Button + Console |
| Email Notifications | 🔜 | Coming Q2 |

## 🎓 Next Steps nach erfolgreichem Setup

1. **Teste die UI** – Registriere dich, Scrape, Match
2. **Lese DEPLOYMENT.md** – Für Production Setup
3. **Lese ARCHITECTURE.md** – Für System-Details
4. **Customiziere** – Add deine Real Scraper, Email, etc.
5. **Deploy** – Zu Heroku, AWS, DigitalOcean, etc.

## ❓ Fragen?

- API Errors? → Schau http://localhost:8000/docs
- Code-Fragen? → Lese backend/app.py + comments
- Deploy-Fragen? → Siehe DEPLOYMENT.md
- Business-Fragen? → Siehe README.md

---

**Du bist bereit! 🚀 Teste es jetzt!**
