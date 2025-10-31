# app/managers/client_db_manager.py
import logging
from urllib.parse import quote_plus

import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.client_template import ClientBase  # metadata клиентской БД
# Важно: чтобы metadata знала все модели:
from app.models.client_template import (  # noqa: F401
    ClientUser,
    Client,
    ClientUserClientAccess,
    DigitalSignature,
    CompanySettings,
    ReportTemplate,
    ReportPeriod,
    Report,
    ClientReportHistory,
    CalendarHandbook,
    CalendarEvent,
    Organization,
)

logger = logging.getLogger(__name__)


def _build_client_url(database_name: str) -> str:
    """
    SQLAlchemy URL для клиентской БД с Windows Auth.
    """
    server = settings.DB_SERVER
    driver = quote_plus(settings.DB_DRIVER)
    trust = "yes" if str(settings.TRUST_SERVER_CERTIFICATE).lower() in ("1", "true", "yes") else "no"
    return (
        f"mssql+pyodbc://@{server}/{database_name}"
        f"?driver={driver}&trusted_connection=yes&TrustServerCertificate={trust}"
    )


def _pyodbc_master_conn():
    """
    Прямое подключение pyodbc к master с Windows Auth, чтобы выполнить CREATE DATABASE (если нужно).
    """
    driver = settings.DB_DRIVER
    server = settings.DB_SERVER
    trust = "yes" if str(settings.TRUST_SERVER_CERTIFICATE).lower() in ("1", "true", "yes") else "no"
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE=master;"
        f"Trusted_Connection=Yes;"
        f"TrustServerCertificate={'Yes' if trust=='yes' else 'No'};"
    )
    return pyodbc.connect(conn_str, autocommit=True)


class ClientDBManager:
    """
    Управление клиентскими БД: создание, подключение, сессии.
    """

    def create_client_database(self, client_org, database_name: str | None = None) -> str:
        """
        Создаёт БД клиента, если её нет, и накатывает структуру таблиц из ClientBase.metadata.
        Возвращает имя БД.
        """
        db_name = database_name or (client_org.database_name or f"client_{client_org.id}")
        logger.info(f"Проверка/создание клиентской БД: {db_name}")

        # 1) CREATE DATABASE [db_name] IF NOT EXISTS (через pyodbc в master)
        with _pyodbc_master_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DB_ID(?)", db_name)
            row = cur.fetchone()
            if row and row[0] is not None:
                logger.info(f"БД {db_name} уже существует")
            else:
                logger.info(f"Создаю БД {db_name}")
                cur.execute(f"CREATE DATABASE [{db_name}]")
                logger.info(f"БД {db_name} создана")

        # 2) Создание таблиц клиентской схемы
        url = _build_client_url(db_name)
        engine = create_engine(url, pool_pre_ping=True, future=True, fast_executemany=True)
        ClientBase.metadata.create_all(bind=engine, checkfirst=True)
        logger.info(f"Таблицы для БД {db_name} проверены/созданы")

        # 3) Опционально: начальные данные (например, CompanySettings по умолчанию)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
        with SessionLocal() as s:
            # если нет settings – создадим пустую запись
            from sqlalchemy import select
            if s.execute(select(CompanySettings).limit(1)).first() is None:
                s.add(CompanySettings(company_name=client_org.company_name or f"Клиент {client_org.id}"))
            # базовые справочники периодов – по желанию (оставлю пустым)
            s.commit()

        return db_name

    # ---------- вспомогательные методы ----------

    def get_engine(self, database_name: str):
        return create_engine(_build_client_url(database_name), pool_pre_ping=True, future=True, fast_executemany=True)

    def get_client_session(self, database_name: str):
        engine = self.get_engine(database_name)
        return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)()

# singleton
client_db_manager = ClientDBManager()
