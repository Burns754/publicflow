"""
PublicFlow Stripe Service — Checkout, Webhooks, Abo-Verwaltung
"""
import os
import logging
import stripe
from typing import Optional

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Price IDs aus .env
PRICES = {
    "starter_monthly":      os.getenv("STRIPE_PRICE_STARTER_MONTHLY", ""),
    "starter_yearly":       os.getenv("STRIPE_PRICE_STARTER_YEARLY", ""),
    "professional_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", ""),
    "professional_yearly":  os.getenv("STRIPE_PRICE_PRO_YEARLY", ""),
}

# Preise für die Anzeige im Frontend
PLAN_INFO = {
    "starter": {
        "name": "Starter",
        "monthly_price": 249,
        "yearly_price": 224,
        "features": [
            "1 Unternehmensprofil",
            "Tägl. E-Mail-Digest (7:00 Uhr)",
            "EU + BRD Monitoring",
            "Bis zu 10 Treffer pro Tag",
            "Frist-Erinnerungen (7d + 48h)",
            "E-Mail-Support",
        ]
    },
    "professional": {
        "name": "Professional",
        "monthly_price": 499,
        "yearly_price": 449,
        "features": [
            "3 Unternehmensprofile",
            "EU + BRD + alle 16 Bundesländer",
            "Unbegrenzte Treffer täglich",
            "KI-Relevanzbewertung mit Score",
            "Wöchentlicher Marktreport",
            "Prioritäts-Support (24h)",
        ]
    }
}


def create_checkout_session(
    user_id: str,
    user_email: str,
    plan: str,
    interval: str,
    success_url: str,
    cancel_url: str,
) -> Optional[str]:
    """
    Erstellt eine Stripe Checkout Session.
    Gibt die Checkout-URL zurück.
    """
    price_key = f"{plan}_{interval}"
    price_id = PRICES.get(price_key, "")

    if not stripe.api_key:
        logger.warning("[STRIPE MOCK] Kein API-Key — gebe Fake-URL zurück")
        return f"{success_url}?session_id=mock_session&plan={plan}&interval={interval}"

    if not price_id:
        logger.error(f"Keine Price ID für: {price_key}")
        return None

    try:
        # Stripe Customer anlegen oder wiederverwenden
        customers = stripe.Customer.list(email=user_email, limit=1)
        if customers.data:
            customer_id = customers.data[0].id
        else:
            customer = stripe.Customer.create(
                email=user_email,
                metadata={"user_id": user_id}
            )
            customer_id = customer.id

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"user_id": user_id, "plan": plan, "interval": interval},
            subscription_data={
                "metadata": {"user_id": user_id, "plan": plan, "interval": interval}
            },
            allow_promotion_codes=True,
            locale="de",
        )
        logger.info(f"✅ Checkout Session erstellt für {user_email} ({plan}/{interval})")
        return session.url

    except stripe.error.StripeError as e:
        logger.error(f"Stripe Fehler: {e}")
        return None


def handle_webhook(payload: bytes, sig_header: str) -> Optional[dict]:
    """
    Verarbeitet eingehende Stripe Webhooks.
    Gibt das Event zurück wenn valide, sonst None.
    """
    if not WEBHOOK_SECRET:
        logger.warning("[STRIPE MOCK] Kein Webhook-Secret")
        return None
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
        return event
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"Webhook ungültig: {e}")
        return None


def cancel_subscription(stripe_subscription_id: str) -> bool:
    """Kündigt ein Abo zum Periodenende."""
    if not stripe.api_key:
        return True
    try:
        stripe.Subscription.modify(
            stripe_subscription_id,
            cancel_at_period_end=True
        )
        logger.info(f"✅ Abo {stripe_subscription_id} zum Periodenende gekündigt")
        return True
    except stripe.error.StripeError as e:
        logger.error(f"Kündigung fehlgeschlagen: {e}")
        return False


def get_subscription_status(stripe_subscription_id: str) -> Optional[str]:
    """Gibt den aktuellen Status eines Abos zurück."""
    if not stripe.api_key:
        return "active"
    try:
        sub = stripe.Subscription.retrieve(stripe_subscription_id)
        return sub.status
    except Exception:
        return None
