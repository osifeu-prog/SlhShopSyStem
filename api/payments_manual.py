import os
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, Form, HTTPException, Depends
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from .db import get_db
from .models import OrderModel

router = APIRouter(prefix="/payments", tags=["payments"])

UPLOAD_DIR = "uploaded_proofs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-proof")
async def upload_payment_proof(
    order_id: str = Form(...),
    file: UploadFile = None,
    db: Session = Depends(get_db),
):
    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ext = os.path.splitext(file.filename or "")[1]
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(await file.read())

    file_url = f"/uploaded_proofs/{filename}"

    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.payment_proof_url = file_url
    order.status = "waiting_verification"
    order.updated_at = datetime.utcnow()
    db.commit()

    return JSONResponse({"ok": True, "order_id": order_id, "proof_url": file_url})


@router.post("/approve/{order_id}")
async def approve_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "paid"
    order.updated_at = datetime.utcnow()
    db.commit()

    return {"ok": True, "message": "Order approved"}
