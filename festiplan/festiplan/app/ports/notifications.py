"""
Port sortant de notification.

Le cœur applicatif utilise ce contrat pour envoyer des notifications
sans connaître le mécanisme d'envoi (email, SMS, webhook…).
"""
from abc import ABC, abstractmethod


class INotificationPort(ABC):
    """
    Port de notification.

    Contrat : la méthode notify ne doit jamais propager d'exception vers
    l'appelant. Les implémentations doivent gérer les erreurs en interne
    (log, file d'attente, etc.).
    """

    @abstractmethod
    def notify(self, subject: str, message: str) -> None:
        """
        Envoie une notification.

        :param subject: objet/titre de la notification
        :param message: corps du message
        """
