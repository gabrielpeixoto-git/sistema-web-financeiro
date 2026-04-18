from typing import Iterator

from sqlmodel import Session

from financas_app.app.db.engine import get_engine


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
