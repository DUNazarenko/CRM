# app/services/client_auth_service.py
from sqlalchemy.orm import Session
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import ClientUser, Report, CalendarEvent, Client, DigitalSignature
from app.models.main_db import ClientOrganization
import hashlib
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class ClientAuthService:

    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширование пароля для клиентской БД"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверка пароля"""
        return ClientAuthService.hash_password(plain_password) == hashed_password

    @staticmethod
    def authenticate_client_user(database_name: str, login: str, password: str):
        """
        Аутентификация пользователя в клиентской БД.
        Возвращает объект пользователя из клиентской БД или None.
        """
        try:
            session = client_db_manager.get_client_session(database_name)
            user = session.query(ClientUser).filter(
                (ClientUser.email == login) | (ClientUser.login == login)
            ).first()
            if not user:
                return None
            if not ClientAuthService.verify_password(
                password,
                getattr(user, "hashed_password", "") or "",
            ):
                return None
            if hasattr(user, "is_active") and not user.is_active:
                return None
            return user
        except Exception as e:
            logger.error(f"Ошибка аутентификации в БД {database_name}: {str(e)}")
            return None

    @staticmethod
    def get_client_dashboard_data(database_name: str):
        """Получение данных для дашборда клиента"""
        try:
            session = client_db_manager.get_client_session(database_name)

            # Количество клиентов
            clients_count = session.query(Client).count()

            # Количество отчётов
            reports_count = session.query(Report).count()

            # Просроченные отчёты
            overdue_reports = (
                session.query(Report)
                .filter(Report.status == "просрочен")
                .count()
            )

            # Активные отчёты
            active_reports = (
                session.query(Report)
                .filter(Report.status.in_(["в работе", "подготовлен"]))
                .count()
            )

            # Новые клиенты за последнюю неделю
            week_ago = date.today() - timedelta(days=7)
            new_clients_count = session.query(Client).filter(
                Client.created_at >= week_ago
            ).count()

            # ЭЦП, срок действия которых истекает в ближайшие 30 дней
            expiring_signatures_count = session.query(DigitalSignature).filter(
                DigitalSignature.end_date >= date.today(),
                DigitalSignature.end_date <= (date.today() + timedelta(days=30)),
            ).count()

            # Количество событий в календаре на текущий месяц
            current_month_start = date.today().replace(day=1)
            current_month_end = (current_month_start.replace(month=current_month_start.month % 12 + 1, day=1)
                                 if current_month_start.month < 12
                                 else date(current_month_start.year + 1, 1, 1))

            calendar_events = session.query(CalendarEvent).filter(
                CalendarEvent.date >= current_month_start,
                CalendarEvent.date < current_month_end
            ).count()

            return {
                "clients_count": clients_count,
                "reports_count": reports_count,
                "overdue_reports": overdue_reports,
                "active_reports": active_reports,
                "new_clients_count": new_clients_count,
                "expiring_signatures_count": expiring_signatures_count,
                "calendar_events": calendar_events
            }

        except Exception as e:
            logger.error(f"Ошибка получения данных дашборда для БД {database_name}: {str(e)}")
            return {}
