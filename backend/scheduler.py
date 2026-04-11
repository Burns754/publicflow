"""
PublicFlow Scheduler — täglich automatisch:
1. Scraping (neue Ausschreibungen holen)
2. Matching (gegen alle aktiven Unternehmen)
3. Email-Versand (Treffer an Kunden)
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = None


def run_daily_job(engine):
    """
    Haupt-Job: wird täglich um 07:00 Uhr ausgeführt.
    Scrapt, matched und verschickt Emails.
    """
    from sqlalchemy.orm import sessionmaker
    from models import Company, Tender, Match, User, Subscription
    from scraper import ScraperOrchestrator
    from matcher import MatchingService
    from email_service import send_match_notification

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    logger.info(f"⏰ Tages-Job gestartet: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

    try:
        # ── 1. Scraping ──────────────────────────────────────────────
        logger.info("🔄 Scraping...")
        scraper = ScraperOrchestrator()
        tenders_data = scraper.scrape_all()

        new_tenders = 0
        for t in tenders_data:
            if not db.query(Tender).filter(Tender.id == t["id"]).first():
                deadline = None
                if t.get("deadline"):
                    try:
                        deadline = datetime.fromisoformat(t["deadline"])
                    except (ValueError, TypeError):
                        pass
                db.add(Tender(
                    id=t["id"],
                    title=t["title"],
                    description=t.get("description"),
                    source=t["source"],
                    source_url=t["source_url"],
                    deadline=deadline,
                    buyer_name=t.get("buyer_name"),
                    buyer_category=t.get("buyer_category"),
                    budget_min=t.get("budget_min"),
                    budget_max=t.get("budget_max"),
                    cpv_codes=t.get("cpv_codes"),
                    scraped_at=datetime.utcnow()
                ))
                new_tenders += 1
        db.commit()
        logger.info(f"✅ {new_tenders} neue Ausschreibungen gespeichert")

        # ── 2. Alle aktiven zahlenden Kunden holen ───────────────────
        active_subs = db.query(Subscription).filter(
            Subscription.status == "active"
        ).all()
        logger.info(f"👥 {len(active_subs)} aktive Abos gefunden")

        if not active_subs:
            logger.info("Keine aktiven Abos — Job beendet")
            return

        # Alle Ausschreibungen (nur neue seit gestern für Effizienz)
        all_tenders = db.query(Tender).all()
        tenders_list = [
            {
                "id": t.id, "title": t.title,
                "description": t.description, "source": t.source,
                "source_url": t.source_url,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "buyer_name": t.buyer_name, "budget_min": t.budget_min,
                "budget_max": t.budget_max, "cpv_codes": t.cpv_codes,
            }
            for t in all_tenders
        ]

        # ── 3. Matching + Email pro Kunde ────────────────────────────
        service = MatchingService()
        emails_sent = 0

        for sub in active_subs:
            try:
                user = db.query(User).filter(User.id == sub.user_id).first()
                company = db.query(Company).filter(
                    Company.user_id == sub.user_id
                ).first()

                if not user or not company:
                    continue

                # Limit je nach Plan
                limit = 10 if sub.plan == "starter" else 999

                company_dict = {
                    "id": company.id, "name": company.name,
                    "email": company.email, "industry": company.industry,
                    "experience_keywords": company.experience_keywords,
                    "cpv_focus": company.cpv_focus,
                    "min_budget": company.min_budget,
                    "max_budget": company.max_budget, "regions": company.regions,
                }

                matches = service.match_all(
                    [company_dict], tenders_list, min_score=50.0
                )[:limit]

                if not matches:
                    logger.info(f"  {company.name}: keine neuen Treffer")
                    continue

                # Nur ungemeldete Matches nehmen
                new_matches = []
                for m in matches:
                    exists = db.query(Match).filter(
                        Match.company_id == company.id,
                        Match.tender_id == m["tender_id"],
                        Match.notified == True
                    ).first()
                    if not exists:
                        new_matches.append(m)

                        # Match in DB speichern
                        db_match = db.query(Match).filter(
                            Match.company_id == company.id,
                            Match.tender_id == m["tender_id"]
                        ).first()
                        if not db_match:
                            db.add(Match(
                                company_id=company.id,
                                tender_id=m["tender_id"],
                                match_score=m["match_score"],
                                reasoning=m["reasoning"],
                                matched_at=datetime.utcnow(),
                                notified=False
                            ))

                if not new_matches:
                    logger.info(f"  {company.name}: alle Treffer bereits gemeldet")
                    continue

                # Anreichern mit Tender-Details
                enriched = []
                for m in new_matches:
                    t = db.query(Tender).filter(Tender.id == m["tender_id"]).first()
                    enriched.append({
                        **m,
                        "tender_title": t.title if t else "",
                        "tender_source": t.source if t else "",
                        "tender_url": t.source_url if t else "",
                        "tender_deadline": t.deadline.isoformat() if t and t.deadline else None,
                    })

                # Email senden
                sent = send_match_notification(
                    to_email=user.email,
                    company_name=company.name,
                    matches=enriched
                )

                if sent:
                    # Matches als "notified" markieren
                    for m in new_matches:
                        db.query(Match).filter(
                            Match.company_id == company.id,
                            Match.tender_id == m["tender_id"]
                        ).update({
                            "notified": True,
                            "notified_at": datetime.utcnow()
                        })
                    emails_sent += 1
                    logger.info(
                        f"  ✅ {company.name}: {len(new_matches)} Treffer per Email"
                    )

            except Exception as e:
                logger.error(f"  ❌ Fehler bei {sub.user_id}: {e}")
                continue

        db.commit()
        logger.info(
            f"🎉 Tages-Job fertig: {new_tenders} neue Ausschreibungen, "
            f"{emails_sent} Emails versendet"
        )

    except Exception as e:
        logger.error(f"❌ Tages-Job Fehler: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler(engine):
    """Startet den Hintergrund-Scheduler."""
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="Europe/Berlin")

    # Täglich um 07:00 Uhr
    _scheduler.add_job(
        func=lambda: run_daily_job(engine),
        trigger=CronTrigger(hour=7, minute=0),
        id="daily_match_job",
        name="Tägliches Scraping + Matching + Email",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 Stunde Toleranz
    )

    _scheduler.start()
    logger.info("⏰ Scheduler gestartet — Job läuft täglich um 07:00 Uhr")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("⏰ Scheduler gestoppt")
