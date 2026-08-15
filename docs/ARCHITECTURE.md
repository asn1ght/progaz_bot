# ARCHITECTURE.md

# Архитектура проекта ProGaz Telegram Bot


## 1. Общая информация

Проект построен по принципу многослойной архитектуры.

Главная цель:

- разделить Telegram-логику;
- бизнес-логику;
- работу с базой данных;
- внешние сервисы.

Это позволит:

- легко расширять проект;
- добавлять новые функции;
- менять технологии без переписывания всего приложения.


---

# 2. Основная схема взаимодействия



Telegram User

  |

  ↓

Handler

  |

  ↓

Service

  |

  ↓

Repository

  |

  ↓

Database



---

# 3. Уровни приложения


## 3.1 Handler Layer


Путь:


app/handlers/



Назначение:

Работа только с Telegram.


Handler отвечает за:

- получение сообщения;
- обработку кнопок;
- запуск FSM;
- вызов сервисов;
- отправку ответа пользователю.


Handler НЕ должен:

- работать с SQL;
- изменять данные напрямую;
- содержать бизнес-логику.


Пример:


Плохо:

```python
await session.execute(...)

Хорошо:

await object_service.create_object(...)
4. Service Layer

Путь:

app/services/

Назначение:

Основная бизнес-логика.

Service отвечает за:

создание объектов;
изменение графиков;
расчет дат;
создание счетов;
проверку правил.

Пример:

Создание объекта:

Handler:

Получил данные
|
|
Вызвал service

Service:

Проверил данные

Создал объект

Сохранил через Repository
5. Repository Layer

Путь:

app/database/repositories/

Назначение:

Работа с базой данных.

Repository отвечает за:

SELECT;
INSERT;
UPDATE;
DELETE.

Repository НЕ знает про Telegram.

Пример:

ObjectRepository:

Методы:

create()

get_by_id()

get_all()

update()

delete()
6. Database Layer

Путь:

app/database/

Содержит:

models/

base.py

session.py

repositories/
7. Models

Путь:

app/database/models/

Содержит SQLAlchemy модели.

Пример:

User

Object

Inspection

Invoice

Каждая модель:

описывает таблицу;
содержит связи;
содержит типы данных.

Модели НЕ должны содержать бизнес-логику.

8. Session

Файл:

database/session.py

Отвечает за:

подключение к БД;
создание AsyncSession;
управление соединениями.

Используем:

SQLAlchemy Async ORM.

9. Configuration

Файл:

app/config.py

Хранит:

Telegram token;
настройки базы;
параметры приложения.

Все данные берутся из:

.env

Запрещено:

хранить секреты в коде.

10. FSM States

Путь:

app/states/

Назначение:

Хранение состояний Telegram-сценариев.

Примеры:

Добавление объекта:

ObjectCreate.name

ObjectCreate.address

ObjectCreate.engineer

ObjectCreate.date

Изменение даты:

ChangeDate.wait_date
11. Keyboards

Путь:

app/keyboards/

Хранит:

InlineKeyboard;
ReplyKeyboard.

Разделение:

admin/

engineer/

accountant/
12. Scheduler

Путь:

app/scheduler/

Использует:

APScheduler.

Назначение:

Автоматические задачи:

проверка сегодняшних выездов;
отправка уведомлений;
создание счетов;
контроль оплат.

Scheduler НЕ должен работать напрямую с Telegram.

Он вызывает Service.

Пример:

Scheduler

↓

InspectionService

↓

NotificationService

↓

Telegram
13. Middlewares

Путь:

app/middlewares/

Используются для:

проверки пользователя;
загрузки роли;
логирования;
обработки ошибок.
14. Filters

Путь:

app/filters/

Используются для:

проверки роли;
обработки специальных сообщений;
ограничения доступа.

Пример:

Только администратор:

AdminFilter
15. Utils

Путь:

app/utils/

Общие функции.

Примеры:

date_utils.py

logger.py

validators.py
16. Структура проекта
progaz_bot/


app/

 ├── handlers/

 ├── keyboards/

 ├── states/

 ├── services/

 ├── scheduler/

 ├── database/

 │    ├── models/

 │    ├── repositories/

 │    ├── base.py

 │    └── session.py

 ├── middlewares/

 ├── filters/

 ├── utils/

 ├── config.py

 ├── loader.py

 └── bot.py


run.py

.env

requirements.txt

README.md

docs/

17. Error Handling Architecture

Назначение:

Централизованная система обработки ошибок для:

Telegram handlers;
Services;
Database / SQLAlchemy;
APScheduler background jobs.

Компоненты:

app/utils/error_reporter.py

ErrorReporter:

генерация уникального Error ID (ERR-YYYYMMDD-XXXXXX);
построение технического отчета;
запись каждой ошибки в Loguru (уровень ERROR);
отправка отчета разработчику в Telegram;
защита от повторной отправки (cooldown ERROR_COOLDOWN_SECONDS);
redact секретов (BOT_TOKEN, пароли, API keys) перед отправкой.

app/handlers/errors.py

Глобальный aiogram error handler:

dp.register_errors_handler();

перехватывает необработанные исключения из handlers;

пользователю — только безопасное сообщение с Error ID;

разработчику — полный технический отчет.

app/scheduler/setup.py

APScheduler listener:

EVENT_JOB_ERROR;

каждая ошибка job попадает в ErrorReporter;

scheduler не падает.

app/config.py

Настройки:

DEVELOPER_CHAT_ID;
ERROR_REPORTING_ENABLED;
ERROR_COOLDOWN_SECONDS;
ENVIRONMENT.

Loguru:

stderr + logs/app.log;

rotation 10 MB;
retention 30 days;
compression zip.

Поток ошибки:

Exception

→ aiogram errors handler / APScheduler listener

→ ErrorReporter

→ Loguru (всегда)

→ Telegram разработчику (с cooldown)

→ Пользователь: безопасное сообщение с Error ID

Правила:

ErrorReporter никогда не выбрасывает исключения наружу;

длинные отчеты делятся на части (лимит Telegram);

одинаковые ошибки (fingerprint: тип + context + нормализованное сообщение)

не отправляются чаще одного раза за ERROR_COOLDOWN_SECONDS.

18. Правила разработки
Новая функция создается так:

Например:

Добавление объекта.

Создать модель.

models/object.py

Создать repository.

repositories/object.py

Создать service.

services/object.py

Создать FSM.

states/object.py

Создать handler.

handlers/admin/object.py
18. Что запрещено

Запрещено:

SQL в handlers

Плохо:

session.execute()
Бизнес-логика в кнопках

Плохо:

if date.weekday():
    ...
Огромные файлы

Один файл не должен содержать:

1000+ строк;
несколько разных сущностей.
19. Принцип расширения

При добавлении нового функционала:

Сначала проектируется:

База данных.
Repository.
Service.
Telegram-интерфейс.
20. Главная цель архитектуры

Создать поддерживаемый коммерческий продукт.

Код должен быть:

понятным;
расширяемым;
тестируемым;
готовым к переходу SQLite → PostgreSQL.

Конец документа.


---