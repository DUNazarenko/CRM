from sqlalchemy.orm import Session
from app.models.main_db import User
from app.core.security import verify_password, get_password_hash, create_access_token
from datetime import timedelta
from app.core.config import settings

class AuthService:
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str):
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            return False
        return user
    
    @staticmethod
    def create_user(db: Session, email: str, password: str, full_name: str, is_superuser: bool = False):
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_superuser=is_superuser
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def create_access_token_for_user(user: User):
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )