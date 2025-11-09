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
    """
    מקבל צילום אישור תשלום מהבוט, שומר אותו בשרת,
    ומעדכן את ההזמנה בטבלת orders:
    - payment_proof_url  נתיב הקובץ
    - status  waiting_verification
    """
    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ext = os.path.splitext(file.filename or "")[1]
    if not ext:
        ext = ".jpg"

    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    file_url = f"/{UPLOAD_DIR}/{filename}"

    now = datetime.utcnow()
    result = db.execute(
        text(
            'UPDATE public."orders" '
            'SET payment_proof_url = :file_url, status = :status, updated_at = :updated_at '
            'WHERE id = :order_id'
        ),
        {
            "file_url": file_url,
            "status": "waiting_verification",
            "updated_at": now,
            "order_id": order_id,
        },
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Order not found")

    db.commit()

    return JSONResponse(
        {"ok": True, "order_id": order_id, "proof_url": file_url}
    )


@router.post("/approve/{order_id}")
async def approve_order(order_id: str, db: Session = Depends(get_db)):
    """
    מסמן הזמנה כ-paid (אפשר לקרוא ידנית מ-Postman או מה-API).
    """
    now = datetime.utcnow()
    result = db.execute(
        text(
            'UPDATE public."orders" '
            'SET status = :status, updated_at = :updated_at '
            'WHERE id = :order_id'
        ),
        {
            "status": "paid",
            "updated_at": now,
            "order_id": order_id,
        },
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Order not found")

    db.commit()
    return {"ok": True, "message": "Order approved"}
