"""Envío de correo (avisos de cuenta y reportes personalizados).

Dos formas de enviar, según lo que esté configurado:
- SMTP (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD), por ejemplo Gmail con una
  contraseña de aplicación.
- La API HTTPS de Brevo (BREVO_API_KEY), para servidores que bloquean los puertos SMTP
  (como los planes básicos de Railway). El remitente (SMTP_FROM) tiene que estar
  verificado en Brevo.
Sin ninguna de las dos, los avisos de cuenta solo quedan en el log y el envío de
reportes avisa que el correo no está configurado.
"""

import base64
import json
import logging
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

from app.common.exceptions import ServiceUnavailableException
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_BREVO_URL = "https://api.brevo.com/v3/smtp/email"
_TIEMPO_MAXIMO = 20

Adjunto = tuple[str, bytes, str]  # nombre, contenido, tipo MIME


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def configurado(self) -> bool:
        return bool(self.settings.brevo_api_key or self.settings.smtp_host)

    def exigir_configuracion(self) -> None:
        if not self.configurado():
            raise ServiceUnavailableException(
                "El envío por correo no está configurado en el servidor. Descargá el archivo y envialo vos."
            )

    def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        """Aviso de cuenta: si falla, se registra en el log y el trámite sigue."""
        if not self.configurado():
            if self.settings.environment == "production":
                # En producción el cuerpo no va al log (puede tener datos personales): solo se avisa que no salió.
                logger.warning("Correo sin configurar: no se envió a %s (asunto: %s).", destinatario, asunto)
            else:
                logger.info("Correo a %s | asunto: %s\n%s", destinatario, asunto, cuerpo)
            return
        try:
            self._enviar([destinatario], asunto, cuerpo, [])
        except Exception:  # noqa: BLE001 - un correo caído no corta el registro ni la aprobación
            logger.exception("No se pudo enviar el correo a %s", destinatario)

    def enviar_con_adjuntos(self, destinatarios: list[str], asunto: str, cuerpo: str, adjuntos: list[Adjunto]) -> None:
        """Envío pedido por el usuario: si falla, se lo avisa."""
        self.exigir_configuracion()
        try:
            self._enviar(destinatarios, asunto, cuerpo, adjuntos)
        except Exception as exc:
            logger.exception("No se pudo enviar el correo a %s", destinatarios)
            raise ServiceUnavailableException(
                "No se pudo enviar el correo. Revisá las direcciones o intentá de nuevo en unos minutos."
            ) from exc

    def _enviar(self, destinatarios: list[str], asunto: str, cuerpo: str, adjuntos: list[Adjunto]) -> None:
        if self.settings.brevo_api_key:
            self._por_brevo(destinatarios, asunto, cuerpo, adjuntos)
        else:
            self._por_smtp(destinatarios, asunto, cuerpo, adjuntos)

    def _por_smtp(self, destinatarios: list[str], asunto: str, cuerpo: str, adjuntos: list[Adjunto]) -> None:
        s = self.settings
        mensaje = EmailMessage()
        mensaje["From"] = f"EGRESA <{s.smtp_from}>"
        mensaje["To"] = ", ".join(destinatarios)
        mensaje["Subject"] = asunto
        mensaje.set_content(cuerpo)
        for nombre, contenido, tipo in adjuntos:
            principal, _, secundario = tipo.split(";")[0].strip().partition("/")
            mensaje.add_attachment(contenido, maintype=principal, subtype=secundario, filename=nombre)
        contexto = ssl.create_default_context()
        if s.smtp_port == 465:
            servidor = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=_TIEMPO_MAXIMO, context=contexto)
        else:
            servidor = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=_TIEMPO_MAXIMO)
        with servidor:
            if s.smtp_port != 465 and servidor.has_extn("starttls"):
                servidor.starttls(context=contexto)
            if s.smtp_user and s.smtp_password:
                servidor.login(s.smtp_user, s.smtp_password)
            servidor.send_message(mensaje)

    def _por_brevo(self, destinatarios: list[str], asunto: str, cuerpo: str, adjuntos: list[Adjunto]) -> None:
        datos = {
            "sender": {"name": "EGRESA", "email": self.settings.smtp_from},
            "to": [{"email": d} for d in destinatarios],
            "subject": asunto,
            "textContent": cuerpo,
        }
        if adjuntos:
            datos["attachment"] = [
                {"name": nombre, "content": base64.b64encode(contenido).decode()} for nombre, contenido, _ in adjuntos
            ]
        pedido = urllib.request.Request(
            _BREVO_URL,
            data=json.dumps(datos).encode(),
            headers={"api-key": self.settings.brevo_api_key, "content-type": "application/json", "accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(pedido, timeout=_TIEMPO_MAXIMO):
                pass
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Brevo respondió {exc.code}: {exc.read()[:300]!r}") from exc
