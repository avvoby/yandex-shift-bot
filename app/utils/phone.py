"""
Вспомогательные функции для работы с номером телефона.

По ТЗ мы просим пользователя вводить номер строго в формате:
+7XXXXXXXXXX

Но на практике люди могут вставлять:
- +7 999 123-45-67
- 89991234567
- 7 (999) 1234567

Поэтому:
1. очищаем номер от лишних символов
2. пытаемся привести его к формату +7XXXXXXXXXX
3. валидируем
"""

import re


def normalize_phone(raw_phone: str) -> str:
    """
    Пытается привести номер телефона к виду +7XXXXXXXXXX.

    Примеры:
    89991234567 -> +79991234567
    +7 999 123-45-67 -> +79991234567
    """
    phone = raw_phone.strip()

    # Оставляем только цифры и плюс в начале
    digits = re.sub(r"[^\d+]", "", phone)

    # Если пользователь ввел номер с 8XXXXXXXXXX
    if re.fullmatch(r"8\d{10}", digits):
        return "+7" + digits[1:]

    # Если пользователь ввел 7XXXXXXXXXX
    if re.fullmatch(r"7\d{10}", digits):
        return "+" + digits

    # Если уже в правильном формате
    if re.fullmatch(r"\+7\d{10}", digits):
        return digits

    return raw_phone.strip()


def is_valid_russian_phone(phone: str) -> bool:
    """
    Проверяем, что номер строго соответствует формату +7XXXXXXXXXX
    """
    return bool(re.fullmatch(r"\+7\d{10}", phone.strip()))
