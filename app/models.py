from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Product(Base):
    __tablename__ = "products"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price       = Column(Float, nullable=False)     # Prix HT
    stock       = Column(Integer, default=0)
    category    = Column(String(50), nullable=True)
    active      = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    cart_items  = relationship("CartItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

class Coupon(Base):
    __tablename__ = "coupons"
    code       = Column(String(20), primary_key=True)
    reduction  = Column(Float, nullable=False)  # 0 < reduction <= 100
    actif      = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)



class Cart(Base):
    __tablename__ = 'carts'
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items      = relationship('CartItem', back_populates='cart', cascade='all, delete-orphan')

class CartItem(Base):
    __tablename__ = 'cart_items'
    id         = Column(Integer, primary_key=True, index=True)
    cart_id    = Column(Integer, ForeignKey('carts.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity   = Column(Integer, nullable=False, default=1)
    cart       = relationship('Cart',    back_populates='items')
    product    = relationship('Product', back_populates='cart_items')

class Order(Base):
    __tablename__ = 'orders'
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=False, index=True)
    total_ht    = Column(Float, nullable=False)
    total_ttc   = Column(Float, nullable=False)
    coupon_code = Column(String(20), ForeignKey('coupons.code'), nullable=True)
    status      = Column(String(20), default='pending')
    created_at  = Column(DateTime, default=datetime.utcnow)
    items       = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    coupon      = relationship('Coupon')

class OrderItem(Base):
    __tablename__ = 'order_items'
    id         = Column(Integer, primary_key=True, index=True)
    order_id   = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity   = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    order      = relationship('Order',   back_populates='items')
    product    = relationship('Product', back_populates='order_items')
