# app/routes/client_settings.py
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
import logging

from app.core.database import get_main_db
from app.utils import templates
from app.models.main_db import ClientOrganization
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import CompanySettings, Organization

logger = logging.getLogger(__name__)
router = APIRouter()


# ------------------------------------------------------
# Настройки клиента (страница)
# ------------------------------------------------------
@router.get("/client/{client_id}/settings", response_class=HTMLResponse)
async def client_settings_page(
    client_id: int,
    request: Request,
    db: Session = Depends(get_main_db)
):
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")

    session = client_db_manager.get_client_session(org.database_name)
    try:
        company_settings = session.query(CompanySettings).first()
        organizations = session.query(Organization).order_by(Organization.id.desc()).all()
    finally:
        session.close()

    return templates.TemplateResponse(
        "client/settings.html",
        {
            "request": request,
            "client": org,
            "client_id": client_id,
            "company_settings": company_settings,
            "organizations": organizations,
        },
    )


# ------------------------------------------------------
# ✅ Создание новой организации
# ------------------------------------------------------
@router.post("/client/{client_id}/settings/organizations")
async def create_client_organization(
    client_id: int,
    full_name: str = Form(...),
    short_name: str = Form(...),
    inn: str = Form(None),
    kpp: str = Form(None),
    ogrn: str = Form(None),
    legal_address: str = Form(None),
    actual_address: str = Form(None),
    bank_name: str = Form(None),
    bik: str = Form(None),
    payment_account: str = Form(None),
    correspondent_account: str = Form(None),
    db: Session = Depends(get_main_db),
):
    """
    Создаёт организацию в клиентской БД.
    """
    client_org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not client_org or not client_org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")

    session = client_db_manager.get_client_session(client_org.database_name)
    try:
        new_org = Organization(
            full_name=full_name.strip(),
            short_name=short_name.strip(),
            inn=inn.strip() if inn else None,
            kpp=kpp.strip() if kpp else None,
            ogrn=ogrn.strip() if ogrn else None,
            legal_address=legal_address.strip() if legal_address else None,
            actual_address=actual_address.strip() if actual_address else None,
            bank_name=bank_name.strip() if bank_name else None,
            bik=bik.strip() if bik else None,
            payment_account=payment_account.strip() if payment_account else None,
            correspondent_account=correspondent_account.strip() if correspondent_account else None,
        )
        session.add(new_org)
        session.commit()
        logger.info(f"✅ Организация '{short_name}' создана для клиента {client_id}")
        return JSONResponse(
            {"success": True, "message": f"Организация '{short_name}' успешно создана"}, status_code=201
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка создания организации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания организации: {e}")
    finally:
        session.close()


# ------------------------------------------------------
# Удаление организации
# ------------------------------------------------------
@router.delete("/client/{client_id}/settings/organizations/{org_id}")
async def delete_client_organization(
    client_id: int,
    org_id: int,
    db: Session = Depends(get_main_db),
):
    """
    Удаляет организацию из клиентской БД.
    """
    client_org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not client_org or not client_org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")

    session = client_db_manager.get_client_session(client_org.database_name)
    try:
        org = session.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Организация не найдена")

        session.delete(org)
        session.commit()
        logger.info(f"❌ Организация {org_id} удалена у клиента {client_id}")
        return JSONResponse({"success": True, "message": "Организация успешно удалена"})
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка удаления организации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления организации: {e}")
    finally:
        session.close()
