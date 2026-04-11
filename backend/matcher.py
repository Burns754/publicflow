"""
PublicFlow Matcher — KI-Matching via Claude API (Anthropic)
Fallback: regel-basiertes Matching ohne API-Key
"""

import anthropic
import logging
import os
import json
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


class TenderMatcher:

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
        if self.client:
            logger.info("✅ Matcher: Claude API aktiv (claude-haiku-4-5-20251001)")
        else:
            logger.warning("⚠️  Matcher: Kein API-Key — nutze Regel-Matching")

    def calculate_match_score(self, company: Dict, tender: Dict) -> Tuple[float, str]:
        """
        Gibt (score: 0-100, reasoning: str) zurück.
        Nutzt Claude wenn API-Key vorhanden, sonst Regel-Logik.
        """
        if self.client:
            return self._claude_match(company, tender)
        return self._rule_based_match(company, tender)

    # ── Claude-basiertes Matching ──────────────────────────────────────

    def _claude_match(self, company: Dict, tender: Dict) -> Tuple[float, str]:
        prompt = f"""Du bist Experte für öffentliche Vergabe und bewertest ob eine Ausschreibung für ein Unternehmen relevant ist.

UNTERNEHMEN:
- Name: {company.get('name', 'N/A')}
- Branche: {company.get('industry', 'N/A')}
- Kompetenzen: {company.get('experience_keywords', 'N/A')}
- CPV-Fokus: {company.get('cpv_focus', 'N/A')}
- Budget-Interesse: €{company.get('min_budget', 0):,} – €{company.get('max_budget', 0):,}
- Regionen: {company.get('regions', 'N/A')}

AUSSCHREIBUNG:
- Titel: {tender.get('title', 'N/A')}
- Beschreibung: {tender.get('description', 'N/A')[:500]}
- Auftraggeber: {tender.get('buyer_name', 'N/A')}
- Quelle: {tender.get('source', 'N/A')}
- Frist: {tender.get('deadline', 'N/A')}
- Budget: €{tender.get('budget_min') or 0:,} – €{tender.get('budget_max') or 0:,}
- CPV-Codes: {tender.get('cpv_codes', 'N/A')}

Antworte NUR mit einem JSON-Objekt, keine Erklärung davor oder danach:
{{"score": <0-100>, "reasoning": "<max 200 Zeichen Begründung auf Deutsch>"}}

Score-Skala:
0-39: nicht relevant
40-59: möglicherweise relevant
60-79: relevant
80-100: sehr gut passend"""

        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.strip()

            # JSON sauber extrahieren (Claude gibt manchmal Backticks zurück)
            if "```" in raw:
                raw = raw.split("```")[1].replace("json", "").strip()

            result = json.loads(raw)
            score = float(result.get("score", 0))
            reasoning = result.get("reasoning", "Keine Begründung")
            logger.info(f"🤖 Claude Match: {score:.0f}/100 — {reasoning[:60]}")
            return score, reasoning

        except json.JSONDecodeError as e:
            logger.warning(f"Claude JSON-Parse-Fehler: {e} — Fallback zu Regel-Matching")
            return self._rule_based_match(company, tender)
        except anthropic.APIError as e:
            logger.error(f"Claude API-Fehler: {e} — Fallback zu Regel-Matching")
            return self._rule_based_match(company, tender)
        except Exception as e:
            logger.error(f"Matching-Fehler: {e} — Fallback zu Regel-Matching")
            return self._rule_based_match(company, tender)

    # ── Regel-basiertes Matching (kein API-Key nötig) ──────────────────

    def _rule_based_match(self, company: Dict, tender: Dict) -> Tuple[float, str]:
        score = 0.0
        reasons = []

        # 1. Keyword-Matching (40 Punkte)
        keywords = [
            kw.strip().lower()
            for kw in (company.get("experience_keywords") or "").split(",")
            if kw.strip()
        ]
        tender_text = (
            (tender.get("title") or "") + " " + (tender.get("description") or "")
        ).lower()

        if keywords:
            hits = sum(1 for kw in keywords if kw in tender_text)
            keyword_score = min(40, (hits / len(keywords)) * 40)
            score += keyword_score
            if hits > 0:
                reasons.append(f"✅ {hits}/{len(keywords)} Keywords gefunden")
            else:
                reasons.append("❌ Keine Keywords gefunden")

        # 2. Budget-Matching (30 Punkte)
        t_min = tender.get("budget_min") or 0
        t_max = tender.get("budget_max") or 10_000_000
        c_min = company.get("min_budget") or 0
        c_max = company.get("max_budget") or 10_000_000

        if t_max >= c_min and t_min <= c_max:
            score += 30
            reasons.append(f"💰 Budget passt (€{t_min:,.0f}–€{t_max:,.0f})")
        elif t_min == 0 and t_max == 10_000_000:
            score += 15  # Budget unbekannt → halbe Punkte
            reasons.append("💰 Budget unbekannt")
        else:
            reasons.append(f"⚠️ Budget außerhalb Range")

        # 3. Regions-Matching (20 Punkte)
        regions = set(r.strip() for r in (company.get("regions") or "").split(","))
        source = tender.get("source", "")
        if "EU" in regions and "ted" in source:
            score += 20
            reasons.append("📍 EU-Region passt (TED)")
        elif "Deutschland" in regions and "bund" in source:
            score += 20
            reasons.append("📍 Deutschland-Region passt (bund.de)")
        elif regions:
            score += 10
            reasons.append("📍 Region teilweise relevant")

        # 4. CPV-Matching (10 Punkte)
        c_cpv = set(c.strip() for c in (company.get("cpv_focus") or "").split(",") if c.strip())
        t_cpv = set(c.strip() for c in (tender.get("cpv_codes") or "").split(",") if c.strip())
        if c_cpv and t_cpv and (c_cpv & t_cpv):
            score += 10
            reasons.append(f"📋 CPV-Code Match: {c_cpv & t_cpv}")

        return min(100.0, score), "\n".join(reasons)


# ─────────────────────────────────────────────
# Matching Service
# ─────────────────────────────────────────────

class MatchingService:

    def __init__(self):
        self.matcher = TenderMatcher()

    def match_all(self, companies: List[Dict], tenders: List[Dict],
                  min_score: float = 40.0) -> List[Dict]:
        matches = []
        logger.info(f"🔄 Matching: {len(companies)} Unternehmen × {len(tenders)} Ausschreibungen")

        for company in companies:
            for tender in tenders:
                score, reasoning = self.matcher.calculate_match_score(company, tender)
                if score >= min_score:
                    matches.append({
                        "company_id": company["id"],
                        "tender_id": tender["id"],
                        "match_score": round(score, 1),
                        "reasoning": reasoning,
                    })
                    logger.info(
                        f"✅ {company.get('name','?')[:20]} ↔ "
                        f"{tender.get('title','?')[:40]} — Score: {score:.0f}"
                    )

        logger.info(f"📊 {len(matches)} relevante Matches gefunden (min_score={min_score})")
        return sorted(matches, key=lambda m: m["match_score"], reverse=True)
