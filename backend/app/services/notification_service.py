"""
app/services/notification_service.py

Control de consumo del plan y envío de alertas por email.
- Al 80% (1.200 / 1.500 conversaciones): alerta de advertencia
- Al 100% (1.500 / 1.500 conversaciones): alerta de límite alcanzado
"""
import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session as DBSession

from app.core.settings import settings
from app.db.models.messaging import PlanUsage

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: DBSession):
        self.db = db

    # ── PLAN USAGE ────────────────────────────────────────────────────────────

    def get_or_create_current_period(self) -> PlanUsage:
        """Obtiene o crea el registro de uso del mes actual."""
        today = date.today()
        period = date(today.year, today.month, 1)

        usage = self.db.query(PlanUsage).filter(PlanUsage.period_month == period).first()
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
        """
        Incrementa el contador de conversaciones del mes actual.
        Verifica y dispara alertas si se superan los umbrales.
        """
        usage = self.get_or_create_current_period()
        usage.conversation_count = (usage.conversation_count or 0) + 1
        self.db.flush()

        limit = usage.plan_limit or settings.plan_monthly_limit
        count = usage.conversation_count
        pct = count / limit

        # Alerta 80%
        if pct >= 0.80 and not usage.alert_80_sent and settings.alert_email_80_percent:
            self._send_alert_80(count, limit)
            usage.alert_80_sent = 1
            self.db.flush()
            logger.info("Alerta 80%% enviada | count=%s / %s", count, limit)

        # Alerta 100%
        if pct >= 1.00 and not usage.alert_100_sent and settings.alert_email_100_percent:
            self._send_alert_100(count, limit)
            usage.alert_100_sent = 1
            self.db.flush()
            logger.info("Alerta 100%% enviada | count=%s / %s", count, limit)

        return usage

    def get_current_usage(self) -> dict:
        usage = self.get_or_create_current_period()
        limit = usage.plan_limit or settings.plan_monthly_limit
        return {
            "period": str(usage.period_month),
            "count": usage.conversation_count,
            "limit": limit,
            "percentage": round((usage.conversation_count / limit) * 100, 1),
            "alert_80_sent": bool(usage.alert_80_sent),
            "alert_100_sent": bool(usage.alert_100_sent),
        }

    # ── EMAIL ─────────────────────────────────────────────────────────────────

    def _send_email(self, subject: str, html_body: str) -> None:
        if not settings.admin_alert_email or not settings.smtp_user:
            logger.warning("Email no configurado — no se envió alerta: %s", subject)
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
            msg["To"] = settings.admin_alert_email
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_user, settings.admin_alert_email, msg.as_string())

            logger.info("Email enviado a %s | subject: %s", settings.admin_alert_email, subject)
        except Exception as exc:
            logger.exception("Error enviando email de alerta: %s", exc)

    def _send_alert_80(self, count: int, limit: int) -> None:
        subject = f"[LLV Assistant] ⚠️ Has usado el 80% de tus conversaciones del plan"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
          <div style="background:#1B5E3F;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="color:white;margin:0">⚠️ Alerta de consumo — LLV Assistant</h1>
          </div>
          <div style="background:#f9f9f9;padding:24px;border:1px solid #ddd">
            <p style="font-size:16px">Has utilizado <strong>{count} de {limit} conversaciones</strong>
            incluidas en tu plan <strong>Profesional</strong> este mes.</p>
            <div style="background:#FFF9C4;border-left:4px solid #F9A825;padding:12px;margin:16px 0">
              <strong>Te quedan {limit - count} conversaciones disponibles.</strong><br>
              Considera adquirir un paquete adicional de conversaciones para no interrumpir el servicio.
            </div>
            <p>Para adquirir conversaciones adicionales, contacta a tu proveedor técnico:</p>
            <p><strong>José Cortinez</strong> | jcortinezosorio@gmail.com | +57 310 742 6028</p>
          </div>
          <div style="background:#eeeeee;padding:12px;text-align:center;border-radius:0 0 8px 8px;font-size:12px;color:#888">
            LLV Assistant — Sistema automático de monitoreo del plan
          </div>
        </div>
        """
        self._send_email(subject, html)

    def _send_alert_100(self, count: int, limit: int) -> None:
        subject = f"[LLV Assistant] 🚨 LÍMITE ALCANZADO — 1.500 conversaciones consumidas"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
          <div style="background:#B71C1C;padding:20px;border-radius:8px 8px 0 0">
            <h1 style="color:white;margin:0">🚨 Límite de conversaciones alcanzado</h1>
          </div>
          <div style="background:#f9f9f9;padding:24px;border:1px solid #ddd">
            <p style="font-size:16px">Has alcanzado el límite de <strong>{limit} conversaciones</strong>
            incluidas en tu plan <strong>Profesional</strong> este mes.</p>
            <div style="background:#FFEBEE;border-left:4px solid #C62828;padding:12px;margin:16px 0">
              <strong>El bot continuará operando, pero las conversaciones adicionales
              se facturarán como excedente.</strong>
            </div>
            <p>Contacta <strong>inmediatamente</strong> a tu proveedor para adquirir un paquete adicional:</p>
            <p><strong>José Cortinez</strong> | jcortinezosorio@gmail.com | +57 310 742 6028</p>
          </div>
          <div style="background:#eeeeee;padding:12px;text-align:center;border-radius:0 0 8px 8px;font-size:12px;color:#888">
            LLV Assistant — Sistema automático de monitoreo del plan
          </div>
        </div>
        """
        self._send_email(subject, html)
