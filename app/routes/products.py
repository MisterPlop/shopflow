import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.cache import get_cached, set_cached, delete_cached

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["products"])
PRODUCT_CACHE_TTL = 300


@router.get("/", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.active == True)
    if category:
        query = query.filter(Product.category == category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    return query.offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    cache_key = f"product:{product_id}"
    cached = get_cached(cache_key)
    if cached:
        return json.loads(cached)
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.active == True
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {product_id} non trouvé")
    set_cached(cache_key, json.dumps({
        "id": product.id, "name": product.name, "price": product.price,
        "stock": product.stock, "category": product.category,
        "description": product.description, "active": product.active,
        "created_at": product.created_at.isoformat()
    }), PRODUCT_CACHE_TTL)
    return product


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**product_data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, updates: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {product_id} non trouvé")
    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    delete_cached(f"product:{product_id}")
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {product_id} non trouvé")
    product.active = False
    db.commit()
    delete_cached(f"product:{product_id}")