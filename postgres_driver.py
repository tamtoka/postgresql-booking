import os
from contextlib import closing, contextmanager
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from models import MODELS


@contextmanager
def transaction():
    """Открывает соединение и завершает транзакцию при выходе из блока."""
    load_dotenv(Path(__file__).with_name(".env"))
    keys = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        raise ValueError("Заполните параметры подключения: " + ", ".join(missing))

    with closing(psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=5,
    )) as connection, connection, connection.cursor() as cursor:
        yield cursor


def init_db():
    with transaction() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(619806)")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        for model in MODELS:
            cursor.execute(model.ddl)
