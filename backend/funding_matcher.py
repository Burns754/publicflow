"""
PublicFlow — Förder-Matcher
KI-Matching: Unternehmensprofil ↔ Förderprogramm
Gleiche Architektur wie TenderMatcher (Claude + Regel-Fallback)
"""

import anthropic
import logging
import os
import json
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


class FundingMatcher:

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
        if self.client:
            logger.info("✅ FundingMatcher: Claude API aktiv")
        else:
            logger.warning("⚠️  FundingMatcher: Kein API-Key — nutze Regel-Matching")

    def calculate_match_score(self, company: Dict, program: Dict) -> Tuple[float, str]:
        if self.client:
            return self._claude_match(company, program)
        return self._rule_based_match(company, program)

    # ── Claude-basiertes Matching ──────────────────────────────────────

    def _claude_match(self, company: Dict, program: Dict) -> Tuple[float, str]:
        max_amount_str = (
            f"bis {program.get('max_amount', 0):,.0f} €"
            if program.get("max_amount") else "nicht angegeben"
        )
        rate_str = (
            f"{int(program.get('funding_rate', 0) * 100)} %"
            if program.get("funding_rate") else "variabel"
        )

        prompt = f"""Du bist Förderberater und bewertest, ob ein Förderprogramm für ein Unternehmen geeignet ist.

UNTERNEHMEN (anonymisiert):
- Branche: {company.get('industry', 'N/A')}
- Kompetenzen/Keywords: {company.get('experience_keywords', 'N/A')}
- Größe: {company.get('company_size', 'N/A')}
- Regionen: {company.get('regions', 'N/A')}
- Gründungsjahr: {company.get('founded_year', 'N/A')}
- Beschreibung: {(company.get('description') or '')[:200]}

FÖRDERPROGRAMM:
- Name: {program.get('title', 'N/A')}
- Anbieter: {program.get('provider', 'N/A')} ({program.get('provider_level', 'N/A')})
- Art: {program.get('funding_type', 'N/A')}
- Fördersumme: {max_amount_str}
- Förderquote: {rate_str}
- Zielgruppe: {program.get('company_sizes', 'N/A')}
- Branchen: {program.get('industries', 'N/A')}
- Region: {program.get('regions', 'N/A')}
- Themen: {program.get('topics', 'N/A')}
- Antragsvoraussetzungen: {(program.get('eligibility_summary') or '')[:300]}

Bewerte die Passung und antworte NUR mit JSON, keine Erklärung:
{{"score": <0-100>, "reasoning": "<max 220 Zeichen auf Deutsch, konkret warum passend/nicht passend>"}}

Score-Skala:
0-29:  nicht geeignet (falsche Branche, Region, Größe)
30-49: möglicherweise geeignet
50-69: gut geeignet
70-89: sehr gut passend
90-100: perfekte Übereinstimmung"""

        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=250,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1].replace("json", "").strip()

            result = json.loads(raw)
            score = float(result.get("score", 0))
            reasoning = result.get("reasoning", "Keine Begründung")
            logger.info(f"🤖 Förder-Match: {score:.0f}/100 — {reasoning[:60]}")
            return score, reasoning

        except (json.JSONDecodeError, anthropic.APIError, Exception) as e:
            logger.warning(f"Förder-Matching Fehler ({type(e).__name__}): {e} — Fallback")
            return self._rule_based_match(company, program)

    # ── Regel-basiertes Matching ───────────────────────────────────────

    def _rule_based_match(self, company: Dict, program: Dict) -> Tuple[float, str]:
        score = 0.0
        reasons = []

        # 1. Branchen-Matching (30 Punkte)
        prog_industries = [i.strip().lower() for i in (program.get("industries") or "").split(",")]
        comp_industry   = (company.get("industry") or "").lower()
        comp_keywords   = (company.get("experience_keywords") or "").lower()

        if "alle" in prog_industries:
            score += 30
            reasons.append("✅ Alle Branchen förderfähig")
        elif comp_industry and any(ind in comp_industry or comp_industry in ind
                                   for ind in prog_industries if ind):
            score += 30
            reasons.append(f"✅ Branche passend: {comp_industry}")
        elif any(kw in comp_keywords for ind in prog_industries for kw in [ind] if ind):
            score += 15
            reasons.append("⚡ Teilweise Branchen-Überschneidung")
        else:
            reasons.append("⚠️ Branche passt möglicherweise nicht")

        # 2. Regionen-Matching (25 Punkte)
        prog_region = (program.get("regions") or "").lower()
        comp_region = (company.get("regions") or "").lower()

        if "deutschland" in prog_region and "deutschland" in comp_region:
            score += 25
            reasons.append("📍 Region Deutschland passt")
        elif "eu" in prog_region and ("eu" in comp_region or "deutschland" in comp_region):
            score += 25
            reasons.append("📍 EU-Region passt")
        elif any(r.strip().lower() in prog_region
                 for r in comp_region.split(",") if r.strip()):
            score += 25
            reasons.append("📍 Bundesland-Region passt")
        elif "deutschland" in prog_region or "eu" in prog_region:
            score += 15
            reasons.append("📍 Bundesweite Förderung (prüfen)")
        else:
            reasons.append("⚠️ Region möglicherweise nicht abgedeckt")

        # 3. Unternehmensgröße (20 Punkte)
        prog_sizes   = [s.strip().lower() for s in (program.get("company_sizes") or "").split(",")]
        comp_size    = (company.get("company_size") or "").lower()
        founded_year = company.get("founded_year")

        if "alle" in prog_sizes:
            score += 20
            reasons.append("✅ Alle Unternehmensgrößen förderfähig")
        elif comp_size and any(comp_size in s or s in comp_size for s in prog_sizes):
            score += 20
            reasons.append(f"✅ Unternehmensgröße passt: {comp_size}")
        elif "kmu" in prog_sizes:
            score += 10
            reasons.append("⚡ Vermutlich als KMU förderfähig")

        # Gründungsbonus
        if founded_year and "gründung" in (program.get("topics") or "").lower():
            years_old = datetime.now().year - int(founded_year)
            if years_old <= 5:
                score += 5
                reasons.append(f"🌱 Junges Unternehmen ({years_old} Jahre alt)")

        # 4. Themen-Matching via Keywords (25 Punkte)
        prog_topics  = (program.get("topics") or "").lower()
        all_comp_text = f"{comp_industry} {comp_keywords} {company.get('description', '')}".lower()
        topic_words  = [t.strip() for t in prog_topics.split(",") if t.strip()]
        hits         = sum(1 for t in topic_words if t in all_comp_text)

        if topic_words:
            topic_score = min(25, (hits / len(topic_words)) * 25)
            score += topic_score
            if hits > 0:
                reasons.append(f"🎯 {hits}/{len(topic_words)} Themen-Keywords treffen")
            else:
                reasons.append("❓ Keine Themen-Keywords gefunden")

        from datetime import datetime as dt
        return min(100.0, score), " · ".join(reasons)


# ══════════════════════════════════════════════════════════════════════
#  MATCHING SERVICE
# ══════════════════════════════════════════════════════════════════════

class FundingMatchingService:

    def __init__(self):
        self.matcher = FundingMatcher()

    def match_all(self, companies: List[Dict], programs: List[Dict],
                  min_score: float = 35.0) -> List[Dict]:
        matches = []
        logger.info(f"🔄 Förder-Matching: {len(companies)} Unternehmen × {len(programs)} Programme")

        for company in companies:
            for program in programs:
                score, reasoning = self.matcher.calculate_match_score(company, program)
                if score >= min_score:
                    matches.append({
                        "company_id": company["id"],
                        "program_id": program["id"],
                        "match_score": round(score, 1),
                        "reasoning": reasoning,
                    })

        logger.info(f"📊 {len(matches)} Förder-Matches gefunden (min_score={min_score})")
        return sorted(matches, key=lambda m: m["match_score"], reverse=True)

    def match_single_company(self, company: Dict, programs: List[Dict],
                              min_score: float = 35.0) -> List[Dict]:
        """Matching nur für ein Unternehmen — für On-Demand API-Calls"""
        matches = []
        for program in programs:
            score, reasoning = self.matcher.calculate_match_score(company, program)
            if score >= min_score:
                matches.append({
                    "company_id": company["id"],
                    "program_id": program["id"],
                    "match_score": round(score, 1),
                    "reasoning": reasoning,
                    "program": program,
                })
        return sorted(matches, key=lambda m: m["match_score"], reverse=True)


# ══════════════════════════════════════════════════════════════════════
#  KI-ANTRAGSVORLAGEN GENERATOR
# ══════════════════════════════════════════════════════════════════════

class FundingDraftGenerator:
    """Generiert KI-Antragsvorlagen basierend auf Unternehmensprofil + Programm"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

    def generate_draft(self, company: Dict, program: Dict) -> str:
        if not self.client:
            return self._fallback_draft(company, program)

        max_amount_str = (
            f"bis {program.get('max_amount', 0):,.0f} €"
            if program.get("max_amount") else "variabel"
        )

        prompt = f"""Du bist Förderberater und hilfst KMUs bei Förderanträgen.
Erstelle eine strukturierte Antragsvorlage (Entwurf) für das folgende Förderprogramm.

FÖRDERPROGRAMM: {program.get('title')}
Anbieter: {program.get('provider')}
Art: {program.get('funding_type')} | Summe: {max_amount_str}
Voraussetzungen: {program.get('eligibility_summary', '')[:300]}

UNTERNEHMENSDATEN (vom Nutzer zu ergänzen, eckige Klammern = Platzhalter):
- Branche: {company.get('industry', '[Branche eintragen]')}
- Größe: {company.get('company_size', '[Mitarbeiterzahl]')}
- Tätigkeitsfelder: {company.get('experience_keywords', '[Kompetenzen]')}
- Region: {company.get('regions', 'Deutschland')}

Erstelle eine professionelle, vollständige Antragsvorlage auf Deutsch mit:
1. Unternehmensvorstellung (2-3 Sätze, mit Platzhaltern)
2. Projektbeschreibung / Verwendungszweck (3-4 Sätze)
3. Förderbedarf und Begründung (2-3 Sätze)
4. Erwartete Ergebnisse / Wirkung (2-3 Sätze)

Platzhalter in [eckigen Klammern] kennzeichnen wo der Nutzer eigene Daten eintragen muss.
Sprache: professionelles, klares Deutsch. Keine Floskeln. Direkt antragstauglich."""

        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            draft = message.content[0].text.strip()
            logger.info(f"✅ Antragsvorlage generiert für: {program.get('title', '?')[:40]}")
            return draft
        except Exception as e:
            logger.error(f"Draft-Generierung fehlgeschlagen: {e}")
            return self._fallback_draft(company, program)

    def _fallback_draft(self, company: Dict, program: Dict) -> str:
        return f"""## Antragsvorlage: {program.get('title', 'Förderprogramm')}

**1. Unternehmensvorstellung**
[Ihr Unternehmen] ist ein [Branche]-Unternehmen mit Sitz in [Ort], das seit [Gründungsjahr] tätig ist.
Wir beschäftigen [Mitarbeiterzahl] Mitarbeiter und erzielen einen Jahresumsatz von [Umsatz €].
Unsere Kernkompetenzen liegen in: {company.get('experience_keywords', '[Kompetenzen]')}.

**2. Projektbeschreibung**
Im Rahmen des Förderprogramms "{program.get('title', '')}" beantragen wir Mittel für [Projektbeschreibung].
Das Vorhaben umfasst [konkrete Maßnahmen] und soll innerhalb von [Zeitraum] umgesetzt werden.
[Weitere Details zum Projekt].

**3. Förderbedarf und Begründung**
Der Gesamtumfang des Vorhabens beläuft sich auf [Gesamtkosten €], wovon wir
[Eigenanteil €] aus Eigenmitteln finanzieren. Die beantragte Förderung beträgt [Förderbetrag €].
Die Maßnahme ist notwendig, weil [Begründung].

**4. Erwartete Ergebnisse**
Durch die Umsetzung des Projekts erwarten wir [konkrete Ergebnisse].
Die Fördermaßnahme trägt direkt zur [wirtschaftlichen Entwicklung / Digitalisierung / etc.] bei.
Mittelfristig planen wir [Folgemaßnahmen / Wachstumsziel].

---
⚠️ *Diese Vorlage muss vor der Einreichung individuell angepasst werden.
Alle Angaben in [eckigen Klammern] sind durch reale Daten zu ersetzen.
Wir empfehlen die Prüfung durch einen Steuerberater oder Förderberater.*"""
