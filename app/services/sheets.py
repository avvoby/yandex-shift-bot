"""
Работа с Google Sheets.

Что делает этот файл:
- подключается к Google Sheets через service account
- читает листы
- добавляет строки
- обновляет строки пользователей
- предоставляет удобные методы для всего проекта

Важно:
Google Sheets мы используем как "простую базу данных" для первой версии.
"""

import logging
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from app.config import settings
from app.utils.helpers import bool_from_sheet, now_iso

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """
    Класс для работы с Google Sheets.
    """

    def __init__(self) -> None:
        self._client: gspread.Client | None = None
        self._spreadsheet = None

    def _get_client(self) -> gspread.Client:
        """
        Создаем клиент Google Sheets один раз.
        """
        if self._client is not None:
            return self._client

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        credentials = Credentials.from_service_account_file(
            settings.GOOGLE_CREDENTIALS_FILE,
            scopes=scopes,
        )

        self._client = gspread.authorize(credentials)
        return self._client

    def _get_spreadsheet(self):
        """
        Открываем Google-таблицу по ID.
        """
        if self._spreadsheet is not None:
            return self._spreadsheet

        client = self._get_client()
        self._spreadsheet = client.open_by_key(settings.GOOGLE_SHEETS_ID)
        return self._spreadsheet

    def get_worksheet(self, title: str):
        """
        Возвращает лист по названию.
        """
        spreadsheet = self._get_spreadsheet()
        return spreadsheet.worksheet(title)

    def get_all_records(self, sheet_name: str) -> list[dict[str, Any]]:
        """
        Читаем весь лист как список словарей.
        Первая строка листа должна содержать заголовки колонок.
        """
        worksheet = self.get_worksheet(sheet_name)
        return worksheet.get_all_records()

    def append_row(self, sheet_name: str, row: list[Any]) -> None:
        """
        Добавляем одну строку в конец листа.
        """
        worksheet = self.get_worksheet(sheet_name)
        worksheet.append_row(row, value_input_option="USER_ENTERED")

    def ensure_sheet_exists(self, sheet_name: str, headers: list[str]) -> None:
        """
        Убеждаемся, что лист существует.
        Если листа нет — создаем и записываем заголовки.
        """
        spreadsheet = self._get_spreadsheet()

        try:
            spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            worksheet.append_row(headers, value_input_option="USER_ENTERED")
            logger.info("Создан лист %s", sheet_name)

    def find_user_row_index(self, telegram_id: int) -> int | None:
        """
        Ищем строку пользователя по telegram_id в листе users.
        Возвращаем номер строки в Google Sheets (начиная с 1).
        Важно:
        - строка 1 — заголовки
        - реальные данные обычно с 2 строки
        """
        records = self.get_all_records("users")
        for index, row in enumerate(records, start=2):
            if str(row.get("telegram_id", "")).strip() == str(telegram_id):
                return index
        return None

    def get_user_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        """
        Возвращает пользователя из листа users по telegram_id.
        """
        records = self.get_all_records("users")
        for row in records:
            if str(row.get("telegram_id", "")).strip() == str(telegram_id):
                return row
        return None

    def upsert_user(
        self,
        telegram_id: int,
        username: str,
        first_name: str,
        last_name: str,
        full_name_entered: str,
        phone_entered: str,
    ) -> None:
        """
        Создаем или обновляем пользователя в листе users.

        user_id для первой версии можно хранить равным telegram_id.
        """
        sheet_name = "users"
        row_index = self.find_user_row_index(telegram_id)

        if row_index is None:
            # Новый пользователь
            row = [
                str(telegram_id),              # user_id
                str(telegram_id),              # telegram_id
                username,
                first_name,
                last_name,
                full_name_entered,
                phone_entered,
                now_iso(),                     # registered_at
                "registered",                  # registration_status
                "FALSE",                       # is_blocked
                now_iso(),                     # last_seen_at
            ]
            self.append_row(sheet_name, row)
            logger.info("Добавлен новый пользователь telegram_id=%s", telegram_id)
            return

        # Обновляем существующего пользователя
        worksheet = self.get_worksheet(sheet_name)
        worksheet.update(
            f"A{row_index}:K{row_index}",
            [[
                str(telegram_id),              # user_id
                str(telegram_id),              # telegram_id
                username,
                first_name,
                last_name,
                full_name_entered,
                phone_entered,
                self.get_user_by_telegram_id(telegram_id).get("registered_at", now_iso()),  # type: ignore[union-attr]
                "registered",
                "FALSE",
                now_iso(),
            ]],
        )
        logger.info("Обновлен пользователь telegram_id=%s", telegram_id)

    def update_user_last_seen(self, telegram_id: int) -> None:
        """
        Обновляем last_seen_at у пользователя.
        """
        row_index = self.find_user_row_index(telegram_id)
        if row_index is None:
            return

        worksheet = self.get_worksheet("users")
        # Колонка K = last_seen_at
        worksheet.update(f"K{row_index}", [[now_iso()]])

    def get_all_users(self) -> list[dict[str, Any]]:
        """
        Получаем всех пользователей.
        """
        return self.get_all_records("users")

    def get_active_admin_ids(self) -> list[int]:
        """
        Возвращаем список telegram_id активных админов.
        """
        records = self.get_all_records("admins")
        result: list[int] = []

        for row in records:
            if bool_from_sheet(row.get("is_active")):
                try:
                    result.append(int(str(row.get("telegram_id")).strip()))
                except (TypeError, ValueError):
                    continue

        return result

    def append_support_request(
        self,
        telegram_id: int,
        username: str,
        full_name: str,
        phone: str,
        message_text: str,
        forwarded_to_chat: str,
        status: str = "sent",
    ) -> None:
        """
        Сохраняем обращение пользователя в support_requests.
        """
        row = [
            now_iso(),
            str(telegram_id),
            username,
            full_name,
            phone,
            message_text,
            forwarded_to_chat,
            status,
        ]
        self.append_row("support_requests", row)

    def append_broadcast_log(
        self,
        admin_telegram_id: int,
        admin_name: str,
        broadcast_type: str,
        target_type: str,
        target_value: str,
        message_text: str,
        attachment_type: str,
        attachment_file_id: str,
        recipient_count: int,
        success_count: int,
        fail_count: int,
        status: str,
    ) -> None:
        """
        Сохраняем информацию о рассылке в broadcasts_log.
        """
        row = [
            now_iso(),
            str(admin_telegram_id),
            admin_name,
            broadcast_type,
            target_type,
            target_value,
            message_text,
            attachment_type,
            attachment_file_id,
            recipient_count,
            success_count,
            fail_count,
            status,
        ]
        self.append_row("broadcasts_log", row)

    def append_shift_confirmation(
        self,
        campaign_id: str,
        shift_date: str,
        telegram_id: int,
        username: str,
        full_name: str,
        phone: str,
        question_text: str,
        answer: str,
        answered_at: str,
    ) -> None:
        """
        Сохраняем ответ пользователя на опрос по смене.
        """
        row = [
            campaign_id,
            now_iso(),      # created_at
            shift_date,
            str(telegram_id),
            username,
            full_name,
            phone,
            question_text,
            answer,
            answered_at,
        ]
        self.append_row("shift_confirmations", row)

    def get_settings_dict(self) -> dict[str, str]:
        """
        Читаем лист settings и превращаем в словарь key -> value.
        """
        records = self.get_all_records("settings")
        result: dict[str, str] = {}

        for row in records:
            key = str(row.get("key", "")).strip()
            value = str(row.get("value", "")).strip()
            if key:
                result[key] = value

        return result

    def ensure_required_sheets(self) -> None:
        """
        Создаем листы, если их еще нет.
        Это полезно на старте проекта.
        """
        self.ensure_sheet_exists(
            "users",
            [
                "user_id",
                "telegram_id",
                "username",
                "first_name",
                "last_name",
                "full_name_entered",
                "phone_entered",
                "registered_at",
                "registration_status",
                "is_blocked",
                "last_seen_at",
            ],
        )

        self.ensure_sheet_exists(
            "content",
            [
                "key",
                "title",
                "text",
                "buttons_json",
                "updated_at",
            ],
        )

        self.ensure_sheet_exists(
            "faq",
            [
                "category",
                "question",
                "answer",
                "sort_order_category",
                "sort_order_question",
            ],
        )

        self.ensure_sheet_exists(
            "admins",
            [
                "telegram_id",
                "full_name",
                "is_active",
            ],
        )

        self.ensure_sheet_exists(
            "broadcasts_log",
            [
                "created_at",
                "admin_telegram_id",
                "admin_name",
                "broadcast_type",
                "target_type",
                "target_value",
                "message_text",
                "attachment_type",
                "attachment_file_id",
                "recipient_count",
                "success_count",
                "fail_count",
                "status",
            ],
        )

        self.ensure_sheet_exists(
            "support_requests",
            [
                "created_at",
                "telegram_id",
                "username",
                "full_name",
                "phone",
                "message_text",
                "forwarded_to_chat",
                "status",
            ],
        )

        self.ensure_sheet_exists(
            "settings",
            [
                "key",
                "value",
            ],
        )

        self.ensure_sheet_exists(
            "shift_confirmations",
            [
                "campaign_id",
                "created_at",
                "shift_date",
                "telegram_id",
                "username",
                "full_name",
                "phone",
                "question_text",
                "answer",
                "answered_at",
            ],
        )


# Один общий объект сервиса на весь проект
sheets_service = GoogleSheetsService()
