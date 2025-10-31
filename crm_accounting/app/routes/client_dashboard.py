# app/routes/client_dashboard.py
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from calendar import monthrange
import logging

from app.core.database import get_main_db
from app.utils import templates
from app.utils.client_utils import get_client_company_settings, get_today_date
from app.models.main_db import ClientOrganization
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import CalendarHandbook, Client, Report, DigitalSignature

logger = logging.getLogger(__name__)
router = APIRouter()


# -------------------------------------------------------------
# Дашборд клиента
# -------------------------------------------------------------
@router.get("/client/{client_id}/dashboard", response_class=HTMLResponse)
async def client_dashboard(
    client_id: int,
    request: Request,
    db: Session = Depends(get_main_db)
):
    """
    Клиентский дашборд — показывает отчёты, календарь и количество истекающих ЭЦП.
    """
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")

    session = client_db_manager.get_client_session(org.database_name)
    try:
        reports = session.query(Report).order_by(Report.id.desc()).limit(10).all()
        calendar = session.query(CalendarHandbook).order_by(CalendarHandbook.id.desc()).limit(10).all()
        clients_count = session.query(Client).count()

        # --- Расчет количества истекающих ЭЦП ---
        today = datetime.utcnow()
        last_day = monthrange(today.year, today.month)[1]
        end_of_month = today.replace(day=last_day, hour=23, minute=59, second=59)
        threshold_end = end_of_month + timedelta(days=10)

        expiring_signatures_count = (
            session.query(DigitalSignature)
            .filter(DigitalSignature.end_date.isnot(None))
            .filter(DigitalSignature.end_date <= threshold_end)
            .count()
        )

    except Exception as e:
        logger.error(f"Ошибка загрузки данных дашборда клиента {client_id}: {e}")
        reports, calendar, clients_count, expiring_signatures_count = [], [], 0, 0
    finally:
        session.close()

    company_settings = get_client_company_settings(db, client_id)
    client = {"id": client_id, "name": org.company_name or "Клиент"}

    dashboard_data = {
        "clients_count": clients_count,
        "reports": reports,
        "calendar": calendar,
        "today": get_today_date(),
        "expiring_signatures_count": expiring_signatures_count,
    }

    return templates.TemplateResponse(
        "client/dashboard.html",
        {
            "request": request,
            "client_id": client_id,
            "client": client,
            "company_settings": company_settings,
            "dashboard_data": dashboard_data,
        },
    )


# -------------------------------------------------------------
# Страница истекающих ЭЦП
# -------------------------------------------------------------
@router.get("/client/{client_id}/expiring-signatures", response_class=HTMLResponse)
async def expiring_signatures_page(
    client_id: int,
    request: Request,
    db: Session = Depends(get_main_db)
):
    """
    Страница со списком клиентов, у которых ЭЦП истекают в текущем месяце (с учётом -10 дней).
    """
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")

    session = client_db_manager.get_client_session(org.database_name)
    try:
        today = datetime.utcnow()
        last_day = monthrange(today.year, today.month)[1]
        end_of_month = today.replace(day=last_day, hour=23, minute=59, second=59)
        threshold_date = end_of_month + timedelta(days=10)

        signatures = (
            session.query(DigitalSignature)
            .join(Client, DigitalSignature.client_id == Client.id)
            .filter(DigitalSignature.end_date.isnot(None))
            .filter(DigitalSignature.end_date <= threshold_date)
            .order_by(DigitalSignature.end_date.asc())
            .all()
        )

        expiring_clients = []
        for s in signatures:
            days_left = (s.end_date - today).days if s.end_date else None
            expiring_clients.append({
                "client_name": s.client.organization_name,
                "owner_name": s.owner_name,
                "end_date": s.end_date.strftime("%d.%m.%Y") if s.end_date else "—",
                "days_left": days_left,
            })

    except Exception as e:
        logger.error(f"Ошибка загрузки истекающих ЭЦП: {e}")
        expiring_clients = []
    finally:
        session.close()

    # ✅ Добавляем company_settings, чтобы избежать UndefinedError
    company_settings = get_client_company_settings(db, client_id)

    return templates.TemplateResponse(
        "client/expiring-signatures.html",  # путь к шаблону
        {
            "request": request,
            "client": org,
            "client_id": client_id,
            "expiring_clients": expiring_clients,
            "company_settings": company_settings,  # <== добавлено
        },
    )
