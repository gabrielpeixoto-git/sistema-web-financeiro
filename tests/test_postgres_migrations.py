import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run")
def test_postgres_alembic_upgrade_head():
    test_db_url = os.environ["TEST_DATABASE_URL"]
    previous_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_db_url

    try:
        engine = create_engine(test_db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.commit()

        cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
    finally:
        if previous_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_db_url
