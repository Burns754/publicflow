#!/bin/bash

# PublicFlow Quick Start Script

set -e

echo "🚀 PublicFlow - KI Ausschreibungs-Monitor"
echo "==========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 ist nicht installiert!"
    exit 1
fi

echo "✅ Python3 gefunden: $(python3 --version)"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Erstelle Virtual Environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔌 Aktiviere Virtual Environment..."
source venv/bin/activate

# Install requirements
echo "📚 Installiere Dependencies..."
pip install -q -r requirements.txt

# Copy .env if not exists
if [ ! -f ".env" ]; then
    echo "⚙️  Erstelle .env (bitte API-Key hinzufügen)"
    cp .env.example .env
    echo "   ⚠️  Bitte bearbeite .env und füge dein OpenAI API Key hinzu!"
fi

# Start backend
echo ""
echo "🎯 Starte Backend (http://localhost:8000)"
echo "📖 API Docs: http://localhost:8000/docs"
echo "🌐 Frontend: http://localhost:8000/frontend"
echo ""
echo "Drücke Ctrl+C zum Beenden"
echo ""

cd backend
python3 app.py
