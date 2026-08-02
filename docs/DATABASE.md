# DATABASE.md

# Структура базы данных проекта ProGaz Telegram Bot

## 1. Общая информация

Тип базы данных в MVP:

SQLite

ORM:

SQLAlchemy 2.x Async ORM

Архитектурный подход:

Database → Repository → Service → Handler


База данных отвечает за хранение:

- пользователей;
- ролей;
- объектов;
- инженеров;
- графиков проверок;
- истории выездов;
- счетов;
- изменений расписания.

---

# 2. Основные сущности

Основные таблицы:

1. users
2. objects
3. inspections
4. invoices
5. schedule_changes


Связи:


users
|
|
|---- objects
|
|---- inspections
|
|---- invoices

objects
|
|
|---- inspections
|
|---- invoices
|
|---- schedule_changes


---

# 3. Таблица users

## Назначение

Хранит всех пользователей Telegram-бота.

В системе нет отдельной таблицы инженеров.

Инженер является обычным пользователем с ролью engineer.

---

## Структура

| Поле | Тип | Описание |
|-|-|-|
| id | Integer | Уникальный идентификатор |
| telegram_id | BigInteger | Telegram ID пользователя |
| full_name | String | Имя пользователя |
| username | String | Username Telegram |
| phone | String | Телефон |
| role | String | Роль пользователя |
| is_active | Boolean | Активность |
| created_at | DateTime | Дата создания |
| updated_at | DateTime | Дата изменения |


---

## Роли

Допустимые значения:


admin

engineer

accountant



---

# 4. Таблица objects

## Назначение

Главная таблица проекта.

Хранит информацию об обслуживаемых объектах.


---

## Структура

| Поле | Тип | Описание |
|-|-|-|
| id | Integer | ID объекта |
| name | String | Название объекта |
| address | String | Адрес |
| engineer_id | FK | Ответственный инженер |
| monthly_day | Integer | День ежемесячного выезда |
| next_inspection_date | Date | Следующая проверка |
| semiannual_service | Boolean | Нужно ли обслуживание раз в полгода |
| invoice_amount | Decimal | Сумма счета |
| comment | Text | Комментарий |
| is_active | Boolean | Активность |
| created_at | DateTime | Создание |
| updated_at | DateTime | Изменение |


---

## Пример записи


id:
1

name:
Котельная №15

address:
Москва, ул. Ленина 10

engineer_id:
5

monthly_day:
15

semiannual_service:
True

invoice_amount:
25000


---

# 5. Таблица inspections

## Назначение

История всех проверок объектов.


Каждый выезд инженера — отдельная запись.


---

## Почему отдельная таблица?

Нельзя хранить только дату в objects.

Нужно видеть историю:



Январь:
Выполнено

Февраль:
Выполнено

Март:
Перенесено

Апрель:
Отменено



---

## Структура

| Поле | Тип | Описание |
|-|-|-|
| id | Integer | ID проверки |
| object_id | FK | Объект |
| engineer_id | FK | Инженер |
| planned_date | Date | Плановая дата |
| actual_date | Date | Фактическая дата |
| status | String | Статус |
| comment | Text | Комментарий |
| created_at | DateTime | Создание |


---

## Статусы


planned

completed

missed

cancelled



---

# 6. Таблица invoices

## Назначение

Хранение счетов.


---

## Структура

| Поле | Тип | Описание |
|-|-|-|
| id | Integer | ID счета |
| object_id | FK | Объект |
| amount | Decimal | Сумма |
| issue_date | Date | Дата создания |
| paid_date | Date | Дата оплаты |
| status | String | Статус |
| comment | Text | Комментарий |
| created_at | DateTime | Создание |


---

## Статусы


waiting

paid



---

# 7. Таблица schedule_changes

## Назначение

История изменений дат.


Например:

Было:

15 число


Стало:

20 число


---

## Структура

| Поле | Тип | Описание |
|-|-|-|
| id | Integer | ID |
| object_id | FK | Объект |
| old_date | Date | Старая дата |
| new_date | Date | Новая дата |
| change_type | String | Тип изменения |
| changed_by | FK | Кто изменил |
| created_at | DateTime | Дата изменения |


---

## Типы изменения



temporary

permanent



---

# 8. Таблица inspection_comments

## Назначение

Комментарии по выполненным работам.


Создана отдельно для возможности расширения.


В будущем можно добавить:

- фотографии;
- документы;
- файлы.


---

## Структура


| Поле | Тип | Описание |
|-|-|-|
| id | Integer | ID |
| inspection_id | FK | Проверка |
| user_id | FK | Автор |
| text | Text | Комментарий |
| created_at | DateTime | Создание |


---

# 9. Связи SQLAlchemy


## User

Один пользователь:

может быть инженером многих объектов.



User 1:N Object



---

## Object

Один объект:

имеет много проверок.



Object 1:N Inspection



---

## Object

Один объект:

имеет много счетов.



Object 1:N Invoice



---

## Object

Один объект:

имеет историю изменений.



Object 1:N ScheduleChange



---

# 10. Индексы


Создать индексы:


users.telegram_id

Для быстрого поиска пользователя.


objects.engineer_id

Для поиска объектов инженера.


inspections.planned_date

Для работы scheduler.


invoices.status

Для поиска неоплаченных счетов.


---

# 11. Что не хранится в базе


Не храним:

- Telegram токен;
- настройки окружения;
- логи;
- временные состояния FSM.


---

# 12. Будущие расширения


Возможное добавление:


## documents

Документы объекта.


## photos

Фотоотчеты инженеров.


## notifications

История отправленных уведомлений.


## companies

Если появится несколько клиентов.


---

# Итоговая схема



USER

|
|
+---- OBJECT

      |
      |
      +---- INSPECTION

      |
      +---- INVOICE

      |
      +---- SCHEDULE_CHANGE

      |
      +---- COMMENT


Конец документа.