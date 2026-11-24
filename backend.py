from contextlib import contextmanager
from datetime import datetime

from psycopg2 import errors, sql

from models import Booking, Table, User
from postgres_driver import transaction


def _create(cursor, model, values, *, ignore_conflict=False):
    query = sql.SQL("INSERT INTO public.{} ({}) VALUES ({})").format(
        sql.Identifier(model.relation),
        sql.SQL(", ").join(map(sql.Identifier, model.fields)),
        sql.SQL(", ").join([sql.Placeholder()] * len(values)),
    )
    if ignore_conflict:
        query += sql.SQL(" ON CONFLICT DO NOTHING")
    cursor.execute(query + sql.SQL(" RETURNING *"), values)
    row = cursor.fetchone()
    return model(*row) if row else None


def _get(model, record_id):
    with transaction() as cursor:
        cursor.execute(
            sql.SQL("SELECT * FROM public.{} WHERE id = %s").format(
                sql.Identifier(model.relation)
            ),
            (record_id,),
        )
        row = cursor.fetchone()
        return model(*row) if row else None


def _list(model):
    with transaction() as cursor:
        cursor.execute(
            sql.SQL("SELECT * FROM public.{} ORDER BY id").format(
                sql.Identifier(model.relation)
            )
        )
        return [model(*row) for row in cursor.fetchall()]


def _update(cursor, model, record_id, values):
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(field)) for field in model.fields
    )
    cursor.execute(
        sql.SQL("UPDATE public.{} SET {} WHERE id = %s RETURNING *").format(
            sql.Identifier(model.relation), assignments
        ),
        (*values, record_id),
    )
    row = cursor.fetchone()
    return model(*row) if row else None


def _delete(model, record_id):
    with transaction() as cursor:
        cursor.execute(
            sql.SQL("DELETE FROM public.{} WHERE id = %s").format(
                sql.Identifier(model.relation)
            ),
            (record_id,),
        )
        return cursor.rowcount == 1


def create_user(name, email):
    with transaction() as cursor:
        return _create(cursor, User, (name.strip(), email.strip().lower()))


def get_user(user_id):
    return _get(User, user_id)


def get_all_users():
    return _list(User)


def update_user(user_id, name, email):
    with transaction() as cursor:
        return _update(cursor, User, user_id, (name.strip(), email.strip().lower()))


def delete_user(user_id):
    return _delete(User, user_id)


def create_table(number, capacity):
    with transaction() as cursor:
        return _create(cursor, Table, (number, capacity))


def get_table(table_id):
    return _get(Table, table_id)


def get_all_tables():
    return _list(Table)


def update_table(table_id, number, capacity):
    with transaction() as cursor:
        return _update(cursor, Table, table_id, (number, capacity))


def delete_table(table_id):
    return _delete(Table, table_id)


def _validate_period(starts_at, ends_at):
    if starts_at.utcoffset() is not None or ends_at.utcoffset() is not None:
        raise ValueError("Укажите местное время ресторана без часового пояса.")
    if starts_at >= ends_at:
        raise ValueError("Время окончания должно быть позже начала.")


def check_table_availability(table_id, starts_at, ends_at):
    _validate_period(starts_at, ends_at)
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT NOT EXISTS (
                SELECT 1 FROM public.bookings
                WHERE table_id = tables.id
                  AND tsrange(starts_at, ends_at, '[)') && tsrange(%s, %s, '[)')
            )
            FROM public.tables WHERE id = %s
            """,
            (starts_at, ends_at, table_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("Стол с таким ID не найден.")
        return row[0]


@contextmanager
def _booking_write():
    try:
        with transaction() as cursor:
            # Очередь записи исключает взаимную блокировку при проверке GiST.
            cursor.execute("LOCK TABLE public.bookings IN SHARE ROW EXCLUSIVE MODE")
            yield cursor
    except errors.ExclusionViolation as error:
        raise ValueError("Стол уже забронирован на это время.") from error


def create_booking(user_id, table_id, starts_at, ends_at):
    _validate_period(starts_at, ends_at)
    with _booking_write() as cursor:
        return _create(cursor, Booking, (user_id, table_id, starts_at, ends_at))


def get_booking(booking_id):
    return _get(Booking, booking_id)


def get_all_bookings():
    return _list(Booking)


def update_booking(booking_id, user_id, table_id, starts_at, ends_at):
    _validate_period(starts_at, ends_at)
    with _booking_write() as cursor:
        return _update(cursor, Booking, booking_id, (user_id, table_id, starts_at, ends_at))


def delete_booking(booking_id):
    return _delete(Booking, booking_id)


def seed_demo():
    """Заполняет учебную базу. Повторный запуск не дублирует записи."""
    with _booking_write() as cursor:
        for name, email in (
            ("Анна", "anna@example.com"),
            ("Борис", "boris@example.com"),
            ("Вера", "vera@example.com"),
        ):
            _create(cursor, User, (name, email), ignore_conflict=True)
        for number, capacity in ((1, 2), (2, 4), (3, 6)):
            _create(cursor, Table, (number, capacity), ignore_conflict=True)

        for email, number, hour in (
            ("anna@example.com", 1, 18),
            ("boris@example.com", 2, 19),
        ):
            cursor.execute("SELECT id FROM public.users WHERE email = %s", (email,))
            user_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM public.tables WHERE number = %s", (number,))
            table_id = cursor.fetchone()[0]
            _create(
                cursor,
                Booking,
                (
                    user_id, table_id,
                    datetime(2026, 12, 1, hour), datetime(2026, 12, 1, hour + 1),
                ),
                ignore_conflict=True,
            )
