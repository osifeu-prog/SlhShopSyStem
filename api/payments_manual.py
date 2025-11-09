import os
import uuid

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
    Accepts: order_id + image file (bank transfer receipt) from the bot.
    Saves the file into uploaded_proofs/, and updates public."orders":
      - payment_proof_url = file path
      - status = 'waiting_verification'
      - updated_at = NOW()
    """

    # basic validation
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # unique file name
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # save file to disk
    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    # logical URL for internal reference
    file_url = f"/{UPLOAD_DIR}/{filename}"

    # check order exists
    row = db.execute(
        text('SELECT id FROM public."orders" WHERE id = :oid'),
        {"oid": order_id},
    ).fetchone()

    if not row:
        # cleanup if order not found
        try:
            os.remove(filepath)
        except OSError:
            pass
        raise HTTPException(status_code=404, detail="Order not found")

    # update order with proof + status
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
