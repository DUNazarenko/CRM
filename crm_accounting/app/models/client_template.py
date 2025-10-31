# app/models/client_template.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text
)
from sqlalchemy.orm import relationship, declarative_base

ClientBase = declarative_base()


# ===========================================================
# 1️⃣ Пользователи клиента
# ===========================================================
class ClientUser(ClientBase):
    __tablename__ = "client_users"

    id = Column(Integer, primary_key=True, index=True)
    main_user_id = Column(Integer, nullable=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    login = Column(String(255), nullable=False)
    profile_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    accesses = relationship(
        "ClientUserClientAccess",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ClientUser(id={self.id}, login='{self.login}', email='{self.email}')>"


# ===========================================================
# 2️⃣ Клиенты (контрагенты / организации)
# ===========================================================
class Client(ClientBase):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    legal_form = Column(String(100), nullable=False)
    inn = Column(String(12), nullable=True)
    ogrn = Column(String(13), nullable=True)
    organization_name = Column(Text, nullable=False)
    tax_system = Column(String(100), nullable=False)
    is_employer = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Client(id={self.id}, organization_name='{self.organization_name}')>"


# ===========================================================
# 3️⃣ Права пользователей к клиентам
# ===========================================================
class ClientUserClientAccess(ClientBase):
    __tablename__ = "client_user_client_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("client_users.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    can_view_calendar = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("ClientUser", back_populates="accesses")
    client = relationship("Client")

    def __repr__(self):
        return (
            f"<ClientUserClientAccess(user_id={self.user_id}, "
            f"client_id={self.client_id}, can_view_calendar={self.can_view_calendar})>"
        )


# ===========================================================
# 4️⃣ Электронные подписи
# ===========================================================
class DigitalSignature(ClientBase):
    __tablename__ = "digital_signatures"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    owner_name = Column(String(255), nullable=False)
    certificate_number = Column(String(255), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client")

    def __repr__(self):
        return f"<DigitalSignature(id={self.id}, owner='{self.owner_name}', end_date={self.end_date})>"


# ===========================================================
# 5️⃣ Настройки компании
# ===========================================================
class CompanySettings(ClientBase):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=True)
    logo_path = Column(String(512), nullable=True)
    currency = Column(String(16), nullable=True, default="RUB")
    timezone = Column(String(64), nullable=True, default="Europe/Moscow")
    fiscal_year_start = Column(String(16), nullable=True, default="01.01")
    report_email = Column(String(255), nullable=True)
    phone = Column(String(64), nullable=True)
    address = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CompanySettings(company_name='{self.company_name}')>"


# ===========================================================
# 6️⃣ Периоды отчётности
# ===========================================================
class ReportPeriod(ClientBase):
    __tablename__ = "report_periods"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("report_templates.id", ondelete="CASCADE"), nullable=True)
    period = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    report = relationship("ReportTemplate", back_populates="periods")

    def __repr__(self):
        return f"<ReportPeriod(id={self.id}, period='{self.period}', year={self.year})>"


# ===========================================================
# 7️⃣ Шаблоны отчётов (обновлённая версия)
# ===========================================================
class ReportTemplate(ClientBase):
    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True, index=True)
    short_name = Column(String(255), nullable=False)   # ранее name
    full_name = Column(String(500), nullable=False)    # новое поле
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    periods = relationship("ReportPeriod", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReportTemplate(id={self.id}, short_name='{self.short_name}')>"


# ===========================================================
# 8️⃣ Отчёты
# ===========================================================
class Report(ClientBase):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"))
    period_id = Column(Integer, ForeignKey("report_periods.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    created_by = Column(Integer, ForeignKey("client_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(64), nullable=True)
    file_path = Column(String(512), nullable=True)

    template = relationship("ReportTemplate")
    creator = relationship("ClientUser")
    client = relationship("Client")
    report_period = relationship("ReportPeriod")

    def __repr__(self):
        return f"<Report(id={self.id}, client_id={self.client_id}, status='{self.status}')>"

# ===========================================================
# 8️⃣ Связь клиентов с отчётами (упрощённая)
# ===========================================================
class ClientReport(ClientBase):
    __tablename__ = "client_reports"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('clients.id', ondelete="CASCADE"), nullable=False)
    template_id = Column(Integer, ForeignKey('report_templates.id', ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client")
    template = relationship("ReportTemplate")

    def __repr__(self):
        return f"<ClientReport(client_id={self.client_id}, template_id={self.template_id})>"


# ===========================================================
# 9️⃣ История отчётов
# ===========================================================
class ClientReportHistory(ClientBase):
    __tablename__ = "client_report_history"

    id = Column(Integer, primary_key=True, index=True)
    client_report_id = Column(Integer, ForeignKey('client_reports.id'))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    client_report = relationship("ClientReport", backref="history")

    def __repr__(self):
        return (
            f"<ClientReportHistory(client_report_id={self.client_report_id}, "
            f"start_date={self.start_date}, end_date={self.end_date})>"
)

# ===========================================================
# 🔟 Справочник календаря (CalendarHandbook)
# ===========================================================
class CalendarHandbook(ClientBase):
    __tablename__ = "calendar_handbook"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    default_day = Column(Integer, nullable=True)
    default_month = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CalendarHandbook(id={self.id}, name='{self.name}')>"


# ===========================================================
# 1️⃣1️⃣ События календаря
# ===========================================================
class CalendarEvent(ClientBase):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    handbook_id = Column(Integer, ForeignKey("calendar_handbook.id"), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client")
    handbook = relationship("CalendarHandbook")

    def __repr__(self):
        return f"<CalendarEvent(id={self.id}, title='{self.title}', date={self.date})>"


# ===========================================================
# 1️⃣2️⃣ Организации клиента
# ===========================================================
class Organization(ClientBase):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(500), nullable=False)
    short_name = Column(String(250), nullable=False)
    inn = Column(String(12))
    kpp = Column(String(9))
    ogrn = Column(String(13))
    legal_address = Column(Text)
    actual_address = Column(Text)
    bank_name = Column(String(255))
    bik = Column(String(9))
    payment_account = Column(String(20))
    correspondent_account = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
