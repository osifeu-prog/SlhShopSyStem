

from __future__ import annotations

from api.demo_order_mock import router as demo_order_router
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import SessionLocal, engine
from .models import (
    Base,
    User as UserModel,
    Shop as ShopModel,
    Item as ItemModel,
    Order as OrderModel,
)
from .payments_manual import router as payments_router

# ×œ×™×¦×•×¨ ×ک×‘×œ×گ×•×ھ ×گ×‌ ×œ×گ ×§×™×™×‍×•×ھ
Base.metadata.create_all(bind=engine)


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# ×ھ×œ×•×ھ ×œ-SQLAlchemy Session ×œ×›×œ ×‘×§×©×”
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================
# Pydantic Models
# =============================


class UserCreateFromTelegram(BaseModel):
    telegram_id: int
    telegram_username: Optional[str] = None
    display_name: Optional[str] = None
    referral_code: Optional[str] = None


class User(BaseModel):
    id: str
    telegram_id: int
    telegram_username: Optional[str] = None
    display_name: Optional[str] = None
    bnb_address: Optional[str] = None
    ton_address: Optional[str] = None
    referrer_id: Optional[str] = None
    created_at: str
    updated_at: str


class ShopCreate(BaseModel):
    owner_user_id: str
    title: str
    description: Optional[str] = None
    shop_type: Literal["basic", "premium", "distributor"] = "basic"


class Shop(BaseModel):
    id: str
    owner_user_id: str
    title: str
    description: Optional[str] = None
    slug: str
    shop_type: str
    status: str
    referral_code: str
    created_at: str
    updated_at: str


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    price_slh: Optional[str] = None
    price_bnb: Optional[str] = None
    price_nis: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Item(BaseModel):
    id: str
    shop_id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    price_slh: Optional[str] = None
    price_bnb: Optional[str] = None
    price_nis: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class OrderCreate(BaseModel):
    buyer_user_id: str
    shop_id: str
    item_id: str
    payment_method: Literal["slh", "bnb"] = "slh"


class PaymentInstructions(BaseModel):
    to_address: str
    amount: str
    symbol: str
    chain_id: int


class Order(BaseModel):
    id: str
    buyer_user_id: str
    shop_id: str
    item_id: str
    amount_slh: Optional[str] = None
    amount_bnb: Optional[str] = None
    status: str
    tx_hash: Optional[str] = None
    created_at: str
    updated_at: str


class OrderWithPayment(BaseModel):
    order: Order
    payment_instructions: PaymentInstructions


# demo payment config
BSC_CHAIN_ID = 56
SLH_TOKEN_ADDRESS = "0xACb0A09414CEA1C879c67bB7A877E4e19480f022"
SLH_SYMBOL = "SLH"

# =============================
# FastAPI App
# =============================

app = FastAPI(
    title="SLH Shop Core API",
    version="0.1.0",
    description="Core API for SLH Shop-based ecosystem (with SQLite DB).",
)

# ---- Static files for uploaded_proofs ----
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = BASE_DIR.parent / "uploaded_proofs"

if UPLOAD_ROOT.exists():
    app.mount(
        "/uploaded_proofs",
        StaticFiles(directory=str(UPLOAD_ROOT)),
        name="uploaded_proofs",
    )

# ---- Include payments router (/payments/upload-proof) ----
app.include_router(payments_router)


# =============================
# Health & Meta
# =============================


@app.get("/healthz")
def healthz() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/meta")
def meta() -> Dict[str, Any]:
    return {
        "name": "SLH Shop Core",
        "version": "0.1.0",
        "chain_id": BSC_CHAIN_ID,
        "token_address": SLH_TOKEN_ADDRESS,
        "symbol": SLH_SYMBOL,
        "db": "sqlite",
    }


# =============================
# Users
# =============================


@app.post("/users/telegram-sync", response_model=User)
def users_telegram_sync(
    payload: UserCreateFromTelegram,
    db: Session = Depends(get_db),
) -> User:
    user = db.query(UserModel).filter(
        UserModel.telegram_id == payload.telegram_id
    ).first()

    if user:
        user.telegram_username = payload.telegram_username or user.telegram_username
        user.display_name = payload.display_name or user.display_name
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user = UserModel(
            telegram_id=payload.telegram_id,
            telegram_username=payload.telegram_username,
            display_name=payload.display_name,
            bnb_address=None,
            ton_address=None,
            referrer_id=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return User(
        id=user.id,
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
        display_name=user.display_name,
        bnb_address=user.bnb_address,
        ton_address=user.ton_address,
        referrer_id=user.referrer_id,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: str, db: Session = Depends(get_db)) -> User:
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=user.id,
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
        display_name=user.display_name,
        bnb_address=user.bnb_address,
        ton_address=user.ton_address,
        referrer_id=user.referrer_id,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@app.get("/users/{user_id}/shops", response_model=List[Shop])
def get_user_shops(user_id: str, db: Session = Depends(get_db)) -> List[Shop]:
    shops = db.query(ShopModel).filter(ShopModel.owner_user_id == user_id).all()
    return [
        Shop(
            id=s.id,
            owner_user_id=s.owner_user_id,
            title=s.title,
            description=s.description,
            slug=s.slug,
            shop_type=s.shop_type,
            status=s.status,
            referral_code=s.referral_code,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in shops
    ]


@app.get("/users/{user_id}/orders", response_model=List[Order])
def get_user_orders(user_id: str, db: Session = Depends(get_db)) -> List[Order]:
    orders = db.query(OrderModel).filter(OrderModel.buyer_user_id == user_id).all()
    return [
        Order(
            id=o.id,
            buyer_user_id=o.buyer_user_id,
            shop_id=o.shop_id,
            item_id=o.item_id,
            amount_slh=o.amount_slh,
            amount_bnb=o.amount_bnb,
            status=o.status,
            tx_hash=o.tx_hash,
            created_at=o.created_at.isoformat(),
            updated_at=o.updated_at.isoformat(),
        )
        for o in orders
    ]


# =============================
# Shops
# =============================


@app.post("/shops", response_model=Shop)
def create_shop(payload: ShopCreate, db: Session = Depends(get_db)) -> Shop:
    owner = db.query(UserModel).filter(UserModel.id == payload.owner_user_id).first()
    if not owner:
        raise HTTPException(status_code=400, detail="Owner user not found")

    base = payload.title.replace(" ", "-")[:12] or "shop"
    suffix = datetime.utcnow().strftime("%H%M%S")
    slug = f"{base}-{suffix}"
    referral_code = slug.split("-")[-1]

    shop = ShopModel(
        owner_user_id=payload.owner_user_id,
        title=payload.title,
        description=payload.description,
        slug=slug,
        shop_type=payload.shop_type,
        status="active",
        referral_code=referral_code,
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)

    return Shop(
        id=shop.id,
        owner_user_id=shop.owner_user_id,
        title=shop.title,
        description=shop.description,
        slug=shop.slug,
        shop_type=shop.shop_type,
        status=shop.status,
        referral_code=shop.referral_code,
        created_at=shop.created_at.isoformat(),
        updated_at=shop.updated_at.isoformat(),
    )


@app.get("/shops/{shop_id}", response_model=Shop)
def get_shop(shop_id: str, db: Session = Depends(get_db)) -> Shop:
    shop = db.query(ShopModel).filter(ShopModel.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    return Shop(
        id=shop.id,
        owner_user_id=shop.owner_user_id,
        title=shop.title,
        description=shop.description,
        slug=shop.slug,
        shop_type=shop.shop_type,
        status=shop.status,
        referral_code=shop.referral_code,
        created_at=shop.created_at.isoformat(),
        updated_at=shop.updated_at.isoformat(),
    )


@app.get("/shops/by-owner/{owner_user_id}", response_model=List[Shop])
def get_shops_by_owner(
    owner_user_id: str,
    db: Session = Depends(get_db),
) -> List[Shop]:
    shops = db.query(ShopModel).filter(ShopModel.owner_user_id == owner_user_id).all()
    return [
        Shop(
            id=s.id,
            owner_user_id=s.owner_user_id,
            title=s.title,
            description=s.description,
            slug=s.slug,
            shop_type=s.shop_type,
            status=s.status,
            referral_code=s.referral_code,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in shops
    ]


@app.get("/shops/by-referral/{referral_code}", response_model=Shop)
def get_shop_by_referral(
    referral_code: str,
    db: Session = Depends(get_db),
) -> Shop:
    shop = (
        db.query(ShopModel)
        .filter(ShopModel.referral_code == referral_code)
        .first()
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found for referral code")

    return Shop(
        id=shop.id,
        owner_user_id=shop.owner_user_id,
        title=shop.title,
        description=shop.description,
        slug=shop.slug,
        shop_type=shop.shop_type,
        status=shop.status,
        referral_code=shop.referral_code,
        created_at=shop.created_at.isoformat(),
        updated_at=shop.updated_at.isoformat(),
    )


# =============================
# Items
# =============================


@app.post("/shops/{shop_id}/items", response_model=Item)
def create_item(
    shop_id: str,
    payload: ItemCreate,
    db: Session = Depends(get_db),
) -> Item:
    shop = db.query(ShopModel).filter(ShopModel.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    metadata_json = json.dumps(payload.metadata or {})

    item = ItemModel(
        shop_id=shop_id,
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
        price_slh=payload.price_slh,
        price_bnb=payload.price_bnb,
        price_nis=payload.price_nis,
        metadata_json=metadata_json,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return Item(
        id=item.id,
        shop_id=item.shop_id,
        name=item.name,
        description=item.description,
        image_url=item.image_url,
        price_slh=item.price_slh,
        price_bnb=item.price_bnb,
        price_nis=item.price_nis,
        metadata=json.loads(item.metadata_json or "{}"),
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


@app.get("/shops/{shop_id}/items", response_model=List[Item])
def list_shop_items(shop_id: str, db: Session = Depends(get_db)) -> List[Item]:
    shop = db.query(ShopModel).filter(ShopModel.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    items = db.query(ItemModel).filter(ItemModel.shop_id == shop_id).all()

    return [
        Item(
            id=i.id,
            shop_id=i.shop_id,
            name=i.name,
            description=i.description,
            image_url=i.image_url,
            price_slh=i.price_slh,
            price_bnb=i.price_bnb,
            price_nis=i.price_nis,
            metadata=json.loads(i.metadata_json or "{}"),
            created_at=i.created_at.isoformat(),
            updated_at=i.updated_at.isoformat(),
        )
        for i in items
    ]


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: str, db: Session = Depends(get_db)) -> Item:
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return Item(
        id=item.id,
        shop_id=item.shop_id,
        name=item.name,
        description=item.description,
        image_url=item.image_url,
        price_slh=item.price_slh,
        price_bnb=item.price_bnb,
        price_nis=item.price_nis,
        metadata=json.loads(item.metadata_json or "{}"),
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


# =============================
# Orders
# =============================


@app.post("/orders", response_model=OrderWithPayment)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> OrderWithPayment:
    buyer = db.query(UserModel).filter(UserModel.id == payload.buyer_user_id).first()
    if not buyer:
        raise HTTPException(status_code=400, detail="Buyer user not found")

    shop = db.query(ShopModel).filter(ShopModel.id == payload.shop_id).first()
    if not shop:
        raise HTTPException(status_code=400, detail="Shop not found")

    item = db.query(ItemModel).filter(ItemModel.id == payload.item_id).first()
    if not item:
        raise HTTPException(status_code=400, detail="Item not found")

    amount_slh: Optional[str] = None
    amount_bnb: Optional[str] = None
    symbol: str

    if payload.payment_method == "slh":
        if not item.price_slh:
            raise HTTPException(status_code=400, detail="Item has no SLH price")
        amount_slh = item.price_slh
        symbol = SLH_SYMBOL
    else:
        if not item.price_bnb:
            raise HTTPException(status_code=400, detail="Item has no BNB price")
        amount_bnb = item.price_bnb
        symbol = "BNB"

    order = OrderModel(
        buyer_user_id=buyer.id,
        shop_id=shop.id,
        item_id=item.id,
        amount_slh=amount_slh,
        amount_bnb=amount_bnb,
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    payment = PaymentInstructions(
        to_address=SLH_TOKEN_ADDRESS
        if payload.payment_method == "slh"
        else "0xYourBNBMerchantAddress",
        amount=amount_slh or amount_bnb or "0",
        symbol=symbol,
        chain_id=BSC_CHAIN_ID,
    )

    return OrderWithPayment(
        order=Order(
            id=order.id,
            buyer_user_id=order.buyer_user_id,
            shop_id=order.shop_id,
            item_id=order.item_id,
            amount_slh=order.amount_slh,
            amount_bnb=order.amount_bnb,
            status=order.status,
            tx_hash=order.tx_hash,
            created_at=order.created_at.isoformat(),
            updated_at=order.updated_at.isoformat(),
        ),
        payment_instructions=payment,
    )


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str, db: Session = Depends(get_db)) -> Order:
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return Order(
        id=order.id,
        buyer_user_id=order.buyer_user_id,
        shop_id=order.shop_id,
        item_id=order.item_id,
        amount_slh=order.amount_slh,
        amount_bnb=order.amount_bnb,
        status=order.status,
        tx_hash=order.tx_hash,
        created_at=order.created_at.isoformat(),
        updated_at=order.updated_at.isoformat(),
    )

from .demo_order_bot_manual import router as demo_order_bot_router
app.include_router(demo_order_bot_router)


from .demo_order_mock import router as demo_order_router








app.include_router(demo_order_router)
