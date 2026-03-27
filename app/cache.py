# app/cache.py
import os
import logging
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def _create_redis_client():
    try:
        import redis
        client = redis.from_url(REDIS_URL, decode_responses=True,
                                socket_connect_timeout=2)
        client.ping()
        logger.info(f"Redis connecté : {REDIS_URL}")
        return client
    except Exception as e:
        logger.warning(f"Redis indisponible ({e}) — MagicMock activé")
        return MagicMock()


redis_client = _create_redis_client()

# ── Helpers de cache ─────────────────────────────────────────
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))


def get_cached(key: str):
    """Récupère une valeur du cache. Retourne None si absente."""
    try:
        return redis_client.get(key)
    except Exception:
        return None


def set_cached(key: str, value: str, ttl: int = CACHE_TTL):
    """Stocke une valeur dans le cache avec TTL."""
    try:
        redis_client.setex(key, ttl, value)
    except Exception:
        pass


def delete_cached(key: str):
    """Invalide une entrée du cache."""
    try:
        redis_client.delete(key)
    except Exception:
        pass