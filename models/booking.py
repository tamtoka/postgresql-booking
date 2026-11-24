from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar


@dataclass(frozen=True)
class Booking:
    id: int
    user_id: int
    table_id: int
    starts_at: datetime
    ends_at: datetime

    relation: ClassVar[str] = "bookings"
    fields: ClassVar[tuple[str, ...]] = ("user_id", "table_id", "starts_at", "ends_at")
    ddl: ClassVar[str] = """
        CREATE TABLE IF NOT EXISTS public.bookings (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id integer NOT NULL REFERENCES public.users(id),
            table_id integer NOT NULL REFERENCES public.tables(id),
            starts_at timestamp NOT NULL,
            ends_at timestamp NOT NULL,
            CONSTRAINT booking_positive_duration CHECK (starts_at < ends_at),
            CONSTRAINT booking_no_overlap EXCLUDE USING gist (
                table_id WITH =,
                tsrange(starts_at, ends_at, '[)') WITH &&
            )
        )
    """
