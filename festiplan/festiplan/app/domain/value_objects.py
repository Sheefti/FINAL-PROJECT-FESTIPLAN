"""
Value objects et enums du domaine FestiPlan.
"""
from enum import Enum


class FestivalStatus(str, Enum):
    """
    Cycle de vie d'un festival.

    preparation → published
    Un festival publié est verrouillé : les concerts ne peuvent plus être
    déplacés ni annulés directement.
    """
    PREPARATION = "preparation"
    PUBLISHED = "published"


class ConcertStatus(str, Enum):
    """Cycle de vie d'un concert."""
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
