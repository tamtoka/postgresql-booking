import argparse
import sys
from datetime import datetime

import psycopg2
from psycopg2 import errors

import backend
from models import Booking, Table, User
from postgres_driver import init_db


def read_id(label):
    value = int(input(f"{label}: "))
    if value < 1:
        raise ValueError(f"{label} должен быть положительным числом.")
    return value


def read_period():
    return tuple(
        datetime.strptime(input(f"{label} (ГГГГ-ММ-ДД ЧЧ:ММ): "), "%Y-%m-%d %H:%M")
        for label in ("Начало", "Окончание")
    )


def user_fields():
    return input("Имя: "), input("Email: ")


def table_fields():
    return read_id("Номер стола"), read_id("Число мест")


def booking_fields():
    return read_id("ID пользователя"), read_id("ID стола"), *read_period()


def describe(record):
    if isinstance(record, User):
        return f"#{record.id}  {record.name}  {record.email}"
    if isinstance(record, Table):
        return f"#{record.id}  Стол №{record.number}, мест: {record.capacity}"
    if isinstance(record, Booking):
        return (
            f"#{record.id}  Стол ID {record.table_id}  Пользователь ID {record.user_id}"
            f"  {record.starts_at:%Y-%m-%d %H:%M} — {record.ends_at:%Y-%m-%d %H:%M}"
        )
    return "Запись не найдена."


def manage(title, fields, list_all, get, create, update, delete):
    print(f"\n{title}\n1  Список   2  Найти по ID   3  Добавить   4  Изменить   5  Удалить   0  Назад")
    action = input("> ").strip()
    if action == "1":
        records = list_all()
        if not records:
            print("Записей пока нет.")
        for record in records:
            print(describe(record))
    elif action == "2":
        print(describe(get(read_id("ID записи"))))
    elif action == "3":
        print(describe(create(*fields())))
    elif action == "4":
        record_id = read_id("ID записи")
        if get(record_id) is None:
            print("Запись не найдена.")
        else:
            print(describe(update(record_id, *fields())))
    elif action == "5":
        print("Запись удалена." if delete(read_id("ID записи")) else "Запись не найдена.")
    elif action != "0":
        print("Выберите пункт от 0 до 5.")


SECTIONS = {
    "1": (
        "Пользователи", user_fields, backend.get_all_users, backend.get_user,
        backend.create_user, backend.update_user, backend.delete_user,
    ),
    "2": (
        "Столы", table_fields, backend.get_all_tables, backend.get_table,
        backend.create_table, backend.update_table, backend.delete_table,
    ),
    "3": (
        "Бронирования", booking_fields, backend.get_all_bookings, backend.get_booking,
        backend.create_booking, backend.update_booking, backend.delete_booking,
    ),
}


def menu():
    while True:
        print(
            "\nБД6 · Бронирование столов\n"
            "1  Пользователи   2  Столы   3  Бронирования\n"
            "4  Проверить доступность   0  Выход"
        )
        action = input("> ").strip()
        try:
            if action == "0":
                return
            if action == "4":
                available = backend.check_table_availability(read_id("ID стола"), *read_period())
                print("Стол свободен." if available else "Стол занят на это время.")
            elif action in SECTIONS:
                manage(*SECTIONS[action])
            else:
                print("Выберите пункт от 0 до 4.")
        except ValueError as error:
            print(f"Ошибка ввода: {error}")
        except errors.UniqueViolation:
            print("Запись с таким email или номером стола уже существует.")
        except errors.ForeignKeyViolation:
            print("Проверьте ID пользователя и стола. Перед удалением записи удалите связанные бронирования.")
        except errors.CheckViolation:
            print("Проверьте обязательные поля и допустимые значения.")
        except errors.DataException:
            print("Введённое значение выходит за допустимые пределы.")


def main():
    parser = argparse.ArgumentParser(description="Бронирование столов в PostgreSQL")
    parser.add_argument("--seed", action="store_true", help="добавить учебные записи и выйти")
    args = parser.parse_args()
    try:
        init_db()
        if args.seed:
            backend.seed_demo()
            print("Учебные записи подготовлены.")
        else:
            menu()
    except (EOFError, KeyboardInterrupt):
        print()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    except psycopg2.Error:
        print("Ошибка PostgreSQL. Проверьте подключение, права и схему базы по README.md.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
