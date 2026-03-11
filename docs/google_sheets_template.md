# Шаблон Google Sheets для Telegram-бота

Ниже перечислены все листы, которые должны быть в Google-таблице.

---

## 1. Лист `users`

Хранит зарегистрированных пользователей.

### Колонки:
- user_id
- telegram_id
- username
- first_name
- last_name
- full_name_entered
- phone_entered
- registered_at
- registration_status
- is_blocked
- last_seen_at

### Пример строки:
| user_id | telegram_id | username | first_name | last_name | full_name_entered | phone_entered | registered_at | registration_status | is_blocked | last_seen_at |
|---|---|---|---|---|---|---|---|---|---|---|
| 123456789 | 123456789 | ivan_ivanov | Ivan | Ivanov | Иванов Иван Иванович | +79991234567 | 2026-03-11T10:00:00+00:00 | registered | FALSE | 2026-03-11T10:05:00+00:00 |

---

## 2. Лист `content`

Хранит тексты и кнопки для разделов меню.

### Колонки:
- key
- title
- text
- buttons_json
- updated_at

### Обязательные ключи:
- registration_welcome
- main_menu_text
- fallback_message
- ask_question_prompt
- ask_question_success
- more_jobs
- support_chat
- access_document
- training

### Пример строк:

| key | title | text | buttons_json | updated_at |
|---|---|---|---|---|
| registration_welcome | Регистрация | Здравствуйте! Для работы с ботом нужно пройти регистрацию. Пожалуйста, введите ваши ФИО полностью. |  | 2026-03-11 |
| main_menu_text | Главное меню | Выберите нужный раздел. |  | 2026-03-11 |
| fallback_message | Сообщение по умолчанию | Мы не можем помочь в этом формате. Пожалуйста, обратитесь в чат поддержки в Telegram или в приложении. |  | 2026-03-11 |
| ask_question_prompt | Задать вопрос | Напишите ваш вопрос. Мы передадим его коллегам. |  | 2026-03-11 |
| ask_question_success | Вопрос отправлен | Спасибо! Ваш вопрос передан коллегам. Скоро с вами свяжутся. |  | 2026-03-11 |
| more_jobs | Еще задания | Посмотрите дополнительные задания по ссылке ниже. | [{"text":"Открыть задания","url":"https://example.com/jobs"}] | 2026-03-11 |
| support_chat | Чат поддержки | Перейдите в чат поддержки по кнопке ниже. | [{"text":"Открыть чат","url":"https://t.me/example_chat"}] | 2026-03-11 |
| access_document | Допуск на объект | Чтобы получить документ для допуска, заполните форму по ссылке ниже. | [{"text":"Открыть форму","url":"https://example.com/form"}] | 2026-03-11 |
| training | Обучение | Пройдите обучение по ссылкам ниже. | [{"text":"Материал 1","url":"https://example.com/1"},{"text":"Материал 2","url":"https://example.com/2"}] | 2026-03-11 |

### Как заполнять buttons_json
Если кнопок нет — оставьте пусто.

Если одна кнопка:
```json
[{"text":"Открыть","url":"https://example.com"}]
