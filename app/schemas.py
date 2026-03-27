# app/schemas.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

# PRODUCT 
class ProductCreate(BaseModel):
    name:     str   = Field(..., min_length=1, max_length=100)
    price:    float = Field(..., gt=0, description="Prix HT")
    stock:    int   = Field(default=0, ge=0)
    category: Optional[str] = None
    active:   bool  = True

class ProductResponse(ProductCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}
    # ↑ Permet de convertir un objet SQLAlchemy directement en schema

class ProductUpdate(BaseModel):
    name:        Optional[str]   = Field(None, min_length=1, max_length=100)
    description: Optional[str]   = None
    price:       Optional[float] = Field(None, gt=0)
    stock:       Optional[int]   = Field(None, ge=0)
    category:    Optional[str]   = None
    active:      Optional[bool]  = None

# COUPON 
class CouponCreate(BaseModel):
    code:      str   = Field(..., min_length=1, max_length=20)
    reduction: float = Field(..., gt=0, le=100)
    actif:     bool  = True

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, v: str) -> str:
        return v.upper()  # PROMO20, pas promo20

class CouponResponse(BaseModel):
    code: str
    reduction: float
    actif: bool
    model_config = {"from_attributes": True}

class CouponApplyRequest(BaseModel):
    prix:        float = Field(..., gt=0)
    coupon_code: str   = Field(..., min_length=1, max_length=20)


class CouponApplyResponse(BaseModel):
    prix_initial:        float
    prix_final:          float
    reduction_appliquee: float
    coupon_code:         str

class CartItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity:   int = Field(..., gt=0, le=100)

class CartItemResponse(BaseModel):
    id:         int
    product_id: int
    quantity:   int
    product:    Optional[ProductResponse] = None
    model_config = {'from_attributes': True}

class CartResponse(BaseModel):
    id:         int
    user_id:    int
    items:      List[CartItemResponse] = []
    sous_total: float = 0.0
    model_config = {'from_attributes': True}

# ORDER 

class OrderCreate(BaseModel):
    user_id:     int           = Field(..., gt=0)
    coupon_code: Optional[str] = Field(None, max_length=20)

class OrderItemResponse(BaseModel):
    id:         int
    product_id: int
    quantity:   int
    unit_price: float
    model_config = {'from_attributes': True}

class OrderResponse(BaseModel):
    id:          int
    user_id:     int
    total_ht:    float
    total_ttc:   float
    coupon_code: Optional[str]
    status:      str
    created_at:  datetime
    items:       List[OrderItemResponse] = []
    model_config = {'from_attributes': True}

class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|confirmed|shipped|cancelled)$")