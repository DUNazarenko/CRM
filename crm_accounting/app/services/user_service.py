# app/services/user_service.py
import logging
from sqlalchemy.orm import Session
from app.models.main_db import ClientUser, ClientOrganization, UserProfile
from app.core.security import get_password_hash, verify_password
from app.managers.client_db_manager import client_db_manager
from app.models.client_template import ClientUser as ClientUserTemplate

logger = logging.getLogger(__name__)


class UserService:
    """
    Сервис для управления клиентами и пользователями.
    """

    # ---------------------------------------------------------
    # 1️⃣ Создание клиентской организации + автосоздание БД
    # ---------------------------------------------------------
    @staticmethod
    def create_client_organization(db: Session, company_name: str, notes: str | None = None) -> ClientOrganization:
        try:
            client = ClientOrganization(company_name=company_name, notes=notes, is_active=True)
            db.add(client)
            db.commit()
            db.refresh(client)

            # Автоматическое создание клиентской БД
            db_name = f"client_{client.id}"
            created_name = client_db_manager.create_client_database(client, database_name=db_name)
            client.database_name = created_name
            db.commit()
            db.refresh(client)

            logger.info(f"Клиентская БД создана автоматически: {created_name}")
            return client
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка создания клиентской организации/БД: {e}")
            raise

    # ---------------------------------------------------------
    # 2️⃣ Создание пользователя клиента (основная + клиентская БД)
    # ---------------------------------------------------------
    @staticmethod
    def create_client_user(
        db: Session,
        client_organization_id: int,
        email: str,
        login: str,
        password: str,
        full_name: str,
        phone: str | None = None
    ):
        """
        Создаёт пользователя клиента в основной БД и дублирует его в клиентской БД.
        Назначает профиль "Владелец", если это первый пользователь клиента.
        """
        try:
            owner_profile = (
                db.query(UserProfile)
                .filter(UserProfile.name.in_(["Владелец", "Owner"]))
                .first()
            )
            if not owner_profile:
                owner_profile = UserProfile(name="Владелец", description="Профиль владельца клиента")
                db.add(owner_profile)
                db.commit()
                db.refresh(owner_profile)

            hashed = get_password_hash(password)
            user = ClientUser(
                client_organization_id=client_organization_id,
                email=email,
                login=login,
                hashed_password=hashed,
                full_name=full_name,
                phone=phone,
                profile_id=owner_profile.id,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            client_org = db.query(ClientOrganization).filter(ClientOrganization.id == client_organization_id).first()
            if not client_org or not client_org.database_name:
                raise ValueError("Не найдена клиентская БД для зеркалирования пользователя")

            session = client_db_manager.get_client_session(client_org.database_name)
            try:
                tpl_user = ClientUserTemplate(
                    main_user_id=user.id,
                    full_name=full_name,
                    email=email,
                    login=login,
                    hashed_password=user.hashed_password,
                    is_active=True,
                )
                session.add(tpl_user)
                session.commit()
            finally:
                session.close()

            logger.info(f"Пользователь {login} создан успешно (организация ID={client_organization_id})")
            return user

        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка создания пользователя клиента: {e}")
            raise

    # ---------------------------------------------------------
    # 3️⃣ Аутентификация пользователя клиента (вход)
    # ---------------------------------------------------------
    @staticmethod
    def authenticate_client_user(db: Session, login: str, password: str):
        """
        Проверяет логин и пароль пользователя клиента.
        Возвращает объект пользователя при успешной проверке.
        """
        try:
            user = db.query(ClientUser).filter(ClientUser.login == login).first()
            if not user:
                logger.warning(f"Попытка входа: пользователь '{login}' не найден.")
                return None

            if not verify_password(password, user.hashed_password):
                logger.warning(f"Попытка входа: неверный пароль для '{login}'.")
                return None

            if not user.is_active:
                logger.warning(f"Попытка входа: пользователь '{login}' неактивен.")
                return None

            logger.info(f"Пользователь '{login}' успешно аутентифицирован.")
            return user

        except Exception as e:
            logger.error(f"Ошибка аутентификации пользователя '{login}': {e}")
            raise
