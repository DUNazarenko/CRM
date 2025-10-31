# app/main.py
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.database import check_and_create_tables
from app.routes import (
    auth,
    admin,
    client_auth,
    client_dashboard,
    client_clients,
    client_reports,
    client_users,
    calendar,
    calendar_handbook,
    client_settings,
    client_organizations,
)
from app.utils import templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CRM Accounting", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Роутеры
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(client_auth.router, tags=["client_auth"])
app.include_router(client_dashboard.router, tags=["client_dashboard"])
app.include_router(client_clients.router, tags=["client_clients"])
app.include_router(client_reports.router, tags=["client_reports"])
app.include_router(client_users.router, tags=["client_users"])
app.include_router(calendar.router, tags=["calendar"])
app.include_router(calendar_handbook.router, tags=["calendar_handbook"])
app.include_router(client_settings.router, tags=["client_settings"])
app.include_router(client_organizations.router, tags=["client_organizations"])


@app.on_event("startup")
def startup_event():
    logger.info("🚀 Проверка таблиц БД...")
    check_and_create_tables()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Главная страница админ-панели"""
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
