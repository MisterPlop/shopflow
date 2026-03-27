# app/services/cart.py
import logging
from sqlalchemy.orm import Session
from app.models import Cart, CartItem, Product
from app.services.pricing import calcul_prix_ttc
from app.services.stock import verifier_stock

logger = logging.getLogger(__name__)


def get_or_create_cart(user_id: int, session: Session) -> Cart:
    cart = session.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        session.add(cart)
        session.commit()
        session.refresh(cart)
    return cart


def ajouter_au_panier(
    product: Product,
    quantite: int,
    user_id: int,
    session: Session
) -> Cart:
    if quantite <= 0:
        raise ValueError(f"Quantité invalide : {quantite}")

    if not verifier_stock(product, quantite):
        raise ValueError(
            f"Stock insuffisant pour '{product.name}' : "
            f"{product.stock} disponible(s), {quantite} demandé(s)."
        )

    cart = get_or_create_cart(user_id, session)

    existing_item = session.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product.id
    ).first()

    if existing_item:
        existing_item.quantity += quantite
    else:
        item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantite)
        session.add(item)

    session.commit()
    session.refresh(cart)
    return cart


def retirer_du_panier(cart: Cart, product_id: int, session: Session) -> Cart:
    item = session.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product_id
    ).first()
    if not item:
        raise ValueError(f"Produit {product_id} non trouvé dans le panier")
    session.delete(item)
    session.commit()
    session.refresh(cart)
    return cart


def vider_panier(cart: Cart, session: Session) -> Cart:
    session.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    session.commit()
    session.refresh(cart)
    return cart


def calculer_sous_total(cart: Cart) -> float:
    if not cart.items:
        return 0.0
    return round(
        sum(item.product.price * item.quantity for item in cart.items), 2
    )


def calculer_total_ttc(cart: Cart) -> float:
    return calcul_prix_ttc(calculer_sous_total(cart))