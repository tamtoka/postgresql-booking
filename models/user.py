from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str

    relation: ClassVar[str] = "users"
    fields: ClassVar[tuple[str, ...]] = ("name", "email")
    ddl: ClassVar[str] = """
        CREATE TABLE IF NOT EXISTS public.users (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name text NOT NULL CHECK (btrim(name) <> ''),
            email text NOT NULL UNIQUE CHECK (btrim(email) <> '')
        )
    """
