from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Table:
    id: int
    number: int
    capacity: int

    relation: ClassVar[str] = "tables"
    fields: ClassVar[tuple[str, ...]] = ("number", "capacity")
    ddl: ClassVar[str] = """
        CREATE TABLE IF NOT EXISTS public.tables (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            number integer NOT NULL UNIQUE CHECK (number > 0),
            capacity integer NOT NULL CHECK (capacity > 0)
        )
    """
