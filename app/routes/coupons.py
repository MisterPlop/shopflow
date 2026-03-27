import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Coupon
from app.schemas import CouponCreate, CouponResponse, CouponApplyRequest, CouponApplyResponse
from app.services.pricing import appliquer_coupon

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.post("/", response_model=CouponResponse, status_code=201)
def create_coupon(coupon_data: CouponCreate, db: Session = Depends(get_db)):
    existing = db.query(Coupon).filter(Coupon.code == coupon_data.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Coupon '{coupon_data.code}' existe déjà")
    coupon = Coupon(**coupon_data.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.get("/{code}", response_model=CouponResponse)
def get_coupon(code: str, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(
        Coupon.code == code.upper(),
        Coupon.actif == True
    ).first()
    if not coupon:
        raise HTTPException(status_code=404, detail=f"Coupon '{code}' non trouvé ou inactif")
    return coupon


@router.post("/apply", response_model=CouponApplyResponse)
def apply_coupon(request: CouponApplyRequest, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(
        Coupon.code == request.coupon_code.upper(),
        Coupon.actif == True
    ).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon non trouvé ou inactif")
    try:
        prix_final = appliquer_coupon(request.prix, coupon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CouponApplyResponse(
        prix_initial=request.prix,
        prix_final=prix_final,
        reduction_appliquee=coupon.reduction,
        coupon_code=coupon.code
    )