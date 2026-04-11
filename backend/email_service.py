"""
PublicFlow Email Service — via Resend
"""
import os
import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "PublicFlow <noreply@publicflow.io>")
RESEND_URL = "https://api.resend.com/emails"


def _send(to: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY:
        logger.warning(f"[EMAIL MOCK] An: {to} | Betreff: {subject}")
        return True
    try:
        resp = requests.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                     "Content-Type": "application/json"},
            json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html},
            timeout=10
        )
        resp.raise_for_status()
        logger.info(f"✅ Email gesendet an {to}")
        return True
    except Exception as e:
        logger.error(f"❌ Email-Fehler an {to}: {e}")
        return False


def send_match_notification(
    to_email: str,
    company_name: str,
    matches: List[Dict]
) -> bool:
    """Sendet Ausschreibungs-Treffer an den Kunden."""
    count = len(matches)
    subject = f"🎯 {count} neue Ausschreibung{'en' if count != 1 else ''} für {company_name}"

    match_rows = ""
    for m in matches[:10]:  # max 10 pro Mail
        score = m.get("match_score", 0)
        score_color = "#16a34a" if score >= 70 else "#d97706" if score >= 50 else "#6b7280"
        deadline = m.get("tender_deadline", "")
        deadline_str = f"Frist: {deadline[:10]}" if deadline else ""

        match_rows += f"""
        <tr>
          <td style="padding:16px;border-bottom:1px solid #f0f0f0">
            <div style="font-weight:600;color:#111;margin-bottom:4px">
              {m.get('tender_title', 'Ausschreibung')}
            </div>
            <div style="font-size:13px;color:#666;margin-bottom:8px">
              {m.get('tender_source','')} &nbsp;·&nbsp; {deadline_str}
            </div>
            <div style="font-size:13px;color:#444;margin-bottom:10px">
              {m.get('reasoning','').replace(chr(10), ' · ')}
            </div>
            <a href="{m.get('tender_url','#')}"
               style="display:inline-block;background:#2563eb;color:#fff;
                      padding:6px 14px;border-radius:6px;font-size:13px;
                      text-decoration:none;font-weight:500">
              Ausschreibung ansehen →
            </a>
          </td>
          <td style="padding:16px;border-bottom:1px solid #f0f0f0;
                     text-align:center;vertical-align:top;white-space:nowrap">
            <span style="font-size:22px;font-weight:700;color:{score_color}">
              {score:.0f}%
            </span>
            <div style="font-size:11px;color:#999">Match</div>
          </td>
        </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f8f8f8;font-family:-apple-system,
                 BlinkMacSystemFont,'Segoe UI',sans-serif">
      <div style="max-width:620px;margin:32px auto;background:#fff;
                  border-radius:12px;overflow:hidden;
                  box-shadow:0 1px 4px rgba(0,0,0,.08)">

        <!-- Header -->
        <div style="background:#2563eb;padding:28px 32px">
          <div style="font-size:22px;font-weight:700;color:#fff">PublicFlow</div>
          <div style="font-size:14px;color:#bfdbfe;margin-top:4px">
            Ausschreibungs-Monitor
          </div>
        </div>

        <!-- Intro -->
        <div style="padding:28px 32px 0">
          <h2 style="margin:0 0 8px;font-size:18px;color:#111">
            Hallo {company_name},
          </h2>
          <p style="margin:0;color:#555;font-size:15px;line-height:1.6">
            wir haben heute <strong>{count} passende
            Ausschreibung{'en' if count != 1 else ''}</strong> für dein Profil gefunden:
          </p>
        </div>

        <!-- Matches -->
        <div style="padding:20px 32px">
          <table style="width:100%;border-collapse:collapse">
            {match_rows}
          </table>
        </div>

        <!-- Footer -->
        <div style="padding:20px 32px;border-top:1px solid #f0f0f0;
                    font-size:12px;color:#999">
          Du erhältst diese Mail weil du bei PublicFlow registriert bist.<br>
          <a href="#" style="color:#2563eb">Profil anpassen</a> &nbsp;·&nbsp;
          <a href="#" style="color:#2563eb">Abmelden</a>
        </div>
      </div>
    </body>
    </html>"""

    return _send(to_email, subject, html)


def send_welcome_email(to_email: str, full_name: str) -> bool:
    """Willkommens-Mail nach Registrierung."""
    subject = "Willkommen bei PublicFlow 🎯"
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f8f8f8;
                 font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
      <div style="max-width:580px;margin:32px auto;background:#fff;
                  border-radius:12px;overflow:hidden;
                  box-shadow:0 1px 4px rgba(0,0,0,.08)">
        <div style="background:#2563eb;padding:28px 32px">
          <div style="font-size:22px;font-weight:700;color:#fff">PublicFlow</div>
        </div>
        <div style="padding:32px">
          <h2 style="margin:0 0 16px;color:#111">Hallo {full_name}! 👋</h2>
          <p style="color:#555;line-height:1.7;margin:0 0 16px">
            Schön dass du dabei bist. PublicFlow scannt täglich öffentliche
            Ausschreibungen von TED EU, service.bund.de und weiteren deutschen
            Vergabeplattformen — und schickt dir nur die Treffer, die wirklich
            zu deinem Unternehmen passen.
          </p>
          <p style="color:#555;line-height:1.7;margin:0 0 24px">
            <strong>Nächster Schritt:</strong> Erstelle dein Unternehmensprofil
            damit wir wissen wonach wir suchen sollen.
          </p>
          <a href="#" style="display:inline-block;background:#2563eb;color:#fff;
                             padding:12px 24px;border-radius:8px;font-size:15px;
                             text-decoration:none;font-weight:600">
            Profil erstellen →
          </a>
        </div>
      </div>
    </body>
    </html>"""
    return _send(to_email, subject, html)


def send_payment_confirmation(to_email: str, full_name: str,
                               plan: str, interval: str) -> bool:
    """Zahlungsbestätigung nach erfolgreichem Abo."""
    plan_label = "Starter" if plan == "starter" else "Professional"
    interval_label = "monatlich" if interval == "monthly" else "jährlich"
    subject = f"✅ Abo aktiviert — PublicFlow {plan_label}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f8f8f8;
                 font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
      <div style="max-width:580px;margin:32px auto;background:#fff;
                  border-radius:12px;overflow:hidden;
                  box-shadow:0 1px 4px rgba(0,0,0,.08)">
        <div style="background:#16a34a;padding:28px 32px">
          <div style="font-size:22px;font-weight:700;color:#fff">PublicFlow</div>
        </div>
        <div style="padding:32px">
          <h2 style="margin:0 0 16px;color:#111">
            Zahlung bestätigt ✅
          </h2>
          <p style="color:#555;line-height:1.7;margin:0 0 16px">
            Hallo {full_name}, dein <strong>PublicFlow {plan_label}</strong>-Abo
            ({interval_label}) ist jetzt aktiv.
          </p>
          <p style="color:#555;line-height:1.7;margin:0">
            Ab morgen früh bekommst du täglich deine Ausschreibungs-Treffer
            direkt ins Postfach.
          </p>
        </div>
      </div>
    </body>
    </html>"""
    return _send(to_email, subject, html)
