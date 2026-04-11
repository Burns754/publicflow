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
