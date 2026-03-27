# app/services/order.py
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Cart, Order, OrderItem, Coupon
from app.services.pricing import appliquer_coupon, calcul_prix_ttc
from app.services.stock import reserver_stock
from app.services.cart import calculer_sous_total, vider_panier

logger = logging.getLogger(__name__)


def creer_commande(
    user_id: int,
    cart: Cart,
    session: Session,
    coupon: Optional[Coupon] = None
) -> Order:
    if not cart.items:
        raise ValueError("Impossible de créer une commande depuis un panier vide.")

    total_ht = calculer_sous_total(cart)
    total_ttc = calcul_prix_ttc(total_ht)

    if coupon:
        total_ttc = appliquer_coupon(total_ttc, coupon)

    order = Order(
        user_id=user_id,
        total_ht=total_ht,
        total_ttc=total_ttc,
        coupon_code=coupon.code if coupon else None,
        status="pending"
    )
    session.add(order)
    session.flush()

    for item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product.id,
            quantity=item.quantity,
            unit_price=item.product.price
        )
        session.add(order_item)
        reserver_stock(item.product, item.quantity, session)

    vider_panier(cart, session)
    session.commit()
    session.refresh(order)
    logger.info(f"Commande créée : order_id={order.id} user={user_id} total_ttc={total_ttc}")
    return order


def mettre_a_jour_statut(order_id: int, nouveau_statut: str, session: Session) -> Order:
    TRANSITIONS_VALIDES = {
        "pending":   ["confirmed", "cancelled"],
        "confirmed": ["shipped",   "cancelled"],
        "shipped":   [],
        "cancelled": [],
    }

    order = session.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ValueError(f"Commande {order_id} non trouvée.")

    if nouveau_statut not in TRANSITIONS_VALIDES.get(order.status, []):
        raise ValueError(
            f"Transition invalide : {order.status} → {nouveau_statut}. "
            f"Transitions autorisées : {TRANSITIONS_VALIDES.get(order.status, [])}"
        )

    order.status = nouveau_statut
    session.commit()
    session.refresh(order)
    return order