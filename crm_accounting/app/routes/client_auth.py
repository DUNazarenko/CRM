# app/routes/client_auth.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_main_db
from app.services.user_service import UserService
from pydantic import BaseModel
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter()

class ClientLogin(BaseModel):
    login: str
    password: str

@router.post("/client/login")
async def client_login(login_data: ClientLogin, db: Session = Depends(get_main_db)):
    """Обработка входа клиента через API"""
    try:
        logger.info(f"Попытка входа с логином: {login_data.login}")
        
        # Используем новый сервис аутентификации
        user = UserService.authenticate_client_user(db, login_data.login, login_data.password)
        
        if not user:
            logger.warning(f"Пользователь с логином '{login_data.login}' не найден или неверный пароль")
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        logger.info(f"Успешная аутентификация пользователя: {user.full_name}")
        
        # Проверяем, что клиентская организация активна и имеет БД
        if not user.client_organization.is_active:
            logger.warning(f"Клиентская организация не активна для пользователя {user.id}")
            raise HTTPException(status_code=400, detail="Ваш аккаунт деактивирован")
        
        if not user.client_organization.database_name:
            logger.warning(f"У клиентской организации {user.client_organization.id} нет созданной БД")
            raise HTTPException(status_code=400, detail="База данных для вашего аккаунта еще не создана. Обратитесь к администратору.")
        
        # Возвращаем успешный ответ с URL для редиректа
        return JSONResponse({
            "success": True,
            "message": "Успешный вход",
            "redirect_url": f"/client/{user.client_organization.id}/dashboard",
            "client_id": user.client_organization.id,
            "user_name": user.full_name
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка входа клиента: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")