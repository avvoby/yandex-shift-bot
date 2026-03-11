"""
Настройка логирования.

Логи нужны, чтобы видеть:
- бот запустился или нет
- где произошла ошибка
- какие действия выполнялись

На первом этапе делаем простой и понятный лог в консоль.
"""

import logging


def setup_logging(log_level: str = "INFO") -> None:
    """
    Настраиваем стандартное логирование Python.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
