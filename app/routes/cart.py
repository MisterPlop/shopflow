import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, Cart
from app.schemas import CartItemCreate, CartResponse
from app.services.cart import (
    ajouter_au_panier, retirer_du_panier, vider_panier,
    get_or_create_cart, calculer_total_ttc
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/", response_model=CartResponse, status_code=201)
def add_to_cart(item: CartItemCreate, user_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.id == item.product_id,
        Product.active == True
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {item.product_id} non trouvé")
    try:
        cart = ajouter_au_panier(product, item.quantity, user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    response = CartResponse.model_validate(cart)
    response.sous_total = calculer_total_ttc(cart)
    return response


@router.get("/{user_id}", response_model=CartResponse)
def get_cart(user_id: int, db: Session = Depends(get_db)):
    cart = get_or_create_cart(user_id, db)
    response = CartResponse.model_validate(cart)
    response.sous_total = calculer_total_ttc(cart)
    return response


@router.delete("/{user_id}/item/{product_id}", response_model=CartResponse)
def remove_from_cart(user_id: int, product_id: int, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Panier non trouvé")
    try:
        cart = retirer_du_panier(cart, product_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    response = CartResponse.model_validate(cart)
    response.sous_total = calculer_total_ttc(cart)
    return response


@router.delete("/{user_id}", status_code=204)
def clear_cart(user_id: int, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Panier non trouvé")
    vider_panier(cart, db)