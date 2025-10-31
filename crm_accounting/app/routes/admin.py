# app/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
import logging

from app.core.database import get_main_db
from app.models.main_db import ClientOrganization, ClientUser
from app.managers.client_db_manager import client_db_manager
from app.services.user_service import UserService
from app.utils import templates

logger = logging.getLogger(__name__)
router = APIRouter()


# ------------------------------------------------------
# (Опционально) HTML-страница админ-панели
# ------------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Возвращает HTML-шаблон админ-панели (если заходите на /api/admin/dashboard)."""
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})


# ------------------------------------------------------
# Список клиентов (JSON)
# ------------------------------------------------------
@router.get("/clients")
async def list_clients(
    db: Session = Depends(get_main_db),
    query: str | None = None,
    status: str | None = None
):
    """
    Возвращает список клиентов с e-mail, телефоном (из таблицы client_users) и статусом БД.
    """
    try:
        q = db.query(ClientOrganization)
        if query:
            q = q.filter(ClientOrganization.company_name.ilike(f"%{query}%"))

        orgs = q.order_by(ClientOrganization.id.desc()).all()
        logger.info(f"📋 Загружено клиентов: {len(orgs)}")

        result = []
        for org in orgs:
            has_db = bool(org.database_name)
            if status == "has_db" and not has_db:
                continue
            if status == "no_db" and has_db:
                continue

            # Берем первого пользователя-«владельца» из client_users (основная БД)
            client_user = (
                db.query(ClientUser)
                .filter(ClientUser.client_organization_id == org.id)
                .order_by(ClientUser.id.asc())
                .first()
            )

            email = getattr(client_user, "email", None) if client_user else None
            phone = getattr(client_user, "phone", None) if client_user else None

            result.append({
                "id": org.id,
                "company_name": org.company_name or "—",
                "email": email or "—",
                "phone": phone or "—",
                "profile_name": "Владелец",
                "database_name": org.database_name or "Не создана",
                "is_active": True,
                "client_organization_id": org.id
            })

        return result
    except Exception as e:
        logger.error(f"Ошибка загрузки клиентов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения списка клиентов")


# ------------------------------------------------------
# ✅ Регистрация нового клиента (из формы на index.html)
# ------------------------------------------------------
@router.post("/clients")
async def create_client_organization(
    data: dict = Body(...),
    db: Session = Depends(get_main_db)
):
    """
    Регистрирует клиента: создаёт ClientOrganization, создает пользователя-владельца
    в client_users и (по флагу) создаёт клиентскую БД.

    Ожидаемый payload (см. index.html -> handleRegister()):
    {
        "email": "...",           # обязательно
        "phone": "...",           # обязательно
        "contact_person": "...",  # обязательно (ФИО)
        "login": "...",           # обязательно
        "password": "...",        # обязательно
        "company_name": "...",    # опционально
        "create_database": true   # опционально
    }
    """
    try:
        email = (data.get("email") or "").strip()
        phone = (data.get("phone") or "").strip()
        contact_person = (data.get("contact_person") or "").strip()
        login = (data.get("login") or "").strip()
        password = (data.get("password") or "").strip()
        company_name = (data.get("company_name") or "").strip()
        create_db_flag = bool(data.get("create_database", False))

        # Бэкенд-валидация
        if not email:
            raise HTTPException(status_code=400, detail="Не указан email.")
        if not phone:
            raise HTTPException(status_code=400, detail="Не указан телефон.")
        if not contact_person:
            raise HTTPException(status_code=400, detail="Не указано контактное лицо.")
        if not login or not password:
            raise HTTPException(status_code=400, detail="Не указан логин или пароль.")

        # 1) Создаём запись клиента (ClientOrganization) в основной БД
        client_org = UserService.create_client_organization(
            db=db,
            company_name=company_name or contact_person,  # если нет имени компании — используем ФИО
            notes=None
        )

        # 2) Создаём пользователя-владельца в основной БД (client_users)
        UserService.create_client_user(
            db=db,
            client_organization_id=client_org.id,
            email=email,
            login=login,
            password=password,
            full_name=contact_person or login,
            phone=phone
        )

        # 3) По флагу создаём клиентскую БД (client_{id})
        created_db_name = None
        if create_db_flag:
            created_db_name = client_db_manager.create_client_database(
                client_org, database_name=client_org.database_name or f"client_{client_org.id}"
            )
            client_org.database_name = created_db_name
            db.commit()

        logger.info(
            f"✅ Клиент зарегистрирован: id={client_org.id}, "
            f"company='{client_org.company_name}', db='{client_org.database_name}'"
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Клиент успешно зарегистрирован.",
                "client_id": client_org.id,
                "database_name": created_db_name or client_org.database_name
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка регистрации клиента: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка регистрации клиента: {e}")


# ------------------------------------------------------
# Создание БД клиента вручную (из админки)
# ------------------------------------------------------
@router.post("/clients/{client_id}/create-database")
async def create_database_for_client(client_id: int, db: Session = Depends(get_main_db)):
    """Создаёт клиентскую базу данных для существующего клиента."""
    client = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    try:
        created = client_db_manager.create_client_database(
            client, database_name=client.database_name or f"client_{client.id}"
        )
        client.database_name = created
        db.commit()
        return {"success": True, "message": f"База {created} успешно создана"}
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка создания БД: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания БД: {e}")


# ------------------------------------------------------
# Удаление клиента
# ------------------------------------------------------
@router.delete("/clients/{client_id}")
async def delete_client(client_id: int, db: Session = Depends(get_main_db)):
    """Удаляет клиента из основной БД (ClientOrganization + каскад, если настроен)."""
    client = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    db.delete(client)
    db.commit()
    return {"success": True, "message": f"Клиент {client.company_name} удалён"}
