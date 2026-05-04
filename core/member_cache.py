"""
Cache de miembros de la familia para evitar lecturas stale.

El problema: cuando un usuario hace logout y otro login, Flet puede
cachear controles de la vista anterior. Si la nueva vista se renderiza
usando datos de una sesión anterior, los miembros muestran información
incorrecta.

La solución: un cache por familia_id que se limpia automáticamente
cuando un usuario hace logout de esa familia.
"""
from __future__ import annotations

import logging
from typing import NamedTuple

from models.family_member_model import FamilyMember

logger = logging.getLogger(__name__)


class CacheEntry(NamedTuple):
    members: list[FamilyMember]
    timestamp: float


class FamilyMemberCache:
    """
    Cache en memoria para miembros de la familia.

    Cada entrada es {familia_id: CacheEntry(members, timestamp)}.
    Se invalidar cuando el usuario hace logout.

    Por qué no es un problema de "autoridad dividida":
    - Este cache es un READ-THROUGH cache: si el dato no está en cache,
      se lee de la BD y se almacena.
    - La BD es siempre la fuente de verdad. El cache solo evita
      lecturas repetidas innecesarias.
    - Al hacer logout, se limpia el cache de esa familia, asegurando
      que no haya datos stale de una sesión anterior.
    """

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self._cache: dict[int, CacheEntry] = {}
        self._ttl = ttl_seconds

    def get(self, familia_id: int) -> list[FamilyMember] | None:
        """
        Obtener miembros del cache si existe y no expiró.
        Retorna None si no hay cache o expiró.
        """
        import time

        if familia_id not in self._cache:
            return None

        entry = self._cache[familia_id]
        if time.time() - entry.timestamp > self._ttl:
            logger.info(
                "[MemberCache] Cache expirado para familia %d, invalidando",
                familia_id,
            )
            del self._cache[familia_id]
            return None

        logger.info(
            "[MemberCache] Cache HIT para familia %d (%d miembros)",
            familia_id,
            len(entry.members),
        )
        return entry.members

    def set(self, familia_id: int, members: list[FamilyMember]) -> None:
        """Almacenar miembros en cache."""
        import time

        self._cache[familia_id] = CacheEntry(
            members=list(members),
            timestamp=time.time(),
        )
        logger.info(
            "[MemberCache] Cache SET para familia %d (%d miembros)",
            familia_id,
            len(members),
        )

    def invalidate(self, familia_id: int) -> None:
        """Invalidar cache de una familia (llamar en logout)."""
        if familia_id in self._cache:
            logger.info(
                "[MemberCache] Cache INVALIDATED para familia %d",
                familia_id,
            )
            del self._cache[familia_id]

    def clear(self) -> None:
        """Limpiar todo el cache."""
        self._cache.clear()
        logger.info("[MemberCache] Cache CLEARED")


# Singleton global del proceso
member_cache = FamilyMemberCache()