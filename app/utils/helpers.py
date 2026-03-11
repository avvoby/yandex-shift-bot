"""
Разные небольшие вспомогательные функции,
которые переиспользуются в нескольких местах проекта.
"""

from datetime import datetime, timezone
from typing import Iterable


def now_iso() -> str:
    """
    Возвращает текущую дату и время в ISO-формате.
    Такой формат удобно хранить в Google Sheets.
    """
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: str | int | None, default: int = 0) -> int:
    """
    Безопасное преобразование в число.
    Если не получилось — возвращаем default.
    """
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def split_and_clean_lines(text: str) -> list[str]:
    """
    Разбивает текст по строкам, удаляет пустые строки и лишние пробелы.
    Полезно для вставки списка Telegram ID.
    """
    lines = [line.strip() for line in text.splitlines()]
    return [line for line in lines if line]


def parse_telegram_ids(text: str) -> list[int]:
    """
    Получает текст, где админ вставил Telegram ID по одному на строку,
    и превращает его в список чисел.

    Пример входа:
    12345
    56789
    99999
    """
    result = []
    for line in split_and_clean_lines(text):
        try:
            result.append(int(line))
        except ValueError:
            # Невалидные строки просто пропускаем
            continue
    return result


def chunk_list(items: list, size: int) -> list[list]:
    """
    Разбивает список на части по size элементов.
    Это пригодится для аккуратных рассылок.
    """
    if size <= 0:
        return [items]

    return [items[i:i + size] for i in range(0, len(items), size)]


def bool_from_sheet(value: str | bool | None) -> bool:
    """
    Переводим значения из Google Sheets в bool.

    Считаем TRUE / true / 1 / yes / да как True.
    """
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return str(value).strip().lower() in {"true", "1", "yes", "да"}
