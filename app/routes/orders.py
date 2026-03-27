import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Cart, Order, Coupon
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order import creer_commande, mettre_a_jour_statut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == order_data.user_id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Panier vide ou inexistant")
    coupon = None
    if order_data.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == order_data.coupon_code.upper(),
            Coupon.actif == True
        ).first()
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon non trouvé ou inactif")
    try:
        order = creer_commande(order_data.user_id, cart, db, coupon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Commande {order_id} non trouvée")
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db)
):
    try:
        order = mettre_a_jour_statut(order_id, status_update.status, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order


@router.get("/user/{user_id}", response_model=list[OrderResponse])
def get_user_orders(user_id: int, db: Session = Depends(get_db)):
    return db.query(Order).filter(Order.user_id == user_id).all()