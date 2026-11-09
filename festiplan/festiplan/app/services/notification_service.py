"""
Adaptateur de notification par email.

Implémente INotificationPort en déléguant à send_email.

CORRECTION Défaut 2 :
    Les exceptions levées par send_email (ex. RuntimeError quand
    fail_notifications=True) sont attrapées ICI et loggées.
    Elles ne sont jamais propagées à l'appelant : la notification est
    considérée best-effort. L'API ne retourne plus HTTP 500 après
    avoir déjà persisté une modification.
"""
import logging

from app.ports.notifications import INotificationPort
from app.utils.email_sender import send_email

logger = logging.getLogger(__name__)


class EmailNotificationAdapter(INotificationPort):
    """Envoi de notifications par email (best-effort)."""

    RECIPIENT = "production@festiplan.test"

    def notify(self, subject: str, message: str) -> None:
        """
        Envoie un email. Si l'envoi échoue, l'erreur est loggée
        et NON propagée (contrat du port).
        """
        try:
            send_email(self.RECIPIENT, subject, message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Échec de la notification email '%s' : %s", subject, exc)


# Alias de rétrocompatibilité pour le code qui utilise encore NotificationService.
NotificationService = EmailNotificationAdapter

