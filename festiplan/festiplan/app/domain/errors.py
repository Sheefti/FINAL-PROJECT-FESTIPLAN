"""
Exceptions métier du domaine FestiPlan.
Ces exceptions sont indépendantes de tout framework (FastAPI, SQLAlchemy…).
"""


class DomainError(Exception):
    """Classe de base pour toutes les erreurs métier."""


class NotFoundError(DomainError):
    """Ressource introuvable."""


class ConflictError(DomainError):
    """Chevauchement de créneaux ou contrainte d'unicité violée."""


class ValidationError(DomainError):
    """Données invalides selon les règles métier."""


class FestivalLockedError(DomainError):
    """Opération refusée car le festival est publié (état verrouillé)."""


class EquipmentError(DomainError):
    """La scène ne dispose pas des équipements requis par l'artiste."""
