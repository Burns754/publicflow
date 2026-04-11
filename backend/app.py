"""
PublicFlow Backend v0.3
- Registrierung + Login (JWT)
- Profil-Fragebogen
- Stripe Checkout (Abo mit Paywall)
- Stripe Webhooks
- Manuelle Suche (Check24-Funktion)
- Täglicher Scheduler
"""

from fastapi import FastAPI, HTTPException, Request, Depends, status, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, text, or_
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import asyncio
import logging
import os
import threading
from typing import Optional, List

from models import Base, User, Company, Subscription, Tender, Match, SearchQuery
from auth import (hash_password, verify_password, create_access_token,
                  get_current_user_id, generate_id)
from scraper import ScraperOrchestrator
from matcher import MatchingService
from email_service import send_welcome_email, send_payment_confirmation
from stripe_service import (create_checkout_session, handle_webhook,
                             cancel_subscription, PLAN_INFO)
from scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── DB ────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./publicflow.db")
# Railway liefert postgres:// URLs - SQLAlchemy braucht postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")

# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="PublicFlow API",
    description="KI-gestütztes Ausschreibungs-Monitoring",
    version="0.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend statische Dateien — Pfade für lokal & Docker/Railway
_FRONTEND_PATHS = ["../frontend", "/app/frontend", "frontend"]
for _fp in _FRONTEND_PATHS:
    if os.path.exists(_fp):
        app.mount("/app", StaticFiles(directory=_fp, html=True), name="frontend")
        logger.info(f"📁 Frontend gemountet: {_fp}")
        break


# ── Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ProfileRequest(BaseModel):
    company_name: str
    industry: str
    experience_keywords: str       # "Cloud,DevOps,Python"
    regions: str = "Deutschland,EU"
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    cpv_focus: Optional[str] = None
    company_size: Optional[str] = None
    description: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    source: Optional[str] = None   # "bund.de" | "ted.europa.eu"
    limit: int = 20

class CheckoutRequest(BaseModel):
    plan: str      # starter | professional
    interval: str  # monthly | yearly


# ── Helpers ───────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_active_sub(user_id: str, db) -> Subscription:
    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active"
    ).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Aktives Abo erforderlich. Bitte zuerst abonnieren."
        )
    return sub


# ── System ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Redirect zur Landing Page."""
    return RedirectResponse(url="/app/landing.html", status_code=302)

@app.get("/api")
async def api_root():
    return {"status": "✅ PublicFlow API läuft", "version": "0.3.0", "docs": "/docs"}

@app.get("/health")
async def health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        return {"status": "error", "database": "error"}
    finally:
        db.close()

@app.get("/plans")
async def get_plans():
    """Gibt alle verfügbaren Abo-Pläne zurück (öffentlich)."""
    return {"plans": PLAN_INFO}


# ── Auth ──────────────────────────────────────────────────────────────

@app.post("/auth/register")
async def register(req: RegisterRequest):
    """Neuen Nutzer registrieren."""
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == req.email.lower()).first():
            raise HTTPException(status_code=409, detail="Email bereits registriert")

        loop = asyncio.get_running_loop()
        pw_hash = await loop.run_in_executor(None, hash_password, req.password)
        user = User(
            id=generate_id(),
            email=req.email.lower(),
            hashed_password=pw_hash,
            full_name=req.full_name,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Email im Hintergrund — blockiert den Event-Loop NICHT
        threading.Thread(
            target=send_welcome_email,
            args=(user.email, user.full_name),
            daemon=True
        ).start()
        token = create_access_token(user.id)

        logger.info(f"👤 Neuer Nutzer: {user.email}")
        return {"token": token, "user_id": user.id, "email": user.email,
                "full_name": user.full_name, "has_profile": False, "has_subscription": False}
    finally:
        db.close()


@app.post("/auth/login")
async def login(req: LoginRequest):
    """Login — gibt JWT Token zurück."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == req.email.lower()).first()
        loop = asyncio.get_running_loop()
        pw_ok = user and await loop.run_in_executor(
            None, verify_password, req.password, user.hashed_password
        )
        if not pw_ok:
            raise HTTPException(status_code=401, detail="Email oder Passwort falsch")

        company = db.query(Company).filter(Company.user_id == user.id).first()
        sub = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        ).first()

        token = create_access_token(user.id)
        return {
            "token": token,
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "has_profile": company is not None,
            "has_subscription": sub is not None,
            "plan": sub.plan if sub else None
        }
    finally:
        db.close()


@app.get("/auth/me")
async def me(user_id: str = Depends(get_current_user_id)):
    """Aktuellen Nutzer abrufen."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Nutzer nicht gefunden")

        company = db.query(Company).filter(Company.user_id == user_id).first()
        sub = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()

        return {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "has_profile": company is not None,
            "has_subscription": sub is not None,
            "plan": sub.plan if sub else None,
            "company": {
                "name": company.name,
                "industry": company.industry,
                "regions": company.regions
            } if company else None
        }
    finally:
        db.close()


# ── Profil-Fragebogen ─────────────────────────────────────────────────

@app.post("/profile")
async def create_profile(
    req: ProfileRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Unternehmensprofil aus Fragebogen speichern.
    Kein Abo erforderlich — Profil wird im Onboarding VOR dem Abo angelegt.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        existing = db.query(Company).filter(Company.user_id == user_id).first()

        if existing:
            # Update
            existing.name = req.company_name
            existing.industry = req.industry
            existing.experience_keywords = req.experience_keywords
            existing.regions = req.regions
            existing.min_budget = req.min_budget
            existing.max_budget = req.max_budget
            existing.cpv_focus = req.cpv_focus
            existing.company_size = req.company_size
            existing.description = req.description
            db.commit()
            logger.info(f"📝 Profil aktualisiert: {req.company_name}")
            return {"status": "updated", "company_id": existing.id}
        else:
            company = Company(
                id=generate_id(),
                user_id=user_id,
                name=req.company_name,
                email=user.email if user else "",
                industry=req.industry,
                experience_keywords=req.experience_keywords,
                regions=req.regions,
                min_budget=req.min_budget,
                max_budget=req.max_budget,
                cpv_focus=req.cpv_focus,
                company_size=req.company_size,
                description=req.description,
                created_at=datetime.utcnow()
            )
            db.add(company)
            db.commit()
            logger.info(f"📝 Profil erstellt: {req.company_name}")
            return {"status": "created", "company_id": company.id}
    finally:
        db.close()


@app.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user_id)):
    """Eigenes Profil abrufen."""
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.user_id == user_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Noch kein Profil erstellt")
        return {
            "company_id": company.id,
            "name": company.name,
            "industry": company.industry,
            "experience_keywords": company.experience_keywords,
            "regions": company.regions,
            "min_budget": company.min_budget,
            "max_budget": company.max_budget,
            "cpv_focus": company.cpv_focus,
            "company_size": company.company_size,
            "description": company.description,
        }
    finally:
        db.close()


# ── Stripe ────────────────────────────────────────────────────────────

@app.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Stripe Checkout Session erstellen."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Nutzer nicht gefunden")

        if req.plan not in ("starter", "professional"):
            raise HTTPException(status_code=400, detail="Ungültiger Plan")
        if req.interval not in ("monthly", "yearly"):
            raise HTTPException(status_code=400, detail="Ungültiges Intervall")

        checkout_url = create_checkout_session(
            user_id=user_id,
            user_email=user.email,
            plan=req.plan,
            interval=req.interval,
            success_url=f"{FRONTEND_URL}/app/index.html?checkout=success",
            cancel_url=f"{FRONTEND_URL}/app/index.html?checkout=cancel",
        )

        if not checkout_url:
            raise HTTPException(status_code=500, detail="Checkout konnte nicht erstellt werden")

        return {"checkout_url": checkout_url}
    finally:
        db.close()


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Stripe Webhook — aktiviert Abos nach Zahlung."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    event = handle_webhook(payload, sig)

    if not event:
        # Mock-Modus (kein Webhook-Secret) → manuell aktivieren
        return {"status": "mock_mode"}

    db = SessionLocal()
    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session["metadata"].get("user_id")
            plan = session["metadata"].get("plan", "starter")
            interval = session["metadata"].get("interval", "monthly")
            stripe_sub_id = session.get("subscription", "")
            customer_id = session.get("customer", "")

            if user_id:
                existing = db.query(Subscription).filter(
                    Subscription.user_id == user_id
                ).first()
                if existing:
                    existing.status = "active"
                    existing.plan = plan
                    existing.interval = interval
                    existing.stripe_customer_id = customer_id
                    if stripe_sub_id:
                        existing.id = stripe_sub_id
                else:
                    db.add(Subscription(
                        id=stripe_sub_id or generate_id(),
                        user_id=user_id,
                        stripe_customer_id=customer_id,
                        plan=plan,
                        interval=interval,
                        status="active",
                        created_at=datetime.utcnow()
                    ))
                db.commit()

                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    threading.Thread(
                        target=send_payment_confirmation,
                        args=(user.email, user.full_name, plan, interval),
                        daemon=True
                    ).start()
                logger.info(f"✅ Abo aktiviert: {user_id} → {plan}/{interval}")

        elif event["type"] == "customer.subscription.deleted":
            sub_id = event["data"]["object"]["id"]
            sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
            if sub:
                sub.status = "canceled"
                sub.canceled_at = datetime.utcnow()
                db.commit()
                logger.info(f"❌ Abo gekündigt: {sub_id}")

        elif event["type"] == "customer.subscription.updated":
            stripe_sub = event["data"]["object"]
            sub = db.query(Subscription).filter(
                Subscription.id == stripe_sub["id"]
            ).first()
            if sub:
                sub.status = stripe_sub["status"]
                db.commit()

    finally:
        db.close()

    return {"status": "ok"}


@app.post("/subscription/activate-mock")
async def activate_mock(
    plan: str = "professional",
    interval: str = "monthly",
    user_id: str = Depends(get_current_user_id)
):
    """
    Nur für lokales Testen ohne echtes Stripe:
    aktiviert ein Abo direkt.
    """
    db = SessionLocal()
    try:
        existing = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        if existing:
            existing.status = "active"
            existing.plan = plan
            existing.interval = interval
        else:
            db.add(Subscription(
                id=generate_id(),
                user_id=user_id,
                plan=plan,
                interval=interval,
                status="active",
                created_at=datetime.utcnow()
            ))
        db.commit()
        return {"status": "activated", "plan": plan, "interval": interval}
    finally:
        db.close()


@app.delete("/subscription")
async def cancel_sub(user_id: str = Depends(get_current_user_id)):
    """Abo kündigen (zum Periodenende)."""
    db = SessionLocal()
    try:
        sub = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Kein aktives Abo")

        cancel_subscription(sub.id)
        sub.status = "cancel_pending"
        db.commit()
        return {"status": "Abo wird zum Periodenende gekündigt"}
    finally:
        db.close()


# ── Ausschreibungen & Matching ────────────────────────────────────────

def _do_scrape_background():
    """Scraping läuft in einem eigenen Thread — blockiert den Server nicht."""
    db = SessionLocal()
    try:
        logger.info("🔄 Hintergrund-Scraping gestartet...")
        scraper = ScraperOrchestrator()
        tenders_data = scraper.scrape_all()

        new_count = 0
        for t in tenders_data:
            if not db.query(Tender).filter(Tender.id == t["id"]).first():
                deadline = None
                if t.get("deadline"):
                    try:
                        deadline = datetime.fromisoformat(t["deadline"])
                    except (ValueError, TypeError):
                        pass
                db.add(Tender(
                    id=t["id"], title=t["title"],
                    description=t.get("description"), source=t["source"],
                    source_url=t["source_url"], deadline=deadline,
                    buyer_name=t.get("buyer_name"),
                    buyer_category=t.get("buyer_category"),
                    budget_min=t.get("budget_min"),
                    budget_max=t.get("budget_max"),
                    cpv_codes=t.get("cpv_codes"),
                    scraped_at=datetime.utcnow()
                ))
                new_count += 1
        db.commit()
        logger.info(f"✅ Hintergrund-Scraping fertig: {len(tenders_data)} gesamt, {new_count} neu")
    except Exception as e:
        logger.error(f"❌ Hintergrund-Scraping Fehler: {e}")
    finally:
        db.close()


@app.post("/scrape")
async def trigger_scrape(user_id: str = Depends(get_current_user_id)):
    """
    Manuell Scraping triggern (nur eingeloggte Nutzer).
    Gibt sofort zurück — Scraping läuft im Hintergrund.
    Status via GET /scrape/status oder GET /tenders prüfen.
    """
    t = threading.Thread(target=_do_scrape_background, daemon=True)
    t.start()
    return {"status": "started", "message": "Scraping läuft im Hintergrund. Ergebnisse in ~30s unter /tenders abrufbar."}


@app.get("/tenders")
async def list_tenders(
    limit: int = 50,
    user_id: str = Depends(get_current_user_id)
):
    """Alle gespeicherten Ausschreibungen — zum Prüfen nach dem Scraping."""
    db = SessionLocal()
    try:
        tenders = db.query(Tender).order_by(Tender.scraped_at.desc()).limit(limit).all()
        return {
            "total": len(tenders),
            "tenders": [
                {
                    "id": t.id,
                    "title": t.title,
                    "source": t.source,
                    "source_url": t.source_url,
                    "buyer_name": t.buyer_name,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "scraped_at": t.scraped_at.isoformat() if t.scraped_at else None,
                }
                for t in tenders
            ]
        }
    finally:
        db.close()


def _send_instant_alert(email: str, company_name: str, matches: list,
                        company_id: str, engine) -> None:
    """
    Sofort-Benachrichtigung nach manuellem Matching.
    Läuft in eigenem Thread — markiert Matches als 'notified'.
    """
    from email_service import send_match_notification
    try:
        sent = send_match_notification(
            to_email=email,
            company_name=company_name,
            matches=matches
        )
        if sent:
            # Matches in DB als notified markieren
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=engine)
            db2 = Session()
            try:
                for m in matches:
                    db2.query(Match).filter(
                        Match.company_id == company_id,
                        Match.tender_id == m["tender_id"]
                    ).update({"notified": True, "notified_at": datetime.utcnow()})
                db2.commit()
            finally:
                db2.close()
            logger.info(f"✅ Sofort-Alert gesendet an {email} ({len(matches)} Matches)")
    except Exception as e:
        logger.error(f"❌ Sofort-Alert Fehler: {e}")


@app.post("/match")
async def trigger_match(
    min_score: float = 50.0,
    user_id: str = Depends(get_current_user_id)
):
    """Matching für das eigene Unternehmensprofil."""
    db = SessionLocal()
    try:
        require_active_sub(user_id, db)

        company = db.query(Company).filter(Company.user_id == user_id).first()
        if not company:
            raise HTTPException(status_code=404,
                                detail="Erst Profil erstellen (POST /profile)")

        tenders = db.query(Tender).all()
        if not tenders:
            return {"status": "no_tenders",
                    "message": "Erst /scrape aufrufen", "matches": []}

        company_dict = {
            "id": company.id, "name": company.name, "email": company.email,
            "industry": company.industry,
            "experience_keywords": company.experience_keywords,
            "cpv_focus": company.cpv_focus, "min_budget": company.min_budget,
            "max_budget": company.max_budget, "regions": company.regions,
        }
        tenders_list = [
            {
                "id": t.id, "title": t.title, "description": t.description,
                "source": t.source, "source_url": t.source_url,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "buyer_name": t.buyer_name, "budget_min": t.budget_min,
                "budget_max": t.budget_max, "cpv_codes": t.cpv_codes,
            }
            for t in tenders
        ]

        service = MatchingService()
        matches = service.match_all([company_dict], tenders_list, min_score=min_score)

        # Speichern + anreichern
        result = []
        new_matches_for_alert = []

        for m in matches:
            existing = db.query(Match).filter(
                Match.company_id == company.id,
                Match.tender_id == m["tender_id"]
            ).first()
            is_new = existing is None
            if is_new:
                db.add(Match(
                    company_id=company.id, tender_id=m["tender_id"],
                    match_score=m["match_score"], reasoning=m["reasoning"],
                    matched_at=datetime.utcnow(), notified=False
                ))
            t = db.query(Tender).filter(Tender.id == m["tender_id"]).first()
            enriched = {
                **m,
                "tender_title": t.title if t else "",
                "tender_source": t.source if t else "",
                "tender_url": t.source_url if t else "",
                "tender_deadline": t.deadline.isoformat() if t and t.deadline else None,
            }
            result.append(enriched)
            if is_new:
                new_matches_for_alert.append(enriched)

        db.commit()

        # Sofort-Alert: E-Mail für neue Matches im Hintergrund
        if new_matches_for_alert:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                threading.Thread(
                    target=_send_instant_alert,
                    args=(user.email, company.name, new_matches_for_alert,
                          company.id, db.bind),
                    daemon=True
                ).start()
                logger.info(f"📧 Sofort-Alert für {len(new_matches_for_alert)} neue Matches gestartet")

        return {"matches_found": len(result), "new_matches": len(new_matches_for_alert),
                "matches": result}
    finally:
        db.close()


@app.get("/matches")
async def get_my_matches(user_id: str = Depends(get_current_user_id)):
    """Alle gespeicherten Matches des eigenen Profils."""
    db = SessionLocal()
    try:
        require_active_sub(user_id, db)
        company = db.query(Company).filter(Company.user_id == user_id).first()
        if not company:
            return {"total": 0, "matches": []}

        matches = db.query(Match).filter(
            Match.company_id == company.id
        ).order_by(Match.match_score.desc()).all()

        result = []
        for m in matches:
            t = db.query(Tender).filter(Tender.id == m.tender_id).first()
            result.append({
                "match_score": m.match_score,
                "reasoning": m.reasoning,
                "matched_at": m.matched_at.isoformat(),
                "notified": m.notified,
                "tender_id": m.tender_id,
                "tender_title": t.title if t else "",
                "tender_source": t.source if t else "",
                "tender_url": t.source_url if t else "",
                "tender_deadline": t.deadline.isoformat() if t and t.deadline else None,
            })
        return {"total": len(result), "matches": result}
    finally:
        db.close()


# ── Manuelle Suche (Check24-Funktion) ─────────────────────────────────

@app.post("/search")
async def search_tenders(
    req: SearchRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Manuelle Freitextsuche in allen Ausschreibungen.
    Erfordert aktives Abo (Professional empfohlen).
    """
    db = SessionLocal()
    try:
        require_active_sub(user_id, db)

        query = db.query(Tender)

        # Freitext-Filter
        if req.query:
            search_term = f"%{req.query.lower()}%"
            query = query.filter(
                or_(
                    Tender.title.ilike(search_term),
                    Tender.description.ilike(search_term),
                    Tender.buyer_name.ilike(search_term),
                )
            )

        # Budget-Filter
        if req.min_budget is not None:
            query = query.filter(
                or_(Tender.budget_max >= req.min_budget,
                    Tender.budget_max.is_(None))
            )
        if req.max_budget is not None:
            query = query.filter(
                or_(Tender.budget_min <= req.max_budget,
                    Tender.budget_min.is_(None))
            )

        # Quellen-Filter
        if req.source:
            query = query.filter(Tender.source == req.source)

        tenders = query.order_by(Tender.scraped_at.desc()).limit(req.limit).all()

        # Suchanfrage loggen
        db.add(SearchQuery(
            user_id=user_id,
            query=req.query,
            created_at=datetime.utcnow(),
            result_count=len(tenders)
        ))
        db.commit()

        return {
            "query": req.query,
            "total": len(tenders),
            "tenders": [
                {
                    "id": t.id, "title": t.title,
                    "source": t.source, "source_url": t.source_url,
                    "buyer_name": t.buyer_name,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "budget_min": t.budget_min, "budget_max": t.budget_max,
                    "cpv_codes": t.cpv_codes,
                    "description": (t.description or "")[:300],
                }
                for t in tenders
            ]
        }
    finally:
        db.close()


# ── Startup / Shutdown ────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("🚀 PublicFlow v0.3 startet...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Datenbank bereit")

    start_scheduler(engine)

    logger.info(f"🤖 Claude AI: {'aktiv' if os.getenv('ANTHROPIC_API_KEY') else 'kein Key — Regel-Matching'}")
    logger.info(f"💳 Stripe: {'aktiv' if os.getenv('STRIPE_SECRET_KEY') else 'kein Key — Mock-Modus'}")
    logger.info(f"📧 Resend: {'aktiv' if os.getenv('RESEND_API_KEY') else 'kein Key — Mock-Modus'}")


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()
    logger.info("🛑 PublicFlow gestoppt")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
