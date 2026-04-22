"""T178: SendGrid email notifier — best-effort, never raises into the caller.

The SendGrid Python SDK is synchronous, so we run it via a thread executor.
When `SENDGRID_API_KEY` is unset (dev/test) calls become no-ops and log at debug.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)


def _build_message(*, to_email: str, subject: str, html: str, text: Optional[str] = None) -> Any:
    """Lazy import — SendGrid SDK is heavy and we want test environments to skip it."""
    from sendgrid.helpers.mail import Mail  # type: ignore[import-not-found]

    return Mail(
        from_email=(settings.sendgrid_from_email, settings.sendgrid_from_name),
        to_emails=to_email,
        subject=subject,
        plain_text_content=text or "",
        html_content=html,
    )


def _send_sync(message: Any) -> Optional[int]:
    from sendgrid import SendGridAPIClient  # type: ignore[import-not-found]

    client = SendGridAPIClient(settings.sendgrid_api_key)
    response = client.send(message)
    return getattr(response, "status_code", None)


async def send_email(*, to_email: str, subject: str, html: str, text: Optional[str] = None) -> bool:
    """Best-effort email send. Returns True if the API accepted the message."""
    if not settings.sendgrid_api_key:
        logger.debug("SendGrid not configured — skipping email", extra={"to": to_email, "subject": subject})
        return False

    try:
        message = _build_message(to_email=to_email, subject=subject, html=html, text=text)
        status = await asyncio.to_thread(_send_sync, message)
        accepted = status is not None and 200 <= status < 300
        if not accepted:
            logger.warning("SendGrid returned non-2xx", extra={"status": status, "to": to_email})
        return accepted
    except Exception:
        logger.warning("SendGrid send failed", exc_info=True)
        return False


async def send_client_noor_confirmation(*, to_email: str, full_name: str, reference_id: str) -> bool:
    subject = f"Your Noor Collection request — {reference_id}"
    html = (
        f"<p>Dear {full_name},</p>"
        f"<p>Thank you for your interest in our Noor Collection. Your request "
        f"(<strong>{reference_id}</strong>) is now with our private concierge team.</p>"
        f"<p>We will reach out personally within 48 hours.</p>"
        f"<p>— The Aueshah Atelier</p>"
    )
    return await send_email(to_email=to_email, subject=subject, html=html, text=html)


async def send_client_noor_decision(
    *,
    to_email: str,
    full_name: str,
    reference_id: str,
    decision: str,
) -> bool:
    if decision == "approved":
        subject = f"Your Noor Collection allocation — {reference_id}"
        html = (
            f"<p>Dear {full_name},</p>"
            f"<p>It is our privilege to confirm your Noor allocation "
            f"(<strong>{reference_id}</strong>). A member of our private concierge will "
            f"reach out shortly to arrange your viewing.</p>"
            f"<p>— The Aueshah Atelier</p>"
        )
    else:
        subject = f"An update on your Noor request — {reference_id}"
        html = (
            f"<p>Dear {full_name},</p>"
            f"<p>Thank you for your interest in the Noor Collection. We are unable to "
            f"proceed with this particular request (<strong>{reference_id}</strong>) "
            f"at this time, but our concierge would be glad to share alternatives.</p>"
            f"<p>— The Aueshah Atelier</p>"
        )
    return await send_email(to_email=to_email, subject=subject, html=html, text=html)


async def send_client_appointment_confirmation(
    *,
    to_email: str,
    reference_id: str,
    appointment_type: str,
    preferred_date: Optional[str] = None,
) -> bool:
    subject = f"Your appointment request — {reference_id}"
    when = f"<li>Preferred time: {preferred_date}</li>" if preferred_date else ""
    html = (
        f"<p>Thank you for reaching out to Aueshah.</p>"
        f"<p>We've received your appointment request "
        f"(<strong>{reference_id}</strong>).</p>"
        f"<ul><li>Type: {appointment_type}</li>{when}</ul>"
        f"<p>A member of our concierge team will contact you within 24 hours.</p>"
        f"<p>— The Aueshah Atelier</p>"
    )
    return await send_email(to_email=to_email, subject=subject, html=html, text=html)


async def send_concierge_appointment_alert(
    *,
    to_email: str,
    reference_id: str,
    client_email: str,
    appointment_type: str,
    phone: Optional[str] = None,
    preferred_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    subject = f"[Appointment] {reference_id} — {appointment_type}"
    optional_rows = ""
    if phone:
        optional_rows += f"<li>Phone: {phone}</li>"
    if preferred_date:
        optional_rows += f"<li>Preferred: {preferred_date}</li>"
    if notes:
        optional_rows += f"<li>Notes: {notes}</li>"
    html = (
        f"<p>New appointment request from <strong>{client_email}</strong>.</p>"
        f"<ul>"
        f"<li>Reference: {reference_id}</li>"
        f"<li>Type: {appointment_type}</li>"
        f"{optional_rows}"
        f"</ul>"
    )
    return await send_email(to_email=to_email, subject=subject, html=html, text=html)


async def send_concierge_noor_alert(
    *,
    to_email: str,
    reference_id: str,
    full_name: str,
    purpose: str,
    timeline: str,
    contact_method: str,
    contact_details: str,
) -> bool:
    subject = f"[Noor] New request {reference_id} — {full_name}"
    html = (
        f"<p>New Noor allocation request from <strong>{full_name}</strong>.</p>"
        f"<ul>"
        f"<li>Reference: {reference_id}</li>"
        f"<li>Purpose: {purpose}</li>"
        f"<li>Timeline: {timeline}</li>"
        f"<li>Contact: {contact_method} — {contact_details}</li>"
        f"</ul>"
    )
    return await send_email(to_email=to_email, subject=subject, html=html, text=html)
