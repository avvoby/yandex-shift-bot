"""
Простой кэш в памяти.

Зачем он нужен:
- чтобы бот не ходил в Google Sheets при каждом сообщении;
- чтобы снизить нагрузку;
- чтобы ускорить ответы.

Как работает:
- мы храним данные в памяти;
- у каждого набора данных есть время последнего обновления;
- если кэш устарел, данные перечитываются из Google Sheets.
"""

from datetime import datetime, timedelta, timezone
from typing import Any


class SimpleCache:
    """
    Очень простой кэш:
    key -> {"value": ..., "updated_at": ...}
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    def set(self, key: str, value: Any) -> None:
        """
        Сохраняем значение в кэш.
        """
        self._data[key] = {
            "value": value,
            "updated_at": datetime.now(timezone.utc),
        }

    def get(self, key: str) -> Any:
        """
        Возвращаем значение из кэша или None, если ничего нет.
        """
        item = self._data.get(key)
        if not item:
            return None
        return item["value"]

    def is_expired(self, key: str, minutes: int) -> bool:
        """
        Проверяем, устарел ли кэш.
        Если записи нет — считаем, что устарел.
        """
        item = self._data.get(key)
        if not item:
            return True

        updated_at = item["updated_at"]
        expire_at = updated_at + timedelta(minutes=minutes)
        return datetime.now(timezone.utc) > expire_at

    def clear(self, key: str | None = None) -> None:
        """
        Очищаем:
        - весь кэш, если key не передан
        - только один ключ, если key указан
        """
        if key is None:
            self._data.clear()
            return

        self._data.pop(key, None)
