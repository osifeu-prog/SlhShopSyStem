from datetime import datetime
import uuid

from sqlalchemy import BigInteger, Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from .db import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def now_dt():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    telegram_username = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    bnb_address = Column(String, nullable=True)
    ton_address = Column(String, nullable=True)
    referrer_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=now_dt, nullable=False)
    updated_at = Column(DateTime, default=now_dt, nullable=False)

    shops = relationship("Shop", back_populates="owner")
    orders = relationship("Order", back_populates="buyer")


class Shop(Base):
    __tablename__ = "shops"

    id = Column(String, primary_key=True, default=gen_uuid)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    shop_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    referral_code = Column(String, unique=True, index=True, nullable=False)

    created_at = Column(DateTime, default=now_dt, nullable=False)
    updated_at = Column(DateTime, default=now_dt, nullable=False)

    owner = relationship("User", back_populates="shops")
    items = relationship("Item", back_populates="shop")
    orders = relationship("Order", back_populates="shop")


class Item(Base):
    __tablename__ = "items"

    id = Column(String, primary_key=True, default=gen_uuid)
    shop_id = Column(String, ForeignKey("shops.id"), nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)

    price_slh = Column(String, nullable=True)
    price_bnb = Column(String, nullable=True)
    price_nis = Column(Float, nullable=True)

    metadata_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=now_dt, nullable=False)
    updated_at = Column(DateTime, default=now_dt, nullable=False)

    shop = relationship("Shop", back_populates="items")
    orders = relationship("Order", back_populates="item")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=gen_uuid)
    buyer_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    shop_id = Column(String, ForeignKey("shops.id"), nullable=False)
    item_id = Column(String, ForeignKey("items.id"), nullable=False)

    amount_slh = Column(String, nullable=True)
    amount_bnb = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    tx_hash = Column(String, nullable=True)

    created_at = Column(DateTime, default=now_dt, nullable=False)
    updated_at = Column(DateTime, default=now_dt, nullable=False)

    buyer = relationship("User", back_populates="orders")
    shop = relationship("Shop", back_populates="orders")
    item = relationship("Item", back_populates="orders")


