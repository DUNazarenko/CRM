# app/utils/client_utils.py
import logging
from types import SimpleNamespace
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.main_db import ClientOrganization
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import CompanySettings

logger = logging.getLogger(__name__)


def get_client_company_settings(db: Session, client_id: int) -> SimpleNamespace:
    """
    Возвращает объект с полями company_name и logo для шапки клиентского портала.
    Гарантирует наличие полей, даже если запись в клиентской БД отсутствует.
    """
    org = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
    if not org or not org.database_name:
        return SimpleNamespace(company_name="Моя компания", logo=None)

    session = client_db_manager.get_client_session(org.database_name)
    try:
        cs = session.query(CompanySettings).first()
        if not cs:
            cs = CompanySettings(company_name=org.company_name or "Моя компания")
            session.add(cs)
            session.commit()
            session.refresh(cs)

        company_name = getattr(cs, "company_name", None) or "Моя компания"
        logo = getattr(cs, "logo", None) if hasattr(cs, "logo") else None

        return SimpleNamespace(company_name=company_name, logo=logo)

    except Exception as e:
        logger.error(f"Ошибка получения настроек компании для клиента {client_id}: {e}")
        return SimpleNamespace(company_name="Моя компания", logo=None)
    finally:
        session.close()


def get_today_date() -> str:
    """
    Возвращает сегодняшнюю дату в формате YYYY-MM-DD.
    Используется для отображения текущего дня в дашборде и календаре.
    """
    try:
        return datetime.now().strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"Ошибка получения текущей даты: {e}")
        return "1970-01-01"
