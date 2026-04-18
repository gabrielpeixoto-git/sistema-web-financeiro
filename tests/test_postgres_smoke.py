import os

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from financas_app.app.db import models as _models  # noqa: F401


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run")
def test_postgres_connection_and_schema():
    engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        value = session.exec(text("SELECT 1")).scalar()
    assert value == 1
