# app/routes/client_organizations.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging

from app.core.database import get_main_db
from app.utils import templates
from app.utils.client_utils import get_client_company_settings
from app.models.main_db import ClientOrganization
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import Organization  # проверь, есть ли такая модель

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/client/{client_id}/organizations", response_class=HTMLResponse)
async def client_organizations_page(
    client_id: int,
    request: Request,
    db: Session = Depends(get_main_db),
):
    """
    Страница организаций внутри клиентского портала.
    """
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")

    session = client_db_manager.get_client_session(org.database_name)
    try:
        organizations = []
        # Если в шаблоне используется таблица организаций, загружаем их из client DB
        if "Organization" in session.bind.dialect.get_table_names(session.bind):
            organizations = session.query(Organization).order_by(Organization.id.desc()).all()
    except Exception as e:
        logger.error(f"Ошибка при загрузке организаций клиента {client_id}: {e}")
    finally:
        session.close()

    company_settings = get_client_company_settings(db, client_id)
    client = {"id": client_id, "name": org.company_name or "Клиент"}

    return templates.TemplateResponse(
        "client/organizations.html",  # шаблон должен существовать
        {
            "request": request,
            "client_id": client_id,
            "client": client,
            "company_settings": company_settings,
            "organizations": organizations,
        },
    )
