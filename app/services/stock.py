# app/services/stock.py
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Product
from app.cache import redis_client

logger = logging.getLogger(__name__)
STOCK_CACHE_TTL = 600


def _stock_cache_key(product_id: int) -> str:
    return f"product:{product_id}:stock"


def verifier_stock(product: Product, quantite: int) -> bool:
    if quantite <= 0:
        raise ValueError(f"Quantité invalide : {quantite}.")
    return product.stock >= quantite


def reserver_stock(product: Product, quantite: int, session: Session) -> Product:
    if not verifier_stock(product, quantite):
        raise ValueError(
            f"Stock insuffisant pour '{product.name}' : "
            f"{product.stock} disponible(s), {quantite} demandé(s)."
        )
    product.stock -= quantite
    session.commit()
    session.refresh(product)
    redis_client.delete(_stock_cache_key(product.id))
    return product


def liberer_stock(product: Product, quantite: int, session: Session) -> Product:
    if quantite <= 0:
        raise ValueError(f"Quantité invalide : {quantite}")
    product.stock += quantite
    session.commit()
    session.refresh(product)
    redis_client.set(_stock_cache_key(product.id), product.stock)
    return product


def get_stock_cached(product_id: int) -> Optional[int]:
    cached = redis_client.get(_stock_cache_key(product_id))
    if cached is not None:
        return int(cached)
    return None