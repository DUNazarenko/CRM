# app/routes/client_reports.py

import logging
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_main_db
from app.utils import templates
from app.utils.client_utils import get_client_company_settings
from app.models.main_db import ClientOrganization
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import (
    Client,
    ReportTemplate,
    ClientReport,
    ClientReportHistory,
    ReportPeriod  # ДОБАВЛЕНО: импорт ReportPeriod
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_client_org_or_404(db: Session, client_id: int) -> ClientOrganization:
    """Проверка существования клиента и его базы."""
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        raise HTTPException(status_code=404, detail="База клиента не найдена")
    return org


# === Справочник шаблонов отчётов ===
@router.get("/client/{client_id}/reports", response_class=HTMLResponse)
async def client_reports_page(
    client_id: int,
    request: Request,
    db: Session = Depends(get_main_db),
):
    """Отображение списка шаблонов отчётов клиента."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        reports = session.query(ReportTemplate).order_by(ReportTemplate.id.desc()).all()
    finally:
        session.close()

    company_settings = get_client_company_settings(db, client_id)
    client = {"id": client_id, "name": org.company_name or "Клиент"}

    return templates.TemplateResponse(
        "client/reports.html",
        {
            "request": request,
            "client_id": client_id,
            "client": client,
            "reports": reports,
            "company_settings": company_settings,
        },
    )


# === Создание нового шаблона отчёта ===
@router.post("/client/{client_id}/reports")
async def create_report(
    client_id: int,
    db: Session = Depends(get_main_db),
    full_name: str = Form(...),
    short_name: str = Form(...),
    description: str = Form(None),
):
    """Создание нового шаблона отчёта."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        new_template = ReportTemplate(
            full_name=full_name.strip(),
            short_name=short_name.strip(),
            description=(description or "").strip() or None,
            is_active=True,
        )
        session.add(new_template)
        session.commit()
        session.refresh(new_template)
        logger.info(f"Создан шаблон отчёта '{new_template.short_name}' для клиента {client_id}")
    except Exception as e:
        session.rollback()
        logger.exception("Ошибка при создании шаблона отчёта")
        raise HTTPException(status_code=500, detail="Ошибка при создании отчёта") from e
    finally:
        session.close()

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "id": new_template.id,
            "full_name": new_template.full_name,
            "short_name": new_template.short_name,
        },
    )


# === JSON: закреплённые отчёты ===
@router.get("/client/{client_id}/assigned-reports.json")
async def assigned_reports_json(client_id: int, db: Session = Depends(get_main_db)):
    """Возвращает список отчётов, закреплённых за клиентом (с периодами из client_report_history)."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        inner_client = session.query(Client).first()
        if not inner_client:
            return JSONResponse([])

        links = (
            session.query(ClientReport)
            .join(ReportTemplate, ClientReport.template_id == ReportTemplate.id)
            .filter(ClientReport.client_id == inner_client.id, ClientReport.is_active == True)
            .all()
        )

        result = []
        for link in links:
            # периоды берём из client_report_history
            periods = (
                session.query(ClientReportHistory)
                .filter(ClientReportHistory.client_report_id == link.id)
                .order_by(ClientReportHistory.start_date.desc())
                .all()
            )

            result.append({
                "id": link.id,
                "template_id": link.template_id,
                "report_name": link.template.full_name,
                "short_name": link.template.short_name,
                "periods": [
                    {
                        "id": p.id,
                        "start_date": p.start_date.isoformat() if p.start_date else None,
                        "end_date": p.end_date.isoformat() if p.end_date else None,
                    }
                    for p in periods
                ],
            })
    finally:
        session.close()
    return JSONResponse(result)


# === JSON: доступные отчёты ===
@router.get("/client/{client_id}/available-reports.json")
async def available_reports_json(client_id: int, db: Session = Depends(get_main_db)):
    """Возвращает шаблоны отчётов, которые ещё не закреплены за клиентом."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        inner_client = session.query(Client).first()
        if not inner_client:
            return JSONResponse([])

        assigned = {r.template_id for r in session.query(ClientReport).filter(ClientReport.client_id == inner_client.id)}
        available = (
            session.query(ReportTemplate)
            .filter(ReportTemplate.is_active == True)
            .filter(~ReportTemplate.id.in_(assigned))
            .order_by(ReportTemplate.full_name)
            .all()
        )
        data = [{"template_id": r.id, "full_name": r.full_name, "short_name": r.short_name} for r in available]
    finally:
        session.close()
    return JSONResponse(data)


# === Добавить отчёт клиенту ===
@router.post("/client/{client_id}/assigned-reports")
async def assign_report(client_id: int, template_id: int = Form(...), db: Session = Depends(get_main_db)):
    """Добавляет отчёт (шаблон) клиенту."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        inner_client = session.query(Client).first()
        if not inner_client:
            raise HTTPException(400, "В базе клиента отсутствует запись в таблице clients")

        tpl = session.query(ReportTemplate).filter_by(id=template_id).first()
        if not tpl:
            raise HTTPException(404, "Шаблон отчёта не найден")

        exists = session.query(ClientReport).filter_by(client_id=inner_client.id, template_id=template_id).first()
        if exists:
            raise HTTPException(400, "Этот отчёт уже добавлен клиенту")

        link = ClientReport(client_id=inner_client.id, template_id=template_id, is_active=True)
        session.add(link)
        session.commit()
    finally:
        session.close()
    return JSONResponse({"message": "Отчёт добавлен"})


# === Добавление периода (client_report_history) ===
@router.post("/client/{client_id}/assigned-reports/{template_id}/periods")
async def add_period(
    client_id: int,
    template_id: int,
    start_date: str = Form(...),
    end_date: str = Form(None),
    db: Session = Depends(get_main_db),
):
    """Добавление нового периода (DATE) в client_report_history."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        inner_client = session.query(Client).first()
        if not inner_client:
            raise HTTPException(400, "В базе клиента отсутствует запись в таблице clients")

        client_report = session.query(ClientReport).filter_by(
            client_id=inner_client.id, template_id=template_id
        ).first()
        if not client_report:
            raise HTTPException(404, "Связь client_report не найдена")

        try:
            start_d = date.fromisoformat(start_date)
            end_d = date.fromisoformat(end_date) if end_date else None
        except ValueError:
            raise HTTPException(400, "Неверный формат даты. Используйте ГГГГ-ММ-ДД")

        new_period = ClientReportHistory(
            client_report_id=client_report.id,
            start_date=start_d,
            end_date=end_d,
            created_at=datetime.utcnow()
        )
        session.add(new_period)
        session.commit()
    finally:
        session.close()
    return JSONResponse({"message": "Период добавлен"})


# === Обновление периода (client_report_history) ===
@router.put("/client/{client_id}/assigned-reports/history/{history_id}")
async def update_period(
    client_id: int,
    history_id: int,
    start_date: str = Form(...),
    end_date: str = Form(None),
    db: Session = Depends(get_main_db),
):
    """
    Редактирование существующего периода (client_report_history).
    Принимает start_date/end_date в формате YYYY-MM-DD. Колонки в БД — DATE.
    """
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        inner_client = session.query(Client).first()
        if not inner_client:
            raise HTTPException(400, "В базе клиента отсутствует запись в таблице clients")

        history = (
            session.query(ClientReportHistory)
            .join(ClientReport, ClientReportHistory.client_report_id == ClientReport.id)
            .filter(
                ClientReportHistory.id == history_id,
                ClientReport.client_id == inner_client.id,
            )
            .first()
        )
        if not history:
            raise HTTPException(404, "Период не найден")

        try:
            start_d = date.fromisoformat(start_date)
            end_d = date.fromisoformat(end_date) if end_date else None
        except ValueError:
            raise HTTPException(400, "Неверный формат даты. Используйте ГГГГ-ММ-ДД")

        history.start_date = start_d
        history.end_date = end_d
        session.commit()
    finally:
        session.close()

    return JSONResponse({"message": "Период обновлён"})


# === Удалить отчёт (если нет периодов) ===
@router.delete("/client/{client_id}/assigned-reports/{template_id}")
async def delete_report(client_id: int, template_id: int, db: Session = Depends(get_main_db)):
    """Удаляет отчёт, если у него нет периодов (в client_report_history)."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        inner_client = session.query(Client).first()
        if not inner_client:
            raise HTTPException(400, "В базе клиента отсутствует запись в таблице clients")

        has_periods = (
            session.query(ClientReportHistory)
            .join(ClientReport, ClientReportHistory.client_report_id == ClientReport.id)
            .filter(ClientReport.template_id == template_id, ClientReport.client_id == inner_client.id)
            .first()
        )
        if has_periods:
            raise HTTPException(400, "Нельзя удалить отчёт — есть периоды")

        link = session.query(ClientReport).filter_by(client_id=inner_client.id, template_id=template_id).first()
        if not link:
            raise HTTPException(404, "Отчёт не найден")

        session.delete(link)
        session.commit()
    finally:
        session.close()
    return JSONResponse({"message": "Отчёт удалён"})


# === Удаление периода (client_report_history) ===
@router.delete("/client/{client_id}/assigned-reports/history/{history_id}")
async def delete_period(client_id: int, history_id: int, db: Session = Depends(get_main_db)):
    """
    Удаляет конкретный период (строку в client_report_history), проверяя принадлежность текущему клиенту.
    """
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        inner_client = session.query(Client).first()
        if not inner_client:
            raise HTTPException(status_code=400, detail="В базе клиента отсутствует запись в таблице clients")

        history = (
            session.query(ClientReportHistory)
            .join(ClientReport, ClientReportHistory.client_report_id == ClientReport.id)
            .filter(
                ClientReportHistory.id == history_id,
                ClientReport.client_id == inner_client.id
            )
            .first()
        )
        if not history:
            raise HTTPException(status_code=404, detail="Период не найден")

        session.delete(history)
        session.commit()
    finally:
        session.close()

    return JSONResponse({"message": "Период удалён"})


# === Детальная страница отчета ===
@router.get("/client/{client_id}/reports/{report_id}", response_class=HTMLResponse)
async def report_detail_page(
    client_id: int,
    report_id: int,
    request: Request,
    db: Session = Depends(get_main_db),
):
    """Детальная страница отчета."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    try:
        report = session.query(ReportTemplate).filter(ReportTemplate.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Отчет не найден")
        
        # Загружаем периоды отчета из таблицы report_periods
        periods = session.query(ReportPeriod).filter(ReportPeriod.report_id == report_id).order_by(ReportPeriod.year.desc(), ReportPeriod.due_date).all()
        
    finally:
        session.close()

    company_settings = get_client_company_settings(db, client_id)
    client = {"id": client_id, "name": org.company_name or "Клиент"}

    return templates.TemplateResponse(
        "client/report_card.html",
        {
            "request": request,
            "client_id": client_id,
            "client": client,
            "report": report,
            "company_settings": company_settings,
            "today": datetime.now(),
            "periods": periods,
        },
    )


# === Добавление периода для отчета (в таблицу report_periods) ===
@router.post("/client/{client_id}/reports/{report_id}/periods")
async def add_report_period(
    client_id: int,
    report_id: int,
    period: str = Form(...),
    year: int = Form(...),
    due_date: str = Form(...),
    db: Session = Depends(get_main_db),
):
    """Добавление периода сдачи для отчета в таблицу report_periods."""
    org = _get_client_org_or_404(db, client_id)
    session = client_db_manager.get_client_session(org.database_name)
    
    try:
        # Проверяем существование отчета
        report = session.query(ReportTemplate).filter(ReportTemplate.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Отчет не найден")
        
        # Создаем новый период - ИСПРАВЛЕНО: используем report_id вместо report_template_id
        new_period = ReportPeriod(
            report_id=report_id,  # ИСПРАВЛЕНО: поле называется report_id, а не report_template_id
            period=period,
            year=year,
            due_date=datetime.strptime(due_date, '%Y-%m-%d')  # ИСПРАВЛЕНО: поле due_date типа DateTime
        )
        
        session.add(new_period)
        session.commit()
        session.refresh(new_period)
        
        logger.info(f"Добавлен период для отчета {report_id} клиента {client_id}")
        
    except Exception as e:
        session.rollback()
        logger.exception("Ошибка при добавлении периода отчета")
        raise HTTPException(status_code=500, detail="Ошибка при добавлении периода") from e
    finally:
        session.close()

    return JSONResponse({"message": "Период успешно добавлен"})