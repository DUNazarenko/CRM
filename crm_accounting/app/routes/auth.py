# app/routes/auth.py
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import logging

from app.core.database import get_main_db
from app.services.user_service import UserService
from app.utils import templates

logger = logging.getLogger(__name__)

# API-роутер (остаётся под префиксом /api/auth)
router = APIRouter()

# Публичный роутер (БЕЗ префикса) — для страниц /login, /register
public_router = APIRouter()


# ===========================
# ПУБЛИЧНЫЕ СТРАНИЦЫ: /login, /register
# ===========================

@public_router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    """
    Страница входа (если у тебя уже есть шаблон, он подцепится; если нет — сделай упрощённый).
    """
    # Поддержка существующего шаблона, либо покажем минимальную заглушку
    try:
        return templates.TemplateResponse("auth/login.html", {"request": request})
    except Exception:
        return HTMLResponse(
            """
            <html><body>
            <h2>Вход</h2>
            <form action="/api/auth/login" method="post">
              <div><input type="text" name="login" placeholder="Логин" required></div>
              <div><input type="password" name="password" placeholder="Пароль" required></div>
              <div><button type="submit">Войти</button></div>
            </form>
            <p><a href="/register">Регистрация в CRM</a></p>
            </body></html>
            """,
            status_code=200
        )


@public_router.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    """
    Страница регистрации клиента. Должна вызываться с кнопки «Регистрация в CRM» на странице входа.
    """
    try:
        return templates.TemplateResponse("auth/register.html", {"request": request})
    except Exception:
        # Минимальная форма-заглушка с корректными name полей
        return HTMLResponse(
            """
            <html><body>
            <h2>Регистрация в CRM</h2>
            <form action="/register" method="post">
              <div><input type="text" name="company_name" placeholder="Название организации" required></div>
              <div><input type="text" name="contact_person" placeholder="Контактное лицо"></div>
              <div><input type="email" name="email" placeholder="Email"></div>
              <div><input type="text" name="phone" placeholder="Телефон"></div>
              <div><input type="text" name="login" placeholder="Логин владельца" required></div>
              <div><input type="password" name="password" placeholder="Пароль владельца" required></div>
              <div><input type="text" name="notes" placeholder="Примечание"></div>
              <div><button type="submit">Зарегистрироваться</button></div>
            </form>
            </body></html>
            """,
            status_code=200
        )


@public_router.post("/register", include_in_schema=False)
async def register_submit(
    request: Request,
    company_name: str = Form(...),
    contact_person: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    login: str = Form(...),
    password: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_main_db),
):
    """
    Обработка отправки формы регистрации:
    1) создаёт клиента в основной БД,
    2) автоматически создаёт клиентскую БД client_{id},
    3) создаёт пользователя-владельца (в основной и клиентской БД),
    4) редиректит на /login.
    """
    try:
        # 1) Создаём клиентскую организацию (автосоздание БД внутри)
        client_org = UserService.create_client_organization(
            db=db,
            company_name=company_name,
            notes=notes
        )

        # 2) Создаём владельца (основная + зеркалирование в клиентскую БД)
        UserService.create_client_user(
            db=db,
            client_organization_id=client_org.id,
            email=email,
            login=login,
            password=password,
            full_name=contact_person or login,
            phone=phone
        )

        logger.info(f"✅ Регистрация клиента завершена: {company_name} (DB={client_org.database_name})")

        # после регистрации — на страницу входа
        return RedirectResponse(url="/login", status_code=303)

    except Exception as e:
        logger.error(f"Ошибка при регистрации клиента: {e}")
        # Показать ошибку на форме (если есть шаблон). Если нет — текст.
        try:
            return templates.TemplateResponse(
                "auth/register.html",
                {"request": request, "error": str(e)},
                status_code=400
            )
        except Exception:
            return HTMLResponse(f"Ошибка регистрации: {str(e)}", status_code=400)


# ===========================
# ПРИМЕРЫ API (могут уже быть в проекте)
# ===========================

@router.post("/login")
async def api_login(
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_main_db)
):
    """
    Пример API-входа (если используется).
    """
    # Реализацию оставляю как заглушку — она у тебя может быть в другом сервисе
    if not login or not password:
        raise HTTPException(status_code=400, detail="Укажите логин и пароль")

    return JSONResponse({"success": True})
