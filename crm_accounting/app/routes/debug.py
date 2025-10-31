# app/routes/debug.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_main_db
from app.models.main_db import ClientOrganization
from app.core.security import verify_password
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/client/{login}")
async def debug_client(login: str, password: str, db: Session = Depends(get_main_db)):
    """Временный маршрут для диагностики входа клиента"""
    try:
        logger.info(f"Диагностика входа для логина: {login}")
        
        # Ищем клиента по логину
        client = db.query(ClientOrganization).filter(
            ClientOrganization.login == login
        ).first()
        
        if not client:
            return {
                "found": False, 
                "message": "Клиент не найден",
                "available_logins": [c.login for c in db.query(ClientOrganization).all()]
            }
        
        # Проверяем пароль
        password_match = verify_password(password, client.hashed_password)
        
        result = {
            "found": True,
            "client_id": client.id,
            "login": client.login,
            "is_active": client.is_active,
            "has_database": bool(client.database_name),
            "database_name": client.database_name,
            "password_match": password_match,
            "stored_hash_length": len(client.hashed_password) if client.hashed_password else 0,
            "contact_person": client.contact_person,
            "email": client.email
        }
        
        logger.info(f"Результат диагностики: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Ошибка диагностики: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка диагностики: {str(e)}")