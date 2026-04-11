# 🚀 PublicFlow — Live-Setup in 30 Minuten

## Was du brauchst
- GitHub Account (Repo: github.com/Burns754/publicflow)
- Railway Account (railway.app) — kostenloser Start
- Anthropic Account (console.anthropic.com) — für KI-Matching
- Stripe Account (stripe.com) — für Zahlungen
- Resend Account (resend.com) — für E-Mail-Alerts

---

## SCHRITT 1 — API Keys besorgen (10 Min)

### Anthropic (KI-Matching)
1. Gehe zu: https://console.anthropic.com/settings/keys
2. Klick „Create Key"
3. Name: `publicflow-prod`
4. Kopiere den Key → `sk-ant-api03-...`

### Resend (E-Mails)
1. Gehe zu: https://resend.com/api-keys
2. Klick „Create API Key"
3. Name: `publicflow`, Permission: „Sending access"
4. Kopiere den Key → `re_...`
5. **Domain verifizieren** (optional aber empfohlen):
   - Gehe zu Resend → Domains → Add Domain
   - Füge `publicflow.de` oder deine Domain hinzu
   - Setze DNS-Einträge wie beschrieben

---

## SCHRITT 2 — Stripe einrichten (10 Min)

### Stripe Account
1. Gehe zu: https://dashboard.stripe.com
2. Stelle sicher: **Test-Modus** ist aktiv (Toggle oben rechts)

### 4 Preise anlegen
Gehe zu: Produkte → Neues Produkt erstellen

**Produkt 1: PublicFlow Starter**
- Name: `PublicFlow Starter`
- Preis 1: `€99.00` / Monat (wiederkehrend)
  → Kopiere die Price ID: `price_starter_monthly`
- Preis 2: `€89.00` / Monat (wiederkehrend, Jahresintervall)
  → Kopiere die Price ID: `price_starter_yearly`

**Produkt 2: PublicFlow Professional**
- Name: `PublicFlow Professional`
- Preis 1: `€175.00` / Monat (wiederkehrend)
  → Kopiere die Price ID: `price_pro_monthly`
- Preis 2: `€157.00` / Monat (wiederkehrend, Jahresintervall)
  → Kopiere die Price ID: `price_pro_yearly`

### Stripe Webhook einrichten
1. Gehe zu: Entwickler → Webhooks → Endpoint hinzufügen
2. URL: `https://DEINE-RAILWAY-URL.up.railway.app/webhook/stripe`
3. Events auswählen:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Kopiere den Webhook Secret: `whsec_...`

### Stripe Secret Key
- Gehe zu: Entwickler → API-Schlüssel
- Kopiere „Geheimer Schlüssel": `sk_test_...`
- (Später für Produktion: `sk_live_...`)

---

## SCHRITT 3 — Railway Deployment (10 Min)

### Deployment
1. Gehe zu: https://railway.app
2. Klick „New Project" → „Deploy from GitHub Repo"
3. Wähle `Burns754/publicflow`
4. Railway erkennt automatisch den Dockerfile

### Environment Variables setzen
Im Railway Dashboard → dein Projekt → Variables:

```
JWT_SECRET=<zufälliger-langer-string-min-32-zeichen>
ANTHROPIC_API_KEY=sk-ant-api03-...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER_MONTHLY=price_...
STRIPE_PRICE_STARTER_YEARLY=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
RESEND_API_KEY=re_...
FROM_EMAIL=PublicFlow <noreply@publicflow.de>
FRONTEND_URL=https://DEINE-RAILWAY-URL.up.railway.app
DATABASE_URL=<Railway PostgreSQL URL — automatisch gesetzt>
```

**JWT Secret generieren** (Terminal):
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### PostgreSQL hinzufügen
Im Railway Dashboard → Add Service → Database → PostgreSQL
→ `DATABASE_URL` wird automatisch als Variable gesetzt

### Domain
- Railway gibt dir eine URL: `*.up.railway.app`
- Optional: Eigene Domain unter Settings → Custom Domain

---

## SCHRITT 4 — Testen

### Lokal testen (vor Deployment)
```bash
cd publicflow
cp .env.example .env
# .env ausfüllen mit deinen Keys
bash start.sh
# Browser: http://localhost:8000
```

### Nach Railway Deployment
1. Öffne deine Railway-URL
2. Registriere einen Test-Account
3. Klick „Jetzt scannen" → prüfe ob TED EU Daten kommen
4. Klick „Matching starten" → KI-Score sollte erscheinen
5. Test-Checkout mit Stripe Test-Karte: `4242 4242 4242 4242`

---

## Wichtige URLs nach Deployment

| Was | URL |
|-----|-----|
| Landing Page | `https://deine-url.up.railway.app/` |
| App Login | `https://deine-url.up.railway.app/app/index.html` |
| API Docs | `https://deine-url.up.railway.app/docs` |
| Health Check | `https://deine-url.up.railway.app/health` |

---

## Stripe: Von Test auf Live umstellen

Wenn du bereit bist echte Zahlungen zu nehmen:
1. Stripe Dashboard → Toggle: Test → Live
2. Neue Live-Keys kopieren
3. Neue Live-Price-IDs erstellen (gleiche Preise)
4. Railway-Variablen updaten (`sk_live_...`, neue Price IDs)
5. Webhook für Live neu anlegen

---

## Häufige Probleme

**App startet nicht:**
- Prüfe Railway Logs → Deploy → Build Logs
- Oft: fehlende Environment Variable

**KI-Matching funktioniert nicht:**
- `ANTHROPIC_API_KEY` gesetzt?
- Anthropic Guthaben vorhanden? (console.anthropic.com/billing)

**E-Mails kommen nicht an:**
- `RESEND_API_KEY` korrekt?
- Domain in Resend verifiziert?

**Stripe Checkout schlägt fehl:**
- Price IDs korrekt kopiert (nicht verwechseln)?
- `FRONTEND_URL` auf Railway-URL gesetzt?
