from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_main_db
from app.models.main_db import ClientOrganization

router = APIRouter()

@router.get("/{client_id}/info")
async def get_client_info(client_id: int, db: Session = Depends(get_main_db)):
    client = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client