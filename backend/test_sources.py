"""
PublicFlow — Quellen-Diagnose
Führe aus: python3.14 test_sources.py
Testet alle API-Varianten und zeigt was 2025/2026-Daten liefert.
"""
import requests
import json
from datetime import datetime, timedelta

HEADERS = {"User-Agent": "PublicFlow/1.0 (contact: nicolas@osel.group)"}
s = requests.Session()
s.headers.update(HEADERS)

def sep(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

# ──────────────────────────────────────────────
# TED API v3 — verschiedene Ansätze
# ──────────────────────────────────────────────
sep("TED API: Datum-Filter Varianten")

TED = "https://api.ted.europa.eu/v3/notices/search"

ted_tests = [
    # Variante A: publishedFrom/publishedTo als Top-Level-Param
    ("A: publishedFrom/publishedTo", {
        "query": "CY=DEU",
        "fields": ["ND","TI","PD"],
        "page": 1, "limit": 5,
        "publishedFrom": "20260101",
        "publishedTo": "20261231"
    }),
    # Variante B: Datum mit >= Operator in expert query
    ("B: PD>=20260101", {
        "query": "CY=DEU AND PD>=20260101",
        "fields": ["ND","TI","PD"],
        "page": 1, "limit": 5
    }),
    # Variante C: Lucene Range mit Doppelpunkt
    ("C: PD:[20260101 TO *]", {
        "query": "CY=DEU AND PD:[20260101 TO *]",
        "fields": ["ND","TI","PD"],
        "page": 1, "limit": 5
    }),
    # Variante D: sort als Array (nicht sortField/sortOrder)
    ("D: sort als Array", {
        "query": "CY=DEU",
        "fields": ["ND","TI","PD"],
        "page": 1, "limit": 5,
        "sort": [{"field": "ND", "order": "DESC"}]
    }),
    # Variante E: scope ACTIVE
    ("E: scope=ACTIVE", {
        "query": "CY=DEU",
        "fields": ["ND","TI","PD"],
        "page": 1, "limit": 5,
        "scope": "ACTIVE"
    }),
    # Variante F: onlyLatestVersions
    ("F: onlyLatestVersions=true", {
        "query": "CY=DEU",
        "fields": ["ND","TI","PD"],
        "page": 1, "limit": 5,
        "onlyLatestVersions": True
    }),
    # Variante G: Jahr 2026 im ND-Format ("xxxxxx-2026")
    ("G: ND Wildcard 2026", {
        "query": "CY=DEU AND ND=*-2026",
        "fields": ["ND","TI","PD"],
        "page": 1, "limit": 5
    }),
    # Variante H: publicationDateFrom (alternativer Feldname)
    ("H: publicationDateFrom", {
        "query": "CY=DEU",
        "fields": ["ND","TI","PD"],
        "page": 1, "limit": 5,
        "publicationDateFrom": "2026-01-01",
        "publicationDateTo": "2026-12-31"
    }),
]

for name, payload in ted_tests:
    try:
        r = s.post(TED, json=payload, timeout=15)
        if r.status_code == 200:
            d = r.json()
            notices = d.get("notices", [])
            total = d.get("totalNoticeCount", "?")
            dates = [n.get("PD","?") for n in notices[:3]]
            print(f"✅ {name}: {r.status_code} | Total={total} | Daten={dates}")
        else:
            print(f"❌ {name}: HTTP {r.status_code} — {r.text[:100]}")
    except Exception as e:
        print(f"💥 {name}: {e}")

# ──────────────────────────────────────────────
# Deutsche Quellen — echte URLs testen
# ──────────────────────────────────────────────
sep("DEUTSCHE QUELLEN")

de_sources = [
    # Offizielle Bundesplattform (Nachfolger von bund.de)
    ("service.bund.de RSS", "https://www.service.bund.de/IMPORTE/Ausschreibungen/opensearch.html?view=processForm&resultCount=10&type=1&searchScope=1&tenderStatus=2&outputMode=rss"),
    ("service.bund.de Suche", "https://www.service.bund.de/IMPORTE/Ausschreibungen/opensearch.html"),
    # DTVP neue URLs
    ("DTVP RSS v2", "https://www.dtvp.de/Center/notice/search.do?format=rss&sortField=pd&sortOrder=DESC"),
    ("DTVP Suche", "https://www.dtvp.de/Center/notice/search.do"),
    # Vergabe NRW korrekte URL
    ("Vergabe NRW neu", "https://www.vergabe.nrw.de/VMPCenter/company/announcement/listAnnouncements.do?method=start&status=2&rss=true"),
    # Subreport
    ("Subreport Aktuell", "https://www.subreport.de/E11000/ausschreibungen-rss.xml"),
    # Auftragsboerse
    ("Auftragsboerse RSS", "https://www.auftragsboerse.de/ausschreibungen/rss"),
    # evergabe-online (Bundesplattform)
    ("evergabe-online RSS", "https://www.evergabe-online.de/tenderinformation.html?0&rss=true"),
    ("evergabe-online Suche", "https://www.evergabe-online.de/tenderinformation.html?0"),
    # Simap (Schweiz/DE)
    ("BUND Ausschreibungen neu", "https://www.bund.de/DE/Service/Ausschreibungen/ausschreibungen_node.html"),
]

for name, url in de_sources:
    try:
        r = s.get(url, timeout=10, allow_redirects=True)
        content_type = r.headers.get("Content-Type", "")[:40]
        preview = r.text[:80].replace('\n',' ').strip()
        print(f"{'✅' if r.status_code==200 else '❌'} {name}: HTTP {r.status_code} | {content_type} | {preview}")
    except Exception as e:
        print(f"💥 {name}: {e}")

sep("FERTIG")
print(f"Timestamp: {datetime.now().isoformat()}")
