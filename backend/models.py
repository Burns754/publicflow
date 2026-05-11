"""
PublicFlow Datenmodelle
"""
from sqlalchemy import Column, String, Float, DateTime, Integer, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Registrierter Nutzer mit Login"""
    __tablename__ = "users"

    id = Column(String, primary_key=True)           # uuid
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Beziehungen
    company = relationship("Company", back_populates="user", uselist=False)
    subscription = relationship("Subscription", back_populates="user", uselist=False)


class Company(Base):
    """Unternehmensprofil (aus Fragebogen)"""
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)
    industry = Column(String)
    experience_keywords = Column(String)   # kommasepariert
    cpv_focus = Column(String)             # CPV-Codes
    min_budget = Column(Float)
    max_budget = Column(Float)
    regions = Column(String, default="Deutschland,EU")
    company_size = Column(String)          # Kleinstunternehmen / KMU / Groß
    founded_year = Column(Integer)
    description = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="company")


class Subscription(Base):
    """Stripe-Abo eines Nutzers"""
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True)           # Stripe subscription ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    stripe_customer_id = Column(String)
    plan = Column(String)                            # starter / professional
    interval = Column(String)                        # monthly / yearly
    status = Column(String)                          # active / canceled / past_due
    current_period_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    canceled_at = Column(DateTime)

    user = relationship("User", back_populates="subscription")


class Tender(Base):
    """Öffentliche Ausschreibung"""
    __tablename__ = "tenders"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    source = Column(String)
    source_url = Column(String, unique=True)
    deadline = Column(DateTime)
    published_at = Column(DateTime, default=datetime.utcnow)
    buyer_name = Column(String)
    buyer_category = Column(String)
    budget_min = Column(Float)
    budget_max = Column(Float)
    cpv_codes = Column(String)
    raw_data = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)


class Match(Base):
    """KI-Matching Ergebnis"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    tender_id = Column(String, ForeignKey("tenders.id"), nullable=False)
    match_score = Column(Float)
    reasoning = Column(Text)
    matched_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(Boolean, default=False)
    notified_at = Column(DateTime)


class SearchQuery(Base):
    """Manuelle Suchanfrage eines Nutzers (Check24-Funktion)"""
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    query = Column(String)
    filters = Column(Text)    # JSON: budget, region, cpv, deadline
    created_at = Column(DateTime, default=datetime.utcnow)
    result_count = Column(Integer, default=0)


class FundingProgram(Base):
    """Öffentliches Förderprogramm (Bund, Länder, EU)"""
    __tablename__ = "funding_programs"

    id = Column(String, primary_key=True)           # uuid
    title = Column(String, nullable=False)
    provider = Column(String)                        # z.B. KfW, BAFA, EU-Kommission
    provider_level = Column(String)                  # bund / land / eu
    federal_state = Column(String)                   # Bayern, NRW ... (nur bei Länder-Programmen)
    description = Column(Text)
    funding_type = Column(String)                    # zuschuss / kredit / buergschaft / beratung
    max_amount = Column(Float)                       # maximale Fördersumme €
    funding_rate = Column(Float)                     # Förderquote 0.0-1.0 (z.B. 0.5 = 50%)
    industries = Column(String)                      # kommasepariert: IT,Handwerk,Produktion
    company_sizes = Column(String)                   # Kleinstunternehmen,KMU,Alle
    regions = Column(String)                         # Deutschland / Bayern / EU / ...
    topics = Column(String)                          # Digitalisierung,Energie,Gründung,Export
    eligibility_summary = Column(Text)               # Kurz-Erklärung wer antragsberechtigt ist
    application_url = Column(String)
    deadline = Column(DateTime)                      # None = laufend / kein Stichtag
    is_ongoing = Column(Boolean, default=True)       # Dauerhaftes Programm ohne Stichtag
    source_url = Column(String, unique=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)


class FundingMatch(Base):
    """KI-Matching Ergebnis: Unternehmen ↔ Förderprogramm"""
    __tablename__ = "funding_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    program_id = Column(String, ForeignKey("funding_programs.id"), nullable=False)
    match_score = Column(Float)                      # 0-100
    reasoning = Column(Text)                         # KI-Begründung
    matched_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(Boolean, default=False)
    notified_at = Column(DateTime)
    status = Column(String, default="neu")           # neu / gesehen / beworben / bewilligt / abgelehnt


class FundingDraft(Base):
    """KI-generierter Antrags-Entwurf"""
    __tablename__ = "funding_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    program_id = Column(String, ForeignKey("funding_programs.id"), nullable=False)
    draft_text = Column(Text)                        # KI-generierter Antragstext
    created_at = Column(DateTime, default=datetime.utcnow)
    user_notes = Column(Text)                        # Manuelle Ergänzungen des Nutzers
