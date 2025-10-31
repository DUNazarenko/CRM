# app/routes/client_clients.py
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import case
import logging

from app.core.database import get_main_db
from app.models.main_db import ClientOrganization
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import Client, CompanySettings, DigitalSignature
from app.utils import templates

logger = logging.getLogger(__name__)
router = APIRouter()


# ------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------
def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _get_client_org_or_404(db: Session, client_id: int) -> ClientOrganization:
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")
    return org


# ------------------------------------------------------
# 📄 Список клиентов
# ------------------------------------------------------
@router.get("/client/{client_id}/clients", response_class=HTMLResponse)
async def client_clients_page(client_id: int, request: Request, db: Session = Depends(get_main_db)):
    client_org = _get_client_org_or_404(db, client_id)

    session = client_db_manager.get_client_session(client_org.database_name)
    try:
        clients = session.query(Client).order_by(Client.id.desc()).all()
        company_settings = session.query(CompanySettings).first()
        sig_rows = session.query(DigitalSignature).all()
        signatures = {s.client_id: s for s in sig_rows}

        clients_with_signatures = [
            {"client": c, "signature": signatures.get(c.id)} for c in clients
        ]
    finally:
        session.close()

    return templates.TemplateResponse(
        "client/clients.html",
        {
            "request": request,
            "client_id": client_id,
            "client": client_org,
            "clients_with_signatures": clients_with_signatures,
            "company_settings": company_settings,
        },
    )


# ------------------------------------------------------
# 🧾 Создание клиента
# ------------------------------------------------------
@router.post("/client/{client_id}/clients")
async def create_client_for_tenant(
    client_id: int,
    legal_form: str = Form(...),
    inn: str = Form(None),
    ogrn: str = Form(None),
    organization_name: str = Form(...),
    tax_system: str = Form(...),
    is_employer: bool = Form(False),
    db: Session = Depends(get_main_db),
):
    client_org = _get_client_org_or_404(db, client_id)

    session = client_db_manager.get_client_session(client_org.database_name)
    try:
        new_client = Client(
            legal_form=legal_form.strip(),
            inn=inn.strip() if inn else None,
            ogrn=ogrn.strip() if ogrn else None,
            organization_name=organization_name.strip(),
            tax_system=tax_system.strip(),
            is_employer=is_employer,
            is_active=True,
        )
        session.add(new_client)
        session.commit()
        logger.info(f"✅ Клиент '{organization_name}' создан в БД клиента {client_id}")
        return JSONResponse({"success": True, "message": f"Клиент '{organization_name}' успешно создан."})
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка создания клиента: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания клиента: {e}")
    finally:
        session.close()


# ------------------------------------------------------
# 🪪 Карточка клиента — список ЭЦП
# ------------------------------------------------------
@router.get("/client/{client_id}/clients/{client_inner_id}", response_class=HTMLResponse)
async def client_detail_page(client_id: int, client_inner_id: int, request: Request, db: Session = Depends(get_main_db)):
    client_org = _get_client_org_or_404(db, client_id)

    session = client_db_manager.get_client_session(client_org.database_name)
    try:
        client_obj = session.query(Client).filter(Client.id == client_inner_id).first()
        if not client_obj:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        # ✅ Загружаем все ЭЦП клиента (списком)
        signatures = (
            session.query(DigitalSignature)
            .filter(DigitalSignature.client_id == client_inner_id)
            .order_by(
                case((DigitalSignature.end_date.is_(None), 1), else_=0),
                DigitalSignature.end_date.desc()
            )
            .all()
        )

        company_settings = session.query(CompanySettings).first()
    finally:
        session.close()

    # ✅ Добавляем текущую дату в контекст шаблона
    today = datetime.utcnow()

    return templates.TemplateResponse(
        "client/client_card.html",
        {
            "request": request,
            "client_id": client_id,
            "client_data": client_obj,
            "client_db": client_obj,
            "signatures": signatures,  # теперь список
            "client": client_org,
            "company_settings": company_settings,
            "today": today,  # ✅ добавлено для шаблона
        },
    )


# ------------------------------------------------------
# 🔏 Добавление ЭЦП
# ------------------------------------------------------
@router.post("/client/{client_id}/clients/{client_inner_id}/signatures")
async def add_client_signature(
    client_id: int,
    client_inner_id: int,
    owner_name: str = Form(...),
    certificate_number: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    is_active: bool = Form(True),
    db: Session = Depends(get_main_db),
):
    client_org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(client_org.database_name)

    try:
        if not session.query(Client.id).filter(Client.id == client_inner_id).first():
            raise HTTPException(status_code=404, detail="Клиент не найден")

        ds = DigitalSignature(
            client_id=client_inner_id,
            owner_name=owner_name.strip(),
            certificate_number=certificate_number.strip() if certificate_number else None,
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
            is_active=is_active,
        )
        session.add(ds)
        session.commit()
        logger.info(f"✅ ЭЦП '{owner_name}' добавлена для клиента {client_inner_id}")
        return RedirectResponse(url=f"/client/{client_id}/clients/{client_inner_id}", status_code=303)
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка добавления ЭЦП: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка добавления ЭЦП: {e}")
    finally:
        session.close()
