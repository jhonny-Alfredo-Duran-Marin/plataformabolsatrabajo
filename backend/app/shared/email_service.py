import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Envío de correo transaccional. En Sprint 0 solo registra el envío en el log;
    la integración SMTP real (RF-W01, RF-W04) se conecta aquí en un sprint posterior."""

    def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        logger.info("Correo a %s | asunto: %s\n%s", destinatario, asunto, cuerpo)
