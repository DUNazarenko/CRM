# app/utils/__init__.py

from fastapi.templating import Jinja2Templates
import os

# Определяем абсолютный путь до папки с шаблонами
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Инициализируем шаблонизатор
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Чтобы другие утилиты могли использовать объект templates напрямую:
__all__ = ["templates"]
