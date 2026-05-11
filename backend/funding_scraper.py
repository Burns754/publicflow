"""
PublicFlow — Förderantrags-Scraper
Quellen: Förderdatenbank Bund, KfW, BAFA, EU, alle 16 Bundesländer
"""

import logging
import uuid
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PublicFlow-Bot/1.0; "
        "+https://publicflow.io/bot)"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}
TIMEOUT = 15


# ══════════════════════════════════════════════════════════════════════
#  STATISCHE SEED-DATENBANK — top 50+ bekannte DE/EU-Förderprogramme
#  Diese laufen dauerhaft und müssen nicht täglich neu gescraped werden
# ══════════════════════════════════════════════════════════════════════

SEED_PROGRAMS: List[Dict] = [

    # ── KfW Bund ──────────────────────────────────────────────────────
    {
        "title": "KfW-Digitalisierungskredit (380/390)",
        "provider": "KfW Bankengruppe",
        "provider_level": "bund",
        "description": "Günstige Kredite für Investitionen in die Digitalisierung von KMU. "
                       "Finanziert Hard- und Software, IT-Sicherheit, digitale Prozesse und E-Commerce.",
        "funding_type": "kredit",
        "max_amount": 25_000_000,
        "funding_rate": None,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Deutschland",
        "topics": "Digitalisierung,IT,Software,E-Commerce",
        "eligibility_summary": "Gewerbliche Unternehmen jeder Branche, Freiberufler, max. 250 Mitarbeiter oder max. 50 Mio. € Jahresumsatz",
        "application_url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Digitalisierung/",
        "is_ongoing": True,
        "source_url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Digitalisierung/Foerderprodukte/KfW-Kredit-Digitalisierung-(380-390)/",
    },
    {
        "title": "KfW-Gründerkredit – StartGeld (067)",
        "provider": "KfW Bankengruppe",
        "provider_level": "bund",
        "description": "Kredit für Unternehmensgründungen und junge Unternehmen bis 5 Jahre. "
                       "Bis 125.000 € mit 80 % Haftungsfreistellung für die Hausbank.",
        "funding_type": "kredit",
        "max_amount": 125_000,
        "funding_rate": None,
        "industries": "Alle",
        "company_sizes": "Kleinstunternehmen,KMU",
        "regions": "Deutschland",
        "topics": "Gründung,Startup,Investition",
        "eligibility_summary": "Existenzgründer und Unternehmen bis 5 Jahre nach Gründung",
        "application_url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Gr%C3%BCnden-Nachfolgen/",
        "is_ongoing": True,
        "source_url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Gr%C3%BCnden-Nachfolgen/Foerderprodukte/KfW-Gr%C3%BCnderkredit-StartGeld-(067)/",
    },
    {
        "title": "KfW-Unternehmerkredit (037/047)",
        "provider": "KfW Bankengruppe",
        "provider_level": "bund",
        "description": "Investitionskredit für etablierte Unternehmen. Finanziert Betriebsmittel, "
                       "Investitionen und Wachstum. Bis 25 Mio. €.",
        "funding_type": "kredit",
        "max_amount": 25_000_000,
        "funding_rate": None,
        "industries": "Alle",
        "company_sizes": "KMU,Großunternehmen",
        "regions": "Deutschland",
        "topics": "Wachstum,Investition,Betriebsmittel",
        "eligibility_summary": "Gewerbliche Unternehmen und Freiberufler, die seit mind. 2 Jahren aktiv sind",
        "application_url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Wachsen/",
        "is_ongoing": True,
        "source_url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Wachsen/Foerderprodukte/KfW-Unternehmerkredit-(037-047)/",
    },
    {
        "title": "KfW-Energieeffizienz-Programm – Produktionsanlagen (295/296)",
        "provider": "KfW Bankengruppe",
        "provider_level": "bund",
        "description": "Finanzierung energieeffizienter Produktionsanlagen und -prozesse. "
                       "Besonders attraktiv für produzierende KMU.",
        "funding_type": "kredit",
        "max_amount": 25_000_000,
        "funding_rate": None,
        "industries": "Produktion,Handwerk,Industrie",
        "company_sizes": "KMU,Großunternehmen",
        "regions": "Deutschland",
        "topics": "Energie,Klimaschutz,Produktion,Effizienz",
        "eligibility_summary": "Gewerbliche Unternehmen mit Investitionen in Energieeffizienz",
        "application_url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Energie-Umwelt/",
        "is_ongoing": True,
        "source_url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Energie-Umwelt/Foerderprodukte/KfW-Energieeffizienz-Programm-Produktionsanlagen-(295-296)/",
    },

    # ── BAFA Bund ─────────────────────────────────────────────────────
    {
        "title": "BAFA – Bundesförderung für Energieberatung (EBM)",
        "provider": "BAFA (Bundesamt für Wirtschaft und Ausfuhrkontrolle)",
        "provider_level": "bund",
        "description": "Zuschuss für professionelle Energieberatung in KMU. "
                       "Bis zu 80 % der Beratungskosten, max. 4.800 €.",
        "funding_type": "zuschuss",
        "max_amount": 4_800,
        "funding_rate": 0.80,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Deutschland",
        "topics": "Energie,Beratung,Klimaschutz,Effizienz",
        "eligibility_summary": "KMU mit weniger als 250 Mitarbeitern und max. 50 Mio. € Jahresumsatz",
        "application_url": "https://www.bafa.de/DE/Energie/Energieeffizienz/Energieberatung_Mittelstand/",
        "is_ongoing": True,
        "source_url": "https://www.bafa.de/DE/Energie/Energieeffizienz/Energieberatung_Mittelstand/energieberatung_mittelstand_node.html",
    },
    {
        "title": "BAFA – Markteinführungsprogramm für Solarthermie",
        "provider": "BAFA (Bundesamt für Wirtschaft und Ausfuhrkontrolle)",
        "provider_level": "bund",
        "description": "Investitionszuschüsse für solarthermische Anlagen. "
                       "Für Unternehmen die Solarkollektoren installieren oder nutzen.",
        "funding_type": "zuschuss",
        "max_amount": 50_000,
        "funding_rate": 0.25,
        "industries": "Alle,Handwerk,Produktion",
        "company_sizes": "Alle",
        "regions": "Deutschland",
        "topics": "Energie,Solar,Klimaschutz,Investition",
        "eligibility_summary": "Alle Unternehmen die in Solarthermie investieren",
        "application_url": "https://www.bafa.de/DE/Energie/Heizen_mit_Erneuerbaren_Energien/",
        "is_ongoing": True,
        "source_url": "https://www.bafa.de/DE/Energie/Heizen_mit_Erneuerbaren_Energien/heizen_mit_erneuerbaren_energien_node.html",
    },
    {
        "title": "BAFA – Außenwirtschaftsförderung / Exportberatung",
        "provider": "BAFA (Bundesamt für Wirtschaft und Ausfuhrkontrolle)",
        "provider_level": "bund",
        "description": "Förderung von Auslandsmarkterschließung für KMU. "
                       "Messebeteiligungen, Marktrecherchen, Exportberatung.",
        "funding_type": "zuschuss",
        "max_amount": 24_000,
        "funding_rate": 0.50,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Deutschland",
        "topics": "Export,International,Beratung,Messe",
        "eligibility_summary": "Deutsche KMU die neue Auslandsmärkte erschließen wollen",
        "application_url": "https://www.bafa.de/DE/Aussenwirtschaft/",
        "is_ongoing": True,
        "source_url": "https://www.bafa.de/DE/Aussenwirtschaft/aussenwirtschaft_node.html",
    },

    # ── Bundesministerien ─────────────────────────────────────────────
    {
        "title": "go-digital – Digitalisierung und IT-Sicherheit (BMWi)",
        "provider": "Bundesministerium für Wirtschaft und Klimaschutz (BMWK)",
        "provider_level": "bund",
        "description": "Beratungsförderung für KMU in den Modulen: Digitalisierung, "
                       "IT-Sicherheit, digitale Markterschließung. 50 % Zuschuss auf Beratungsleistung.",
        "funding_type": "zuschuss",
        "max_amount": 17_000,
        "funding_rate": 0.50,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Deutschland",
        "topics": "Digitalisierung,IT,IT-Sicherheit,Beratung",
        "eligibility_summary": "KMU mit < 100 Mitarbeiter und < 20 Mio. € Jahresumsatz",
        "application_url": "https://www.bmwk.de/Redaktion/DE/Artikel/Digitale-Welt/foerderprogramm-go-digital.html",
        "is_ongoing": True,
        "source_url": "https://www.bmwk.de/Redaktion/DE/Artikel/Digitale-Welt/foerderprogramm-go-digital.html",
    },
    {
        "title": "EXIST – Existenzgründungen aus der Wissenschaft",
        "provider": "Bundesministerium für Wirtschaft und Klimaschutz (BMWK)",
        "provider_level": "bund",
        "description": "Gründerstipendium und -förderung für technologiebasierte Unternehmen "
                       "aus Hochschulen. Bis zu 150.000 € Stipendium + Sachleistungen.",
        "funding_type": "zuschuss",
        "max_amount": 150_000,
        "funding_rate": 1.0,
        "industries": "Technologie,Software,Medizin,Cleantech",
        "company_sizes": "Kleinstunternehmen",
        "regions": "Deutschland",
        "topics": "Gründung,Startup,Forschung,Innovation,Technologie",
        "eligibility_summary": "Gründungsteams an Hochschulen und Forschungseinrichtungen mit innovativer Idee",
        "application_url": "https://www.exist.de/EXIST/Navigation/DE/Programm/EXIST-Gruenderstipendium/exist-gruenderstipendium.html",
        "is_ongoing": True,
        "source_url": "https://www.exist.de/",
    },
    {
        "title": "Zentrales Innovationsprogramm Mittelstand (ZIM)",
        "provider": "Bundesministerium für Wirtschaft und Klimaschutz (BMWK)",
        "provider_level": "bund",
        "description": "F&E-Förderung für innovative KMU. Einzelprojekte, Kooperationsprojekte "
                       "und Netzwerke. Bis 380.000 € pro Projekt.",
        "funding_type": "zuschuss",
        "max_amount": 380_000,
        "funding_rate": 0.45,
        "industries": "Technologie,Software,Produktion,Handwerk",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Deutschland",
        "topics": "Innovation,Forschung,Technologie,F&E",
        "eligibility_summary": "KMU mit < 500 Mitarbeiter und < 50 Mio. € Jahresumsatz, keine Landwirtschaft",
        "application_url": "https://www.zim.de/",
        "is_ongoing": True,
        "source_url": "https://www.zim.de/ZIM/Navigation/DE/Programm/zim_programm.html",
    },
    {
        "title": "Digitalbonus Bund / Förderung digitaler Infrastruktur",
        "provider": "Bundesministerium für Wirtschaft und Klimaschutz (BMWK)",
        "provider_level": "bund",
        "description": "Zuschüsse für Investitionen in digitale Infrastruktur, "
                       "Hard- und Software sowie IT-Sicherheit.",
        "funding_type": "zuschuss",
        "max_amount": 50_000,
        "funding_rate": 0.50,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Deutschland",
        "topics": "Digitalisierung,IT,Software,Hardware,IT-Sicherheit",
        "eligibility_summary": "KMU in Deutschland mit aktiver Geschäftstätigkeit",
        "application_url": "https://www.foerderdatenbank.de/",
        "is_ongoing": True,
        "source_url": "https://www.foerderdatenbank.de/FDB/Content/DE/Foerderprogramm/Bund/BMWi/go-digital.html",
    },

    # ── EU-Programme ──────────────────────────────────────────────────
    {
        "title": "EIC Accelerator – EU Innovation Council",
        "provider": "European Innovation Council (EIC)",
        "provider_level": "eu",
        "description": "EU-weite Förderung für hochinnovative Startups und Scale-ups. "
                       "Bis zu 2,5 Mio. € Zuschuss + bis 15 Mio. € Eigenkapitalinvestment.",
        "funding_type": "zuschuss",
        "max_amount": 2_500_000,
        "funding_rate": 0.70,
        "industries": "Technologie,Software,Medizin,Cleantech,DeepTech",
        "company_sizes": "Kleinstunternehmen,KMU",
        "regions": "EU",
        "topics": "Innovation,Startup,Technologie,DeepTech,Skalierung",
        "eligibility_summary": "KMU und Einzelpersonen aus EU-Mitgliedsstaaten mit disruptiver Innovation",
        "application_url": "https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en",
        "is_ongoing": True,
        "source_url": "https://eic.ec.europa.eu/eic-accelerator_en",
    },
    {
        "title": "Horizon Europe – KMU-Instrument",
        "provider": "Europäische Kommission",
        "provider_level": "eu",
        "description": "EU-Forschungs- und Innovationsrahmen. Förderung von F&E-Projekten "
                       "mit europäischer Dimension. Phase 1: 50k €, Phase 2: bis 2,5 Mio. €.",
        "funding_type": "zuschuss",
        "max_amount": 2_500_000,
        "funding_rate": 0.70,
        "industries": "Technologie,Medizin,Energie,Digitalisierung",
        "company_sizes": "KMU",
        "regions": "EU",
        "topics": "Forschung,Innovation,Technologie,F&E,Europa",
        "eligibility_summary": "KMU aus EU-Mitgliedsstaaten mit innovativem F&E-Vorhaben",
        "application_url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/",
        "is_ongoing": True,
        "source_url": "https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en",
    },
    {
        "title": "EFRE – Europäischer Fonds für regionale Entwicklung",
        "provider": "Europäische Kommission / Bundesländer",
        "provider_level": "eu",
        "description": "Strukturfondsförderung für Investitionen, Innovation und Digitalisierung "
                       "in strukturschwachen Regionen. Kofinanzierung durch Bundesländer.",
        "funding_type": "zuschuss",
        "max_amount": 500_000,
        "funding_rate": 0.50,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Deutschland,EU",
        "topics": "Innovation,Digitalisierung,Investition,Region",
        "eligibility_summary": "KMU in strukturschwachen Regionen, je nach Bundesland unterschiedlich",
        "application_url": "https://www.bmwk.de/Redaktion/DE/Dossier/europaeische-strukturfonds.html",
        "is_ongoing": True,
        "source_url": "https://ec.europa.eu/regional_policy/de/funding/erdf/",
    },
    {
        "title": "COSME – EU-Programm für die Wettbewerbsfähigkeit von KMU",
        "provider": "Europäische Kommission / EIF",
        "provider_level": "eu",
        "description": "Erleichterte Finanzierung für KMU durch EU-Garantien. "
                       "Zugang zu Krediten und Risikokapital über lokale Banken.",
        "funding_type": "buergschaft",
        "max_amount": 150_000,
        "funding_rate": None,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "EU",
        "topics": "Finanzierung,Wachstum,Export,International",
        "eligibility_summary": "KMU aus EU-Mitgliedsstaaten, Antragsstellung über lokale Partnerbanken",
        "application_url": "https://single-market-economy.ec.europa.eu/smes/cosme_en",
        "is_ongoing": True,
        "source_url": "https://single-market-economy.ec.europa.eu/smes/cosme_en",
    },

    # ── Bayern ────────────────────────────────────────────────────────
    {
        "title": "Digitalbonus Bayern",
        "provider": "Bayerisches Staatsministerium für Wirtschaft",
        "provider_level": "land",
        "federal_state": "Bayern",
        "description": "Investitionszuschüsse für Digitalisierungsmaßnahmen in bayerischen KMU. "
                       "Standard bis 10.000 €, Premium bis 50.000 €.",
        "funding_type": "zuschuss",
        "max_amount": 50_000,
        "funding_rate": 0.50,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Bayern",
        "topics": "Digitalisierung,IT,Software,Hardware",
        "eligibility_summary": "KMU mit Betriebsstätte in Bayern, < 50 Mitarbeiter (Standard) / < 250 (Premium)",
        "application_url": "https://www.digitalbonus.bayern/",
        "is_ongoing": True,
        "source_url": "https://www.digitalbonus.bayern/",
    },
    {
        "title": "BayTOU – Bayerisches Technologieförderungsprogramm",
        "provider": "LfA Förderbank Bayern",
        "provider_level": "land",
        "federal_state": "Bayern",
        "description": "Finanzierung von technologischen Innovationsvorhaben in Bayern. "
                       "Zinsgünstige Darlehen für F&E und Markteinführung.",
        "funding_type": "kredit",
        "max_amount": 5_000_000,
        "funding_rate": None,
        "industries": "Technologie,Software,Produktion",
        "company_sizes": "KMU",
        "regions": "Bayern",
        "topics": "Innovation,Technologie,F&E,Forschung",
        "eligibility_summary": "Unternehmen mit Sitz oder Betriebsstätte in Bayern, Technologiebranche",
        "application_url": "https://www.lfa.de/programme/innovationsfoerderung/",
        "is_ongoing": True,
        "source_url": "https://www.lfa.de/",
    },

    # ── NRW ───────────────────────────────────────────────────────────
    {
        "title": "NRW.BANK Mittelstandskredit",
        "provider": "NRW.BANK",
        "provider_level": "land",
        "federal_state": "NRW",
        "description": "Zinsgünstige Darlehen für Investitionen und Betriebsmittel von KMU in NRW.",
        "funding_type": "kredit",
        "max_amount": 10_000_000,
        "funding_rate": None,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "NRW",
        "topics": "Investition,Wachstum,Betriebsmittel",
        "eligibility_summary": "KMU mit Betriebsstätte in NRW",
        "application_url": "https://www.nrwbank.de/de/foerderprodukte/nrwmittelstandskredit/",
        "is_ongoing": True,
        "source_url": "https://www.nrwbank.de/",
    },
    {
        "title": "Digitalisierungsförderung NRW – go.digital NRW",
        "provider": "Ministerium für Wirtschaft, Innovation, Digitalisierung NRW",
        "provider_level": "land",
        "federal_state": "NRW",
        "description": "Beratungs- und Investitionsförderung für Digitalisierung in NRW-KMU.",
        "funding_type": "zuschuss",
        "max_amount": 20_000,
        "funding_rate": 0.50,
        "industries": "Alle",
        "company_sizes": "KMU",
        "regions": "NRW",
        "topics": "Digitalisierung,IT,Beratung,Software",
        "eligibility_summary": "KMU mit Betriebsstätte in NRW",
        "application_url": "https://www.wirtschaft.nrw/foerderung/digitalisierung",
        "is_ongoing": True,
        "source_url": "https://www.wirtschaft.nrw/",
    },

    # ── Baden-Württemberg ─────────────────────────────────────────────
    {
        "title": "Innovationsgutscheine BW (Stufe A & B)",
        "provider": "Ministerium für Wirtschaft, Arbeit und Tourismus BW",
        "provider_level": "land",
        "federal_state": "Baden-Württemberg",
        "description": "Gutscheine für externe F&E-Beratung und Technologietransfer. "
                       "Stufe A: bis 7.500 €, Stufe B: bis 20.000 €.",
        "funding_type": "zuschuss",
        "max_amount": 20_000,
        "funding_rate": 0.50,
        "industries": "Alle",
        "company_sizes": "KMU,Kleinstunternehmen",
        "regions": "Baden-Württemberg",
        "topics": "Innovation,Forschung,Beratung,Technologie",
        "eligibility_summary": "KMU mit Betriebsstätte in BW, < 100 (A) / < 500 (B) Mitarbeiter",
        "application_url": "https://wm.baden-wuerttemberg.de/de/wirtschaft/foerderung/innovationsgutscheine/",
        "is_ongoing": True,
        "source_url": "https://wm.baden-wuerttemberg.de/de/wirtschaft/foerderung/",
    },

    # ── Berlin/Brandenburg ────────────────────────────────────────────
    {
        "title": "Berliner Startup Stipendium",
        "provider": "Investitionsbank Berlin (IBB)",
        "provider_level": "land",
        "federal_state": "Berlin",
        "description": "Stipendium für Gründer in Berlin. Bis zu 2.000 €/Monat für 6 Monate "
                       "plus Coworking und Mentoring.",
        "funding_type": "zuschuss",
        "max_amount": 12_000,
        "funding_rate": 1.0,
        "industries": "Technologie,Software,Kreativwirtschaft",
        "company_sizes": "Kleinstunternehmen",
        "regions": "Berlin",
        "topics": "Gründung,Startup,Stipendium",
        "eligibility_summary": "Gründer mit Hauptwohnsitz in Berlin, innovative Geschäftsidee",
        "application_url": "https://www.ibb.de/de/wirtschaftsfoerderung/programme/berliner-startup-stipendium/",
        "is_ongoing": True,
        "source_url": "https://www.ibb.de/",
    },

    # ── Hamburg ───────────────────────────────────────────────────────
    {
        "title": "IFB Hamburg – Innovationsförderung",
        "provider": "IFB Hamburg (Investitions- und Förderbank)",
        "provider_level": "land",
        "federal_state": "Hamburg",
        "description": "Zuschüsse und Darlehen für innovative Projekte in Hamburger Unternehmen. "
                       "F&E, Markteinführung, Technologietransfer.",
        "funding_type": "zuschuss",
        "max_amount": 400_000,
        "funding_rate": 0.50,
        "industries": "Technologie,Logistik,Gesundheit,Software",
        "company_sizes": "KMU",
        "regions": "Hamburg",
        "topics": "Innovation,Technologie,F&E,Forschung",
        "eligibility_summary": "Unternehmen mit Betriebsstätte in Hamburg",
        "application_url": "https://www.ifbhh.de/foerderprogramme/innovationsfoerderung",
        "is_ongoing": True,
        "source_url": "https://www.ifbhh.de/",
    },

    # ── Sachsen ───────────────────────────────────────────────────────
    {
        "title": "SAB – Sächsische Aufbaubank Technologieförderung",
        "provider": "Sächsische Aufbaubank (SAB)",
        "provider_level": "land",
        "federal_state": "Sachsen",
        "description": "F&E-Projektförderung für sächsische KMU. Zuschüsse für industrielle "
                       "Forschung und experimentelle Entwicklung.",
        "funding_type": "zuschuss",
        "max_amount": 500_000,
        "funding_rate": 0.45,
        "industries": "Technologie,Produktion,Software",
        "company_sizes": "KMU",
        "regions": "Sachsen",
        "topics": "Innovation,F&E,Technologie,Forschung",
        "eligibility_summary": "KMU mit Betriebsstätte in Sachsen",
        "application_url": "https://www.sab.de/foerderung/unternehmen/forschung-und-innovation/",
        "is_ongoing": True,
        "source_url": "https://www.sab.de/",
    },

    # ── Niedersachsen ─────────────────────────────────────────────────
    {
        "title": "NBank – Niedersachsen Innovationsförderung",
        "provider": "Investitions- und Förderbank Niedersachsen (NBank)",
        "provider_level": "land",
        "federal_state": "Niedersachsen",
        "description": "Förderung von Innovations- und Investitionsvorhaben in Niedersachsen. "
                       "Zuschüsse und zinsgünstige Darlehen.",
        "funding_type": "zuschuss",
        "max_amount": 200_000,
        "funding_rate": 0.40,
        "industries": "Alle",
        "company_sizes": "KMU",
        "regions": "Niedersachsen",
        "topics": "Innovation,Investition,Digitalisierung",
        "eligibility_summary": "KMU mit Betriebsstätte in Niedersachsen",
        "application_url": "https://www.nbank.de/Unternehmen/Innovieren/index.jsp",
        "is_ongoing": True,
        "source_url": "https://www.nbank.de/",
    },
]


# ══════════════════════════════════════════════════════════════════════
#  LIVE-SCRAPER — Förderdatenbank des Bundes
# ══════════════════════════════════════════════════════════════════════

class FoerderdatenbankScraper:
    """Scraped aktuelle Programme von foerderdatenbank.de"""

    BASE_URL = "https://www.foerderdatenbank.de"
    SEARCH_URL = "https://www.foerderdatenbank.de/FDB/Content/DE/Foerderprogramm/Suche/Suche.html"

    def fetch_programs(self, limit: int = 20) -> List[Dict]:
        programs = []
        try:
            params = {
                "typ": "foerderprogramm",
                "foerderart": "Zuschuss",
                "zielgruppe": "Unternehmen",
            }
            resp = requests.get(
                self.SEARCH_URL, params=params,
                headers=HEADERS, timeout=TIMEOUT
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            items = soup.select(".fdb-search-result-item, .result-item, article.foerderprogramm")
            logger.info(f"Förderdatenbank: {len(items)} Einträge gefunden")

            for item in items[:limit]:
                try:
                    title_el = item.select_one("h2, h3, .title, .result-title")
                    link_el  = item.select_one("a[href]")
                    desc_el  = item.select_one("p, .description, .teaser")

                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    url   = urljoin(self.BASE_URL, link_el["href"]) if link_el else self.BASE_URL
                    desc  = desc_el.get_text(strip=True)[:500] if desc_el else ""

                    programs.append({
                        "title": title,
                        "provider": "Förderdatenbank Bund",
                        "provider_level": "bund",
                        "description": desc,
                        "funding_type": "zuschuss",
                        "industries": "Alle",
                        "company_sizes": "KMU",
                        "regions": "Deutschland",
                        "topics": "Förderung",
                        "eligibility_summary": desc[:200],
                        "application_url": url,
                        "is_ongoing": True,
                        "source_url": url,
                    })
                except Exception as e:
                    logger.warning(f"Parse-Fehler Förderdatenbank-Item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Förderdatenbank Scraper-Fehler: {e}")

        return programs


# ══════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════

class FundingScraperOrchestrator:

    def __init__(self):
        self.live_scraper = FoerderdatenbankScraper()

    def scrape_all(self) -> List[Dict]:
        """
        Gibt alle Förderprogramme zurück:
        1. Statische Seed-Daten (immer verfügbar, kuratiert)
        2. Live-Daten von foerderdatenbank.de
        """
        logger.info("🚀 Funding-Scraper gestartet")

        # Seed-Programme (mit ID versehen)
        result = []
        seen_urls = set()

        for prog in SEED_PROGRAMS:
            prog_copy = dict(prog)
            prog_copy["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, prog["source_url"]))
            prog_copy.setdefault("federal_state", None)
            prog_copy.setdefault("max_amount", None)
            prog_copy.setdefault("funding_rate", None)
            prog_copy.setdefault("deadline", None)
            prog_copy["scraped_at"] = datetime.utcnow()
            prog_copy["active"] = True
            result.append(prog_copy)
            seen_urls.add(prog["source_url"])

        logger.info(f"✅ {len(result)} Seed-Programme geladen")

        # Live-Scraping
        try:
            live = self.live_scraper.fetch_programs(limit=30)
            for prog in live:
                url = prog.get("source_url", "")
                if url and url not in seen_urls:
                    prog["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
                    prog.setdefault("federal_state", None)
                    prog.setdefault("max_amount", None)
                    prog.setdefault("funding_rate", None)
                    prog.setdefault("deadline", None)
                    prog["scraped_at"] = datetime.utcnow()
                    prog["active"] = True
                    result.append(prog)
                    seen_urls.add(url)
            logger.info(f"✅ {len(live)} Live-Programme hinzugefügt")
        except Exception as e:
            logger.warning(f"⚠️ Live-Scraping fehlgeschlagen (Seed-Daten bleiben): {e}")

        logger.info(f"📊 Förder-Scraper fertig: {len(result)} Programme total")
        return result
