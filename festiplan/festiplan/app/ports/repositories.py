"""
Ports sortants (driven ports) — contrats de persistance.

Le cœur applicatif dépend de ces interfaces, jamais des implémentations
SQLAlchemy. Cela permet de tester les cas d'utilisation avec des doubles
en mémoire sans toucher à la base de données.
"""
from abc import ABC, abstractmethod
from typing import Optional


class IConcertRepository(ABC):
    """Contrat pour la persistance des concerts."""

    @abstractmethod
    def get(self, concert_id: int):
        """Renvoie un concert par son identifiant, ou None."""

    @abstractmethod
    def list_for_festival(self, festival_id: int) -> list:
        """Renvoie la liste des concerts actifs d'un festival, triés par heure."""

    @abstractmethod
    def create(self, concert) -> object:
        """Persiste et renvoie un concert."""

    @abstractmethod
    def save(self, concert) -> object:
        """Persiste les modifications d'un concert existant."""


class IFestivalRepository(ABC):
    """Contrat pour la persistance des festivals."""

    @abstractmethod
    def get(self, festival_id: int):
        """Renvoie un festival par son identifiant, ou None."""

    @abstractmethod
    def list(self) -> list:
        """Renvoie tous les festivals."""

    @abstractmethod
    def create(self, festival) -> object:
        """Persiste et renvoie un festival."""

    @abstractmethod
    def save(self, festival) -> object:
        """Persiste les modifications d'un festival existant."""


class IStageRepository(ABC):
    """Contrat pour la persistance des scènes."""

    @abstractmethod
    def get(self, stage_id: int):
        """Renvoie une scène par son identifiant, ou None."""

    @abstractmethod
    def list_for_festival(self, festival_id: int) -> list:
        """Renvoie les scènes d'un festival."""

    @abstractmethod
    def create(self, stage) -> object:
        """Persiste et renvoie une scène."""


class IArtistRepository(ABC):
    """Contrat pour la persistance des artistes."""

    @abstractmethod
    def get(self, artist_id: int):
        """Renvoie un artiste par son identifiant, ou None."""

    @abstractmethod
    def list(self) -> list:
        """Renvoie tous les artistes."""

    @abstractmethod
    def create(self, artist) -> object:
        """Persiste et renvoie un artiste."""


class IIncidentRepository(ABC):
    """Contrat pour la persistance des incidents."""

    @abstractmethod
    def create(self, incident) -> object:
        """Persiste et renvoie un incident."""

    @abstractmethod
    def list(self, concert_id: Optional[int] = None) -> list:
        """Renvoie les incidents, filtrés optionnellement par concert."""
