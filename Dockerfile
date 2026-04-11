FROM python:3.11-slim

WORKDIR /app

# System-Abhängigkeiten
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend & Frontend kopieren
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Datenbank-Verzeichnis
RUN mkdir -p /app/data

WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Railway setzt $PORT automatisch, lokal läuft es auf 8000
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
