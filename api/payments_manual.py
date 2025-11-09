import os
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
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
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    מקבל order_id + קובץ (צילום אישור תשלום) מהבוט,
    שומר את הקובץ בתיקייה uploaded_proofs,
    ומעדכן את השורה בטבלת orders:
      - payment_proof_url = הנתיב לקובץ
      - status = 'waiting_verification'
      - updated_at = NOW()
    """

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="לא התקבל קובץ")

    # קובץ ייחודי
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # שמירת הקובץ בדיסק
    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    # URL לוגי שנחזיר (היום לשימוש פנימי בלבד)
    file_url = f"/{UPLOAD_DIR}/{filename}"

    # בדיקה שההזמנה קיימת
    row = db.execute(
        text('SELECT id FROM public."orders" WHERE id = :oid'),
        {"oid": order_id},
    ).fetchone()

    if not row:
        # אם אין הזמנה  נמחק את הקובץ שלא יהיה זבל
        try:
            os.remove(filepath)
        except OSError:
            pass
        raise HTTPException(status_code=404, detail="Order not found")

    # עדכון ההזמנה
    db.execute(
        text(
            '''
            UPDATE public."orders"
            SET
                payment_proof_url = :url,
                status = :status,
                updated_at = NOW()
            WHERE id = :oid
            '''
        ),
        {
            "url": file_url,
            "status": "waiting_verification",
            "oid": order_id,
        },
    )
    db.commit()

    return JSONResponse(
        {
            "ok": True,
            "order_id": order_id,
            "proof_url": file_url,
        }
    )
