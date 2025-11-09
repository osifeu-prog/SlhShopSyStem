import os
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, Form, HTTPException, Depends
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from .db import get_db

router = APIRouter(prefix="/payments", tags=["payments"])

UPLOAD_DIR = "uploaded_proofs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-proof")
async def upload_payment_proof(
    order_id: str = Form(...),
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # שמירת הקובץ
    ext = os.path.splitext(file.filename or "")[1]
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    file_url = f"/{UPLOAD_DIR}/{filename}"

    # עדכון ההזמנה ישירות בטבלת orders
    result = db.execute(
        text(
            """
            UPDATE orders
            SET payment_proof_url = :file_url,
                status = 'waiting_verification',
                updated_at = NOW()
            WHERE id = :order_id
            RETURNING id
            """
        ),
        {"file_url": file_url, "order_id": order_id},
    ).fetchone()

    if result is None:
        raise HTTPException(status_code=404, detail="Order not found")

    db.commit()

    return JSONResponse({"ok": True, "order_id": order_id, "proof_url": file_url})


@router.post("/approve/{order_id}")
async def approve_order(order_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text(
            """
            UPDATE orders
            SET status = 'paid',
                updated_at = NOW()
            WHERE id = :order_id
            RETURNING id
            """
        ),
        {"order_id": order_id},
    ).fetchone()

    if result is None:
        raise HTTPException(status_code=404, detail="Order not found")

    db.commit()
    return {"ok": True, "message": "Order approved"}
