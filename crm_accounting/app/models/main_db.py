# app/models/main_db.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    permissions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ClientOrganization(Base):
    __tablename__ = "client_organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    # Основные поля
    database_name = Column(String(100))
    company_name = Column(String(255))
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Устаревшие поля (оставляем для обратной совместимости)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    contact_person = Column(String(255), nullable=True)
    login = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=True)

    # Связь с пользователями
    users = relationship("ClientUser", back_populates="client_organization")

    def to_dict(self):
        """Метод для преобразования объекта в словарь"""
        # Получаем основного пользователя (владельца)
        owner_user = None
        if self.users:
            owner_user = next((u for u in self.users if u.profile and u.profile.name == "Владелец"), self.users[0])
        
        return {
            "id": self.id,
            "database_name": self.database_name,
            "company_name": self.company_name,
            "notes": self.notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "users_count": len(self.users) if self.users else 0,
            # Для обратной совместимости
            "email": owner_user.email if owner_user else self.email,
            "phone": owner_user.phone if owner_user else self.phone,
            "contact_person": owner_user.full_name if owner_user else self.contact_person,
            "login": owner_user.login if owner_user else self.login
        }

class ClientUser(Base):
    __tablename__ = "client_users"
    
    id = Column(Integer, primary_key=True, index=True)
    client_organization_id = Column(Integer, ForeignKey('client_organizations.id'), nullable=False)
    email = Column(String(255), nullable=False)
    login = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    profile_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    client_organization = relationship("ClientOrganization", back_populates="users")
    profile = relationship("UserProfile")
    
    def to_dict(self):
        return {
            "id": self.id,
            "client_organization_id": self.client_organization_id,
            "company_name": self.client_organization.company_name if self.client_organization else None,
            "email": self.email,
            "login": self.login,
            "full_name": self.full_name,
            "phone": self.phone,
            "profile_id": self.profile_id,
            "profile_name": self.profile.name if self.profile else None,
            "is_active": self.is_active,
            "database_name": self.client_organization.database_name if self.client_organization else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }