# app/routes/client_users.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging

from app.core.database import get_main_db
from app.utils import templates
from app.utils.client_utils import get_client_company_settings
from app.models.main_db import ClientOrganization
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import ClientUser as ClientUserTemplate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/client/{client_id}/users", response_class=HTMLResponse)
async def client_users_page(
    client_id: int,
    request: Request,
    db: Session = Depends(get_main_db),
):
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")

    session = client_db_manager.get_client_session(org.database_name)
    try:
        users = session.query(ClientUserTemplate).order_by(ClientUserTemplate.id.desc()).all()
    finally:
        session.close()

    company_settings = get_client_company_settings(db, client_id)
    client = {"id": client_id, "name": org.company_name or "Клиент"}

    return templates.TemplateResponse(
        "client/users.html",
        {
            "request": request,
            "client_id": client_id,
            "client": client,                   # ✅
            "users": users,
            "company_settings": company_settings,
        },
    )
