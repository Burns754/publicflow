"""
PublicFlow Scraper v2 — echte Datenquellen
- TED (Tender Electronic Daily): offizielle JSON API v3
- service.bund.de: Bundesplattform für öffentliche Ausschreibungen
- Fallback-Kette für maximale Verfügbarkeit
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "PublicFlow/2.0 (Ausschreibungsmonitor; contact: nicolas@osel.group)",
    "Accept": "application/json, text/html, application/xml;q=0.9, */*;q=0.8",
}


# ─────────────────────────────────────────────────────────────────
# TED Scraper — offizielle EU JSON API v3
# Dokumentation: https://api.ted.europa.eu/swagger-ui/
# Expert Query Syntax: https://ted.europa.eu/en/developers-corner/ted-api
# ─────────────────────────────────────────────────────────────────

class TEDScraper:
    """
    TED via JSON API v3.
    Primäre Strategie: ND=*-YYYY filtert auf aktuelles Jahr (zuverlässigste Methode).
    Fallback: scope=ACTIVE, dann PD>=Datum.
    Profil-aware: Keywords aus Unternehmensprofil fließen in Query ein.
    """

    API_URL = "https://api.ted.europa.eu/v3/notices/search"

    # Felder die wir abrufen (valide v3-Feldnamen laut Swagger)
    FIELDS = ["ND", "TI", "PD", "DT", "AU", "RC", "PC", "CY", "TD"]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": HEADERS["User-Agent"],
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def fetch_for_company(self, keywords: List[str], cpv_codes: Optional[List[str]] = None,
                          limit: int = 20) -> List[Dict]:
        """
        Profil-aware Suche: nutzt Unternehmens-Keywords für gezielte TED-Abfrage.
        Deutlich höhere Treffer-Qualität als allgemeines Scraping.
        """
        if not keywords:
            return self.fetch_recent_tenders(limit)

        year = datetime.now().year
        # Baue Keyword-Query (max. 5 Keywords für Performance)
        kw_clean = [kw.strip() for kw in keywords[:5] if len(kw.strip()) >= 3]
        kw_query = " OR ".join(f'"{kw}"' for kw in kw_clean) if kw_clean else ""

        base_query = f"CY=DEU AND ND=*-{year}"
        if kw_query:
            base_query = f"CY=DEU AND ND=*-{year} AND ({kw_query})"

        # CPV-Filter falls vorhanden
        if cpv_codes:
            cpv_q = " OR ".join(f"PC={c.strip()}" for c in cpv_codes[:3] if c.strip())
            if cpv_q:
                base_query += f" AND ({cpv_q})"

        try:
            resp = self.session.post(self.API_URL, json={
                "query": base_query,
                "fields": self.FIELDS,
                "page": 1,
                "limit": limit
            }, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                notices = data.get("notices", [])
                logger.info(f"✅ TED Profil-Suche: {len(notices)} Treffer für Keywords: {kw_clean}")
                result = []
                for n in notices:
                    t = self._parse_notice(n)
                    if t:
                        result.append(t)
                return self._filter_active(result)
            else:
                logger.warning(f"TED Profil-Suche HTTP {resp.status_code} — Fallback zu allg. Suche")
                return self.fetch_recent_tenders(limit)
        except Exception as e:
            logger.error(f"TED Profil-Suche Fehler: {e} — Fallback")
            return self.fetch_recent_tenders(limit)

    def fetch_eu_wide(self, limit: int = 20) -> List[Dict]:
        """
        EU-weite TED-Suche (ohne Länderbeschränkung).
        Liefert Ausschreibungen aller EU-Institutionen und Mitgliedsstaaten.
        """
        year = datetime.now().year
        prev_year = year - 1
        attempts = [
            (f"EU-weit ND=*-{year}", {
                "query": f"ND=*-{year}",
                "fields": self.FIELDS,
                "page": 1, "limit": limit
            }),
            ("EU-weit scope=ACTIVE", {
                "query": "*",
                "fields": self.FIELDS,
                "page": 1, "limit": limit,
                "scope": "ACTIVE"
            }),
            (f"EU-weit ND=*-{year} OR ND=*-{prev_year}", {
                "query": f"(ND=*-{year} OR ND=*-{prev_year})",
                "fields": self.FIELDS,
                "page": 1, "limit": limit
            }),
        ]
        tenders = []
        for label, payload in attempts:
            try:
                resp = self.session.post(self.API_URL, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    raw = data.get("notices", [])
                    recent = [n for n in raw if self._is_recent(n, min_year=prev_year)]
                    if recent:
                        for n in recent:
                            t = self._parse_notice(n)
                            if t:
                                t["source"] = "ted.europa.eu/EU"
                                t["buyer_category"] = "EU"
                                tenders.append(t)
                        logger.info(f"✅ TED EU-weit '{label}': {len(tenders)} Einträge")
                        break
            except Exception as e:
                logger.warning(f"TED EU-weit '{label}': {e}")
        return self._filter_active(tenders)

    def fetch_recent_tenders(self, limit: int = 20) -> List[Dict]:
        tenders = []
        try:
            logger.info("📡 TED API v3: Aktuelle Ausschreibungen abrufen...")

            today = datetime.now()
            year = today.year
            prev_year = year - 1
            date_str = today.strftime("%Y%m%d")
            # Datum 30 Tage zurück für genügend Treffer
            date_30d = (today - timedelta(days=30)).strftime("%Y%m%d")

            # Versuche in Reihenfolge — erster mit aktuellen Daten gewinnt
            attempts = [
                # 1. Bestes: ND-Wildcard auf aktuelles Jahr
                (f"ND=*-{year}", {
                    "query": f"CY=DEU AND ND=*-{year}",
                    "fields": self.FIELDS,
                    "page": 1, "limit": limit
                }),
                # 2. Beide Jahre (Jahreswechsel Puffer)
                (f"ND=*-{year} OR ND=*-{prev_year}", {
                    "query": f"CY=DEU AND (ND=*-{year} OR ND=*-{prev_year})",
                    "fields": self.FIELDS,
                    "page": 1, "limit": limit
                }),
                # 3. scope=ACTIVE (laut TED Swagger gültig)
                ("scope=ACTIVE", {
                    "query": "CY=DEU",
                    "fields": self.FIELDS,
                    "page": 1, "limit": limit,
                    "scope": "ACTIVE"
                }),
                # 4. PD >= 30 Tage zurück
                (f"PD>={date_30d}", {
                    "query": f"CY=DEU AND PD>={date_30d}",
                    "fields": self.FIELDS,
                    "page": 1, "limit": limit
                }),
                # 5. Lucene Range
                (f"PD:[{date_30d} TO *]", {
                    "query": f"CY=DEU AND PD:[{date_30d} TO *]",
                    "fields": self.FIELDS,
                    "page": 1, "limit": limit
                }),
                # 6. Sort DESC (field name laut Swagger v3)
                ("sort publication-date DESC", {
                    "query": "CY=DEU",
                    "fields": self.FIELDS,
                    "page": 1, "limit": limit,
                    "sort": [{"field": "publication-date", "order": "DESC"}]
                }),
                # 7. onlyLatestVersions
                ("onlyLatestVersions", {
                    "query": "CY=DEU",
                    "fields": self.FIELDS,
                    "page": 1, "limit": limit,
                    "onlyLatestVersions": True
                }),
            ]

            notices = []
            used_approach = "none"

            for label, payload in attempts:
                try:
                    resp = self.session.post(self.API_URL, json=payload, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw = data.get("notices", [])
                        total = data.get("totalNoticeCount", 0)
                        recent = [n for n in raw if self._is_recent(n, min_year=prev_year)]
                        if recent:
                            notices = recent
                            used_approach = label
                            logger.info(f"✅ TED '{label}': {total} gesamt, {len(recent)}/{len(raw)} aktuell")
                            break
                        else:
                            sample = [n.get("PD", "?") for n in raw[:3]]
                            logger.warning(f"TED '{label}': {len(raw)} Notices aber veraltet — {sample}")
                    else:
                        err = resp.text[:120].replace('\n', ' ')
                        logger.warning(f"TED '{label}': HTTP {resp.status_code} — {err}")
                except requests.exceptions.Timeout:
                    logger.warning(f"TED '{label}': Timeout")
                except Exception as e:
                    logger.warning(f"TED '{label}': {e}")

            if not notices:
                logger.error("❌ TED: Kein Ansatz lieferte aktuelle Daten")
            else:
                logger.info(f"TED nutzt Ansatz: '{used_approach}'")

            for notice in notices:
                try:
                    t = self._parse_notice(notice)
                    if t:
                        tenders.append(t)
                except Exception as e:
                    logger.warning(f"TED Parse-Fehler: {e}")

        except requests.exceptions.ConnectionError:
            logger.error("TED API nicht erreichbar")
        except Exception as e:
            logger.error(f"TED Fehler: {e}")

        # Nur Ausschreibungen mit Deadline mind. 24h in Zukunft
        return self._filter_active(tenders)

    def _parse_notice(self, notice: Dict) -> Optional[Dict]:
        nd = notice.get("ND", "")
        if isinstance(nd, list):
            nd = nd[0] if nd else ""

        ti = notice.get("TI", {})
        title = self._extract_multilang(ti)

        au = notice.get("AU", {})
        buyer_name = self._extract_multilang(au)

        if not nd and not title:
            return None

        pd_raw = notice.get("PD", "")
        pub_date = str(pd_raw).split("+")[0] if pd_raw else ""

        # Deadline: DT-Feld
        dt = notice.get("DT", [])
        deadline_str = dt[0] if isinstance(dt, list) and dt else (dt if isinstance(dt, str) else None)
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(
                    str(deadline_str).replace("+02:00", "").replace("+01:00", "").strip()
                )
            except Exception:
                pass

        pc = notice.get("PC", [])
        cpv_codes = ", ".join(pc[:5]) if pc else ""

        rc = notice.get("RC", [])
        region_str = ", ".join(rc[:3]) if rc else "DEU"

        notice_id = f"ted-{nd}" if nd else f"ted-{abs(hash(title))}"
        notice_url = f"https://ted.europa.eu/en/notice/{nd}" if nd else "https://ted.europa.eu"

        return {
            "id": notice_id,
            "title": (title or f"EU-Ausschreibung {nd}")[:300],
            "description": (
                f"EU-Ausschreibung (TED). Auftraggeber: {buyer_name}. "
                f"Region: {region_str}. Veröffentlicht: {pub_date}. CPV: {cpv_codes[:100]}"
            )[:1000],
            "source": "ted.europa.eu",
            "source_url": notice_url,
            "deadline": deadline.isoformat() if deadline else None,
            "buyer_name": buyer_name or "EU-Auftraggeber",
            "buyer_category": "EU",
            "budget_min": None,
            "budget_max": None,
            "cpv_codes": cpv_codes[:500],
        }

    def _is_recent(self, notice: Dict, min_year: int = 2024) -> bool:
        """True wenn Notice aus min_year oder neuer stammt."""
        nd = notice.get("ND", "")
        if isinstance(nd, list):
            nd = nd[0] if nd else ""
        if nd and "-" in str(nd):
            try:
                return int(str(nd).split("-")[-1]) >= min_year
            except Exception:
                pass
        pd = notice.get("PD", "")
        if pd:
            try:
                return int(str(pd)[:4]) >= min_year
            except Exception:
                pass
        return False

    def _filter_active(self, tenders: List[Dict]) -> List[Dict]:
        """Behält nur Ausschreibungen mit Deadline > jetzt + 24h."""
        min_date = datetime.now() + timedelta(hours=24)
        active = []
        for t in tenders:
            dl = t.get("deadline")
            if not dl:
                active.append(t)  # Kein Datum → behalten
                continue
            try:
                if datetime.fromisoformat(dl) > min_date:
                    active.append(t)
            except Exception:
                active.append(t)
        logger.info(f"TED: {len(tenders)} geparst → {len(active)} mit aktiver Deadline")
        return active

    def _extract_multilang(self, field) -> str:
        if not field:
            return ""
        if isinstance(field, str):
            return field
        if isinstance(field, list):
            return field[0] if field else ""
        if isinstance(field, dict):
            for lang in ("deu", "ger", "de", "eng", "en"):
                val = field.get(lang)
                if val:
                    return val[0] if isinstance(val, list) else str(val)
            first = next(iter(field.values()), None)
            if first:
                return first[0] if isinstance(first, list) else str(first)
        return ""


# ─────────────────────────────────────────────────────────────────
# Deutsche Vergabeplattformen (Bund + alle 16 Bundesländer)
# Reihenfolge: Bundesplattform → Länder → Spezialplattformen
# ─────────────────────────────────────────────────────────────────

class EvergabeScraper:
    """
    Scraper für deutsche Vergabeplattformen.
    Deckt Bund, alle relevanten Bundesländer und Spezialplattformen ab.
    Probiert Quellen in Reihenfolge, sammelt von allen (mit Keyword-Filter).
    """

    RSS_SOURCES = [
        # ══════════════════════════════════════════════════════════════
        # BUNDESEBENE
        # ══════════════════════════════════════════════════════════════

        # ── service.bund.de (offizielle Bundesplattform) ──────────────
        ("service.bund.de",
         "https://www.service.bund.de/IMPORTE/Ausschreibungen/opensearch.html"
         "?view=processForm&resultCount=25&type=1&searchScope=1&tenderStatus=2&outputMode=rss"),
        ("service.bund.de-v2",
         "https://www.service.bund.de/SiteGlobals/Forms/Ausschreibungen/Suche/"
         "AusschreibungenSuche_Formular.html?view=processForm&resultCount=25"
         "&tenderStatus=2&outputMode=rss"),

        # ── evergabe-online.de (ITZ Bund) ─────────────────────────────
        ("evergabe-online",
         "https://www.evergabe-online.de/tenderinformation.rss"),

        # ── bund.de-feed ──────────────────────────────────────────────
        ("bund.de-feed",
         "https://www.bund.de/Content/DE/Bekanntmachungen/Suche.html"
         "?nn=3294906&type=1&outputMode=rss"),

        # ══════════════════════════════════════════════════════════════
        # GROSSE ÜBERREGIONALE PLATTFORMEN
        # ══════════════════════════════════════════════════════════════

        # ── DTVP (Deutsches Vergabeportal) ────────────────────────────
        ("DTVP",
         "https://www.dtvp.de/Center/notice/search.do?"
         "rss=true&resultCountType=20&legalBasisType=VOB"),
        ("DTVP-alt",
         "https://www.dtvp.de/Center/notice/search.do?format=rss&status=2"),

        # ── Vergabe24 (DTVP-Tochter) ──────────────────────────────────
        ("Vergabe24",
         "https://www.vergabe24.de/ausschreibungen?format=rss"),

        # ── Subreport ─────────────────────────────────────────────────
        ("Subreport",
         "https://www.subreport.de/E11000/ausschreibungen-rss.xml"),
        ("Subreport-alt",
         "https://www.subreport.de/rss/ausschreibungen.xml"),

        # ── Ausschreibungen.de ────────────────────────────────────────
        ("Ausschreibungen.de",
         "https://www.ausschreibungen.de/rss/ausschreibungen.xml"),

        # ── ibau.de (Bau & Infrastruktur) ────────────────────────────
        ("ibau",
         "https://www.ibau.de/rss/ausschreibungen/?format=rss"),
        ("ibau-alt",
         "https://www.ibau.de/ausschreibungen/rss/"),

        # ── Auftragsboerse.de ─────────────────────────────────────────
        ("Auftragsboerse",
         "https://www.auftragsboerse.de/rss/feed.xml"),
        ("Auftragsboerse-alt",
         "https://www.auftragsboerse.de/ausschreibungen/feed"),

        # ── Deutsche eVergabe ─────────────────────────────────────────
        ("DeutscheEVergabe",
         "https://www.deutsche-evergabe.de/rss/ausschreibungen"),
        ("DeutscheEVergabe-alt",
         "https://www.deutsche-evergabe.de/ausschreibungen?format=rss"),

        # ══════════════════════════════════════════════════════════════
        # BUNDESLAND-PLATTFORMEN
        # ══════════════════════════════════════════════════════════════

        # ── NRW (größtes Bundesland) ──────────────────────────────────
        ("VergabeNRW",
         "https://www.vergabe.nrw.de/VMPCenter/company/announcement/"
         "listAnnouncements.do?method=start&status=2&rss=true"),
        ("VergabeNRW-alt",
         "https://www.vergabe.nrw.de/VMPCenter/company/announcement/"
         "listAnnouncements.do?method=start&rss=true"),

        # ── Bayern ───────────────────────────────────────────────────
        ("VergabeBayern",
         "https://www.vergabe.Bayern.de/NetServer/TenderingProcedureSearchServlet"
         "?function=search&ContentId=VMPBayern_TenderListRSS&Status=2"),
        ("VergabeBayern-alt",
         "https://www.vergabe.Bayern.de/rss/ausschreibungen.xml"),

        # ── Baden-Württemberg ─────────────────────────────────────────
        ("StaatsanzeigerBW",
         "https://vergabe.staatsanzeiger-bw.de/NetServer/TenderingProcedureSearchServlet"
         "?function=search&ContentId=StAnzBW_TenderListRSS&Status=2"),
        ("LeiKaVergabeBW",
         "https://www.leika-vergabe.de/NetServer/TenderingProcedureSearchServlet"
         "?function=search&ContentId=LeIKa_TenderListRSS"),

        # ── Hessen ───────────────────────────────────────────────────
        ("HAD-Hessen",
         "https://www.had.de/onlinesuche_rss.html"),
        ("HAD-Hessen-alt",
         "https://www.had.de/rss/ausschreibungen.xml"),

        # ── Hamburg / Metropol-Nord ───────────────────────────────────
        ("MetropolVergabe",
         "https://www.metropol-vergabe.de/NetServer/TenderingProcedureSearchServlet"
         "?function=search&ContentId=Metropol_TenderListRSS&Status=2"),
        ("MetropolVergabe-alt",
         "https://www.metropol-vergabe.de/rss/ausschreibungen.xml"),

        # ── Sachsen ───────────────────────────────────────────────────
        ("VergabeSachsen",
         "https://www.vergabe.sachsen.de/VMPCenter/company/announcement/"
         "listAnnouncements.do?method=start&status=2&rss=true"),

        # ── Thüringen ─────────────────────────────────────────────────
        ("VergabeThueringen",
         "https://www.vergabe.thueringen.de/VMPCenter/company/announcement/"
         "listAnnouncements.do?method=start&rss=true"),

        # ── Niedersachsen ─────────────────────────────────────────────
        ("VergabeNiedersachsen",
         "https://www.vergabeplattform-niedersachsen.de/NetServer/"
         "TenderingProcedureSearchServlet?function=search&ContentId=NDS_TenderListRSS"),

        # ── Brandenburg / Berlin ──────────────────────────────────────
        ("VergabeBBB",
         "https://www.vergabeplattform.de/NetServer/TenderingProcedureSearchServlet"
         "?function=search&ContentId=BBB_TenderListRSS&Status=2"),

        # ── Rheinland-Pfalz ───────────────────────────────────────────
        ("eVergabeRLP",
         "https://evergabe.rlp.de/NetServer/TenderingProcedureSearchServlet"
         "?function=search&ContentId=RLP_TenderListRSS"),
    ]

    EVERGABE_URL = "https://www.evergabe-online.de/tenderinformation.html?0"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_recent_tenders(self, limit: int = 20, keywords: Optional[List[str]] = None) -> List[Dict]:
        tenders = []

        # Wenn Keywords übergeben → Keyword-Suche auf bund.de versuchen
        if keywords:
            kw_tenders = self._fetch_bund_keyword_search(keywords, limit)
            if kw_tenders:
                tenders.extend(kw_tenders)
                logger.info(f"✅ bund.de Keyword-Suche: {len(kw_tenders)} Treffer")

        # RSS-Quellen durchlaufen bis Ergebnis
        for name, url in self.RSS_SOURCES:
            if len(tenders) >= limit:
                break
            try:
                logger.info(f"📡 {name}: RSS abrufen...")
                result = self._fetch_rss(url, name, limit)
                if result:
                    # Deduplizieren gegen bereits gefundene
                    existing_ids = {t["id"] for t in tenders}
                    new = [t for t in result if t["id"] not in existing_ids]
                    tenders.extend(new)
                    logger.info(f"✅ {name}: {len(new)} neue Einträge")
                    if not keywords:
                        break  # Ohne Keywords: erste funktionierende Quelle reicht
            except Exception as e:
                logger.warning(f"{name} Fehler: {e}")

        if not tenders:
            logger.info("Alle RSS-Quellen leer — versuche evergabe-online HTML...")
            tenders = self._fetch_evergabe_html(limit)

        return self._filter_active(tenders)

    def _fetch_bund_keyword_search(self, keywords: List[str], limit: int = 15) -> List[Dict]:
        """Keyword-Suche auf service.bund.de über OpenSearch."""
        tenders = []
        kw_str = " ".join(keywords[:4])
        import urllib.parse
        encoded_kw = urllib.parse.quote(kw_str)

        urls = [
            f"https://www.service.bund.de/IMPORTE/Ausschreibungen/opensearch.html"
            f"?view=processForm&resultCount={limit}&type=1&searchScope=1"
            f"&tenderStatus=2&outputMode=rss&term={encoded_kw}",
        ]

        for url in urls:
            try:
                result = self._fetch_rss(url, "bund.de-keyword", limit)
                if result:
                    tenders = result
                    break
            except Exception as e:
                logger.warning(f"bund.de Keyword-Suche: {e}")

        return tenders

    def _fetch_rss(self, url: str, source_name: str, limit: int) -> List[Dict]:
        tenders = []
        try:
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            if resp.status_code != 200:
                logger.warning(f"{source_name}: HTTP {resp.status_code}")
                return []

            # Prüfe ob Antwort XML/RSS ist
            ct = resp.headers.get("Content-Type", "")
            if "html" in ct and "rss" not in ct and len(resp.content) < 500:
                logger.warning(f"{source_name}: Keine gültige RSS-Antwort (Content-Type: {ct})")
                return []

            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")[:limit]

            if not items:
                logger.warning(f"{source_name}: 0 <item> gefunden")
                return []

            logger.info(f"{source_name}: {len(items)} Items")
            for item in items:
                try:
                    t = self._parse_rss_item(item, source_name)
                    if t:
                        tenders.append(t)
                except Exception as e:
                    logger.warning(f"{source_name} Parse-Fehler: {e}")

        except requests.exceptions.ConnectionError:
            logger.warning(f"{source_name}: nicht erreichbar")
        except requests.exceptions.Timeout:
            logger.warning(f"{source_name}: Timeout")
        except Exception as e:
            logger.warning(f"{source_name} Fehler: {e}")

        return tenders

    def _parse_rss_item(self, item, source_name: str) -> Optional[Dict]:
        title_tag = item.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title or title.lower() in ("ausschreibungen", "vergabe", "rss"):
            return None

        link_tag = item.find("link")
        url = link_tag.get_text(strip=True) if link_tag else ""
        if not url:
            guid = item.find("guid")
            url = guid.get_text(strip=True) if guid else ""

        desc_tag = item.find("description")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Deadline aus verschiedenen RSS-Feldern extrahieren
        deadline = None
        for tag_name in ("frist", "deadline", "submissionDeadline", "pubDate"):
            tag = item.find(tag_name)
            if tag:
                dl_str = tag.get_text(strip=True)
                deadline = self._parse_date(dl_str)
                if deadline:
                    break

        cat_tag = item.find("category")
        buyer_category = cat_tag.get_text(strip=True) if cat_tag else "Behörde"

        # Buyer aus RSS-spezifischen Tags
        buyer_tag = item.find("auftraggeber") or item.find("publisher") or item.find("author")
        buyer_name = buyer_tag.get_text(strip=True) if buyer_tag else "Öffentlicher Auftraggeber"

        tender_id = f"{source_name.lower().replace(' ', '-')}-{abs(hash(url or title))}"

        return {
            "id": tender_id,
            "title": title[:300],
            "description": (description or f"Deutsche Ausschreibung via {source_name}")[:1000],
            "source": source_name.lower().replace(" ", ""),
            "source_url": url or self.EVERGABE_URL,
            "deadline": deadline.isoformat() if deadline else None,
            "buyer_name": buyer_name[:200],
            "buyer_category": buyer_category,
            "budget_min": None,
            "budget_max": None,
            "cpv_codes": "",
        }

    def _fetch_evergabe_html(self, limit: int) -> List[Dict]:
        """Fallback: evergabe-online.de HTML scrapen."""
        tenders = []
        try:
            resp = self.session.get(self.EVERGABE_URL, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"evergabe HTML: HTTP {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            # Versuche verschiedene Selektoren
            rows = (
                soup.select("tr.tender-row")
                or soup.select(".tender-list-item")
                or soup.select(".ausschreibung-item")
                or [r for r in soup.select("table tr")[1:] if r.find("a")]
            )
            logger.info(f"evergabe HTML: {len(rows)} Zeilen")

            for row in rows[:limit]:
                try:
                    cells = row.find_all(["td", "th"])
                    if not cells:
                        continue
                    title = cells[0].get_text(strip=True)
                    if not title:
                        title = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    link = row.find("a", href=True)
                    url = link["href"] if link else ""
                    if url and not url.startswith("http"):
                        url = "https://www.evergabe-online.de" + url
                    if title and len(title) > 5:
                        tenders.append({
                            "id": f"evergabe-{abs(hash(url or title))}",
                            "title": title[:300],
                            "description": "Deutsche Ausschreibung via evergabe-online.de",
                            "source": "evergabe-online.de",
                            "source_url": url or self.EVERGABE_URL,
                            "deadline": None,
                            "buyer_name": "Öffentlicher Auftraggeber",
                            "buyer_category": "Bund",
                            "budget_min": None,
                            "budget_max": None,
                            "cpv_codes": "",
                        })
                except Exception as e:
                    logger.warning(f"evergabe Parse-Fehler: {e}")

        except Exception as e:
            logger.error(f"evergabe HTML Fehler: {e}")

        return tenders

    def _filter_active(self, tenders: List[Dict]) -> List[Dict]:
        """Behält nur Ausschreibungen mit Deadline > jetzt + 24h."""
        min_date = datetime.now() + timedelta(hours=24)
        active = []
        for t in tenders:
            dl = t.get("deadline")
            if not dl:
                active.append(t)
                continue
            try:
                if datetime.fromisoformat(dl) > min_date:
                    active.append(t)
            except Exception:
                active.append(t)
        logger.info(f"Deutsche Quellen: {len(tenders)} gesamt → {len(active)} aktiv")
        return active

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        # RFC 2822 (RSS pubDate)
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str).replace(tzinfo=None)
        except Exception:
            pass
        # ISO 8601
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00").replace("+00:00", ""))
        except Exception:
            pass
        # Deutsches Format TT.MM.JJJJ
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except Exception:
            pass
        # JJJJ-MM-TT
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception:
            pass
        return None


# Rückwärtskompatibilität
BundDeScraper = EvergabeScraper


# ─────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────

class ScraperOrchestrator:
    """
    Koordiniert alle Scraper und dedupliziert Ergebnisse.
    Quellen: TED (EU), TED EU-weit, 16+ deutsche Vergabeplattformen.
    """

    def __init__(self):
        self.ted  = TEDScraper()
        self.bund = EvergabeScraper()

    def _merge(self, all_tenders: list, seen_ids: set, new_results: list, label: str):
        """Hilfsmethode: neue Ergebnisse dedupliziert einmergen."""
        added = 0
        for t in new_results:
            if t["id"] not in seen_ids:
                seen_ids.add(t["id"])
                all_tenders.append(t)
                added += 1
        logger.info(f"  {label}: {len(new_results)} abgerufen, {added} neu (gesamt {len(all_tenders)})")
        return added

    def scrape_all(self, limit_per_source: int = 25) -> List[Dict]:
        """
        Allgemeines Scraping ohne Profil-Kontext.
        Läuft alle Quellen durch: TED-DE, TED-EU, alle deutschen Plattformen.
        """
        all_tenders = []
        seen_ids = set()

        logger.info("🔄 Multi-Source Scraping gestartet (alle Quellen)...")

        sources = [
            # EU-Quellen
            ("TED-Deutschland",  lambda: self.ted.fetch_recent_tenders(limit_per_source)),
            ("TED-EU-weit",      lambda: self.ted.fetch_eu_wide(limit_per_source)),
            # Deutsche Plattformen (alle RSS_SOURCES werden intern durchlaufen)
            ("DE-Plattformen",   lambda: self.bund.fetch_recent_tenders(limit_per_source)),
        ]

        for name, fn in sources:
            try:
                result = fn()
                self._merge(all_tenders, seen_ids, result, name)
            except Exception as e:
                logger.error(f"Scraper {name} fehlgeschlagen: {e}")
            time.sleep(1)

        logger.info(f"📊 Gesamt dedupliziert: {len(all_tenders)} Ausschreibungen aus allen Quellen")
        return all_tenders

    def scrape_for_profile(self, keywords: List[str], cpv_codes: Optional[List[str]] = None,
                           limit_per_source: int = 25) -> List[Dict]:
        """
        Profil-aware Scraping: höhere Treffer-Relevanz durch keyword-basierte Queries.
        Läuft TED (DE + EU) + alle deutschen Plattformen mit Keyword-Filter.
        """
        all_tenders = []
        seen_ids = set()

        logger.info(f"🎯 Profil-Scraping für Keywords: {keywords[:5]}")

        # TED Deutschland: keyword-aware
        try:
            ted_de = self.ted.fetch_for_company(keywords, cpv_codes, limit_per_source)
            self._merge(all_tenders, seen_ids, ted_de, "TED-DE-Profil")
        except Exception as e:
            logger.error(f"TED-DE Profil Fehler: {e}")

        time.sleep(0.5)

        # TED EU-weit: zusätzliche EU-Treffer
        try:
            ted_eu = self.ted.fetch_eu_wide(limit_per_source)
            self._merge(all_tenders, seen_ids, ted_eu, "TED-EU-weit")
        except Exception as e:
            logger.error(f"TED-EU Profil Fehler: {e}")

        time.sleep(0.5)

        # Deutsche Plattformen: mit Keywords für höhere Relevanz
        try:
            bund_results = self.bund.fetch_recent_tenders(limit_per_source, keywords=keywords)
            self._merge(all_tenders, seen_ids, bund_results, "DE-Plattformen-Profil")
        except Exception as e:
            logger.error(f"DE-Plattformen Profil Fehler: {e}")

        logger.info(f"📊 Profil-Scraping: {len(all_tenders)} Ausschreibungen gesamt")
        return all_tenders
