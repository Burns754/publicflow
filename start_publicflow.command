#!/bin/bash
# PublicFlow Starter — Doppelklick zum Starten

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 PublicFlow v0.3 wird gestartet..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# .env laden
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep -v '^\s*$' | grep -v 'FROM_EMAIL' | xargs)
    echo "✅ .env geladen"
else
    echo "❌ .env nicht gefunden!"; exit 1
fi

# Python ermitteln
for pypath in \
    /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 \
    /usr/local/bin/python3.12 /usr/local/bin/python3.11 \
    python3.12 python3.11 python3; do
    if command -v "$pypath" &>/dev/null; then PY="$pypath"; break; fi
done
echo "🐍 Python: $($PY --version 2>&1)"

# Port 8000 freimachen
PORT_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$PORT_PID" ]; then
    echo "🔄 Port 8000 freigeben (PID $PORT_PID)..."
    kill -9 $PORT_PID 2>/dev/null; sleep 1
fi

# Pakete installieren
if ! $PY -c "import uvicorn" &>/dev/null 2>&1; then
    echo "📦 Installiere Pakete..."
    $PY -m pip install \
        "fastapi" "uvicorn" "pydantic" "sqlalchemy" \
        "beautifulsoup4" "requests" "python-dotenv" "aiohttp" \
        "anthropic" "stripe" "resend" "apscheduler" \
        "python-jose[cryptography]" "passlib" "python-multipart" \
        --only-binary :all: -q 2>&1 | grep -v "already satisfied" || true
    $PY -m pip install lxml --only-binary :all: -q 2>/dev/null || true
fi

# bcrypt explizit installieren (Passwort-Hashing)
if ! $PY -c "import bcrypt" &>/dev/null 2>&1; then
    echo "🔐 Installiere bcrypt..."
    $PY -m pip install bcrypt --only-binary :all: -q 2>/dev/null || \
    $PY -m pip install bcrypt -q 2>/dev/null || \
    echo "⚠️  bcrypt nicht verfügbar — verwende argon2 als Fallback"
    # Argon2 als Fallback
    $PY -m pip install argon2-cffi -q 2>/dev/null || true
fi

echo ""
echo "🌐 http://localhost:8000"
echo "📖 http://localhost:8000/docs"
echo "Strg+C zum Beenden"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd backend
$PY -m uvicorn app:app --reload --port 8000
