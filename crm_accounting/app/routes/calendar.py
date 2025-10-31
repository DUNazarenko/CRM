# app/routes/calendar.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging

from app.core.database import get_main_db
from app.utils import templates
from app.utils.client_utils import get_client_company_settings, get_today_date
from app.models.main_db import ClientOrganization
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import CalendarHandbook, Client, Report, ReportPeriod

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/client/{client_id}/calendar", response_class=HTMLResponse)
async def client_calendar_page(
    client_id: int,
    request: Request,
    db: Session = Depends(get_main_db),
):
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")

    session = client_db_manager.get_client_session(org.database_name)
    try:
        handbook = session.query(CalendarHandbook).all()
        reports = {r.id: r for r in session.query(Report).all()}
        try:
            periods = {p.id: p for p in session.query(ReportPeriod).all()}
        except Exception:
            periods = {}
        clients = {c.id: c for c in session.query(Client).all()}

        events = []
        for h in handbook:
            due = None
            for attr in ("due_date", "deadline_date", "next_due_date"):
                if hasattr(h, attr):
                    due = getattr(h, attr)
                    break
            events.append({
                "id": h.id,
                "client": clients.get(getattr(h, "client_id", None)),
                "report": reports.get(getattr(h, "report_id", None)),
                "period": periods.get(getattr(h, "period_id", None)),
                "due_date": due,
                "status": getattr(h, "status", None),
                "comment": getattr(h, "comment", None),
            })
    finally:
        session.close()

    company_settings = get_client_company_settings(db, client_id)
    client = {"id": client_id, "name": org.company_name or "Клиент"}

    return templates.TemplateResponse(
        "client/calendar.html",
        {
            "request": request,
            "client_id": client_id,
            "client": client,                   # ✅
            "events": events,
            "company_settings": company_settings,
            "today": get_today_date(),
        },
    )
