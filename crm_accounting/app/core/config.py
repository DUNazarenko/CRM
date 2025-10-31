import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # SQL Server (Windows Authentication)
    DB_SERVER: str = os.getenv("DB_SERVER", "localhost")
    DB_DRIVER: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")  # имя установленного драйвера
    TRUST_SERVER_CERTIFICATE: str = os.getenv("TRUST_SERVER_CERTIFICATE", "yes")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "crm_accounting")  # основная БД

    # Секреты / JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

settings = Settings()
