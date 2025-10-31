# app/utils/password_checker.py
import logging
from app.core.security import verify_password
from app.models.main_db import ClientOrganization
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def debug_password_check(db: Session, login: str, password: str):
    """Функция для отладки проверки пароля"""
    client = db.query(ClientOrganization).filter(
        ClientOrganization.login == login
    ).first()
    
    if not client:
        return {"found": False, "message": "Клиент не найден"}
    
    result = {
        "found": True,
        "client_id": client.id,
        "login": client.login,
        "is_active": client.is_active,
        "has_database": bool(client.database_name),
        "password_match": verify_password(password, client.hashed_password),
        "stored_hash": client.hashed_password
    }
    
    logger.info(f"Debug password check: {result}")
    return result