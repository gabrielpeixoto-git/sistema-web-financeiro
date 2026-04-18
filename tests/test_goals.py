from datetime import date

from sqlmodel import SQLModel, Session, create_engine

from financas_app.app.modules.auth.models import User
from financas_app.app.modules.goals.service import (
    add_progress,
    create_goal,
    deactivate,
    format_row,
    list_rows,
)


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'goal_test.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session, email: str, name: str) -> User:
    u = User(email=email, name=name, hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_create_and_progress(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "g1@test.com", "U")
        g = create_goal(s, user_id=u.id, name=" Viagem ", target="1.000,00", due_on=date(2026, 12, 31))
        assert g.target_cents == 100000
        assert g.saved_cents == 0
        add_progress(s, user_id=u.id, goal_id=g.id, amount="250,50")
        rows = list_rows(s, user_id=u.id)
        assert len(rows) == 1
        assert rows[0].saved_cents == 25050
        d = format_row(rows[0])
        assert d["done"] is False
        add_progress(s, user_id=u.id, goal_id=g.id, amount="749,50")
        rows = list_rows(s, user_id=u.id)
        d2 = format_row(rows[0])
        assert d2["done"] is True
        assert d2["bar_pct"] == 100


def test_deactivate(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s, "g2@test.com", "U")
        g = create_goal(s, user_id=u.id, name="X", target="100,00")
        deactivate(s, user_id=u.id, goal_id=g.id)
        assert list_rows(s, user_id=u.id) == []
