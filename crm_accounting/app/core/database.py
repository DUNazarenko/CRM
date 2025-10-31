# app/core/database.py
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------- базовый класс для моделей основной БД ----------
Base = declarative_base()


# ---------- helpers ----------

def _build_main_mssql_url() -> str:
    """
    Формирует URL для SQLAlchemy с Windows Authentication:
    mssql+pyodbc://@SERVER/DATABASE?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes
    """
    server = settings.DB_SERVER
    database = settings.DATABASE_NAME
    driver = quote_plus(settings.DB_DRIVER)
    trust = "yes" if str(settings.TRUST_SERVER_CERTIFICATE).lower() in ("1", "true", "yes") else "no"

    return (
        f"mssql+pyodbc://@{server}/{database}"
        f"?driver={driver}&trusted_connection=yes&TrustServerCertificate={trust}"
    )


# ---------- engine / session ----------

MAIN_DB_URL = _build_main_mssql_url()
_main_engine = create_engine(
    MAIN_DB_URL,
    pool_pre_ping=True,
    future=True,
    fast_executemany=True
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_main_engine,
    future=True
)


def get_main_db():
    """
    Dependency для получения сессии основной БД в FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- optional: ensure tables (если где-то вызывается) ----------

def check_and_create_tables(base_metadata=None):
    """
    Проверяет и создаёт таблицы основной БД, если они отсутствуют.
    """
    if base_metadata is None:
        base_metadata = Base.metadata
    insp = inspect(_main_engine)
    base_metadata.create_all(_main_engine, checkfirst=True)
    logger.info("Проверка/создание таблиц основной БД завершена")
