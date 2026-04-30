"""
app/services/notification_service.py

Control de consumo del plan y notificaciones por email.
- Al 80%: alerta de advertencia
- Al 100%: alerta de límite
- Escalada a agente: notificación al agente asignado
"""
import logging
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session as DBSession

from app.core.settings import settings
from app.db.models.messaging import PlanUsage

logger = logging.getLogger(__name__)

DASHBOARD_URL = "http://localhost:5175"


class NotificationService:
    def __init__(self, db: DBSession):
        self.db = db

    # ── PLAN USAGE ────────────────────────────────────────────────────────────

    def get_or_create_current_period(self) -> PlanUsage:
        today = date.today()
        period = date(today.year, today.month, 1)

        usage = (
            self.db.query(PlanUsage)
            .filter(PlanUsage.period_month == period)
            .first()
        )

        if not usage:
            usage = PlanUsage(
                period_month=period,
                conversation_count=0,
                plan_limit=settings.plan_monthly_limit,
            )
            self.db.add(usage)
            self.db.flush()

        return usage

    def increment_conversation(self) -> PlanUsage:
        usage = self.get_or_create_current_period()
        usage.conversation_count = (usage.conversation_count or 0) + 1
        self.db.flush()

        limit = usage.plan_limit or settings.plan_monthly_limit
        count = usage.conversation_count
        pct = count / limit if limit else 0

        if pct >= 0.80 and not usage.alert_80_sent and settings.alert_email_80_percent:
            self._send_alert_80(count, limit)
            usage.alert_80_sent = 1
            self.db.flush()

        if pct >= 1.00 and not usage.alert_100_sent and settings.alert_email_100_percent:
            self._send_alert_100(count, limit)
            usage.alert_100_sent = 1
            self.db.flush()

        return usage

    def get_current_usage(self) -> dict:
        """
        Fuente confiable para el dashboard:
        calcula el uso mensual desde llv_analytics_events, no desde el contador acumulado.

        Esto evita desfases cuando:
        - una conversación no incrementó PlanUsage correctamente,
        - se corrigió manualmente una sesión,
        - hubo reinicios o errores antes del commit,
        - el dashboard necesita reflejar conversaciones reales.
        """
        from sqlalchemy import func
        from app.db.models.analytics import AnalyticsEvent

        today = date.today()
        period_start = date(today.year, today.month, 1)

        real_count = (
            self.db.query(func.count(AnalyticsEvent.id))
            .filter(
                AnalyticsEvent.event_type == "conversation_started",
                AnalyticsEvent.created_at >= period_start,
            )
            .scalar()
            or 0
        )

        usage = self.get_or_create_current_period()
        usage.conversation_count = real_count
        self.db.flush()

        limit = usage.plan_limit or settings.plan_monthly_limit

        return {
            "period": str(usage.period_month),
            "count": real_count,
            "limit": limit,
            "percentage": round((real_count / limit) * 100, 1) if limit else 0,
            "alert_80_sent": bool(usage.alert_80_sent),
            "alert_100_sent": bool(usage.alert_100_sent),
        }

    # ── NOTIFICACIÓN AL AGENTE ────────────────────────────────────────────────

    def notify_agent_escalation(
        self,
        agent_email: str,
        agent_name: str,
        patient_name: str,
        patient_number: str,
        reason: str,
        ai_summary: str | None,
        session_id: int,
    ) -> None:
        """
        Envía email al agente cuando se le asigna una conversación escalada.
        """
        if not agent_email or not settings.smtp_user:
            logger.warning("Email no configurado — no se notificó al agente %s", agent_name)
            return

        hora = datetime.now().strftime("%I:%M %p")

        summary_html = ""
        if ai_summary:
            summary_html = f"""
            <div style="background:#EAF4EF;border-left:4px solid #1B5E3F;padding:12px;margin:16px 0;border-radius:0 8px 8px 0">
                <p style="font-size:13px;color:#1B5E3F;font-weight:bold;margin:0 0 6px 0">📋 Resumen de la conversación:</p>
                <p style="font-size:13px;color:#333;margin:0;white-space:pre-wrap">{ai_summary}</p>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
          <div style="max-width:580px;margin:30px auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1)">

            <!-- Header -->
            <div style="background:#0b4c45;padding:24px 28px">
              <h1 style="color:#C6A96B;margin:0;font-size:20px">🔔 Tienes un cliente esperando</h1>
              <p style="color:rgba(255,255,255,0.7);margin:6px 0 0 0;font-size:13px">LLV Wellness Clinic · {hora}</p>
            </div>

            <!-- Body -->
            <div style="padding:24px 28px">
              <p style="font-size:16px;color:#333">Hola <strong>{agent_name}</strong>,</p>
              <p style="font-size:14px;color:#555">Se te ha asignado una nueva conversación en el chat de LLV Assistant.</p>

              <!-- Cliente info -->
              <div style="background:#F5F1EB;border-radius:8px;padding:16px;margin:16px 0">
                <table style="width:100%;font-size:14px;color:#333">
                  <tr>
                    <td style="padding:4px 0;color:#7a6a55;width:40%">👤 Cliente:</td>
                    <td style="padding:4px 0"><strong>{patient_name or 'No identificado'}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding:4px 0;color:#7a6a55">📱 WhatsApp:</td>
                    <td style="padding:4px 0"><strong>+{patient_number}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding:4px 0;color:#7a6a55">💬 Motivo:</td>
                    <td style="padding:4px 0">{reason}</td>
                  </tr>
                </table>
              </div>

              {summary_html}

              <!-- CTA -->
              <div style="text-align:center;margin:24px 0">
                <a href="{DASHBOARD_URL}/conversations"
                   style="background:#0b4c45;color:white;padding:14px 32px;border-radius:8px;
                          text-decoration:none;font-size:15px;font-weight:bold;display:inline-block">
                  💬 Ir al dashboard → Responder
                </a>
              </div>

              <p style="font-size:12px;color:#999;text-align:center">
                El cliente está esperando tu respuesta en tiempo real.<br>
                Accede al dashboard y selecciona la conversación asignada.
              </p>
            </div>

            <!-- Footer -->
            <div style="background:#F5F1EB;padding:16px 28px;border-top:1px solid #e5ddd4">
              <p style="font-size:11px;color:#7a6a55;margin:0;text-align:center">
                LLV Aesthetic & Wellness Clinic · Sistema LLV Assistant
              </p>
            </div>
          </div>
        </body>
        </html>
        """

        subject = f"🔔 Cliente esperando — {patient_name or patient_number} | LLV Assistant"
        self._send_email_to(agent_email, subject, html)

    # ── EMAIL HELPERS ─────────────────────────────────────────────────────────

    def _send_email_to(self, to_email: str, subject: str, html_body: str) -> None:
        """Envía email a una dirección específica."""
        if not settings.smtp_user or not settings.smtp_password:
            logger.warning("SMTP no configurado — no se envió: %s", subject)
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
            msg["To"] = to_email
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_user, to_email, msg.as_string())

            logger.info("Email enviado a %s | %s", to_email, subject)

        except Exception as exc:
            logger.exception("Error enviando email a %s: %s", to_email, exc)

    def _send_email(self, subject: str, html_body: str) -> None:
        """Envía email al admin (alertas de plan)."""
        self._send_email_to(settings.admin_alert_email, subject, html_body)

    def _send_alert_80(self, count: int, limit: int) -> None:
        subject = "[LLV Assistant] ⚠️ Has usado el 80% de tus conversaciones"

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
          <div style="background:#0b4c45;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="color:white;margin:0">⚠️ Alerta de consumo — LLV Assistant</h1>
          </div>
          <div style="background:#f9f9f9;padding:24px;border:1px solid #ddd">
            <p>Has utilizado <strong>{count} de {limit} conversaciones</strong> del plan Profesional este mes.</p>
            <div style="background:#FFF9C4;border-left:4px solid #F9A825;padding:12px;margin:16px 0">
              <p style="margin:0">⚠️ Estás al <strong>80%</strong> del límite mensual.</p>
            </div>
            <p>Considera adquirir conversaciones adicionales para evitar interrupciones.</p>
          </div>
        </div>
        """

        self._send_email(subject, html)

    def _send_alert_100(self, count: int, limit: int) -> None:
        subject = "[LLV Assistant] 🚨 Límite de conversaciones alcanzado"

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
          <div style="background:#B71C1C;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="color:white;margin:0">🚨 Límite alcanzado — LLV Assistant</h1>
          </div>
          <div style="background:#f9f9f9;padding:24px;border:1px solid #ddd">
            <p>Has alcanzado el límite de <strong>{limit} conversaciones</strong> del plan Profesional.</p>
            <div style="background:#FFEBEE;border-left:4px solid #B71C1C;padding:12px;margin:16px 0">
              <p style="margin:0">🚨 El bot dejará de responder hasta que adquieras conversaciones adicionales.</p>
            </div>
            <p>Contacta a tu proveedor para adquirir un plan adicional.</p>
          </div>
        </div>
        """

        self._send_email(subject, html)