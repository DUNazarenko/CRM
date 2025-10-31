import logging
from app.managers.client_db_manager import client_db_manager
from app.core.database import get_main_db
from app.models.main_db import ClientOrganization
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def create_database_for_client(client_id: int, db: Session):
    """Автоматическое создание БД для клиента"""
    try:
        client = db.query(ClientOrganization).filter(ClientOrganization.id == client_id).first()
        if not client:
            logger.error(f"Клиент с ID {client_id} не найден")
            return False
        
        if client.database_name:
            logger.info(f"БД для клиента {client_id} уже создана: {client.database_name}")
            return True
        
        # Создаем БД для клиента
        database_name = client_db_manager.create_client_database(str(client.id), client.login)
        
        # Обновляем запись клиента
        client.database_name = database_name
        db.commit()
        
        logger.info(f"Автоматически создана БД для клиента {client_id}: {database_name}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка автоматического создания БД для клиента {client_id}: {str(e)}")
        db.rollback()
        return False