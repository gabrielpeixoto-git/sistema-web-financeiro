from datetime import date

from sqlmodel import Session, SQLModel, create_engine

import financas_app.app.db.models  # noqa: F401
from financas_app.app.modules.accounts.service import create_account
from financas_app.app.modules.auth.models import User
from financas_app.app.modules.categories.service import create_category
from financas_app.app.modules.transactions.service import (
    create_transaction,
    export_csv,
    import_csv_content,
    list_transactions,
)


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'csv_test.db'}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _user(session: Session) -> User:
    u = User(email="csv@test.com", name="csv", hashed_password="x")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_export_csv_contains_rows(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s)
        a = create_account(s, user_id=u.id, currency="BRL", name="Conta A")
        create_transaction(
            s,
            user_id=u.id,
            account_id=a.id,
            kind="in",
            amount="10,00",
            occurred_on=date(2026, 4, 1),
            description="salario",
        )
        csv_content = export_csv(s, user_id=u.id)
        assert "date,kind,account_id,category_id,amount_cents,description" in csv_content
        assert "2026-04-01,in" in csv_content


def test_import_csv_creates_and_skips_duplicates(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s)
        create_account(s, user_id=u.id, currency="BRL", name="Carteira")
        create_category(s, user_id=u.id, name="Mercado")

        content = (
            "date,kind,account_name,category_name,amount,description\n"
            "2026-04-01,out,Carteira,Mercado,12,34,compra\n"
        )
        # corrige separador decimal para manter CSV simples
        content = content.replace("12,34", '"12,34"')

        r1 = import_csv_content(s, user_id=u.id, content=content)
        r2 = import_csv_content(s, user_id=u.id, content=content)
        assert r1["created"] == 1
        assert r2["created"] == 0
        assert r2["skipped"] >= 1
        assert r2["skip_reasons"]["duplicate"] >= 1
        assert len(list_transactions(s, user_id=u.id, limit=10)) == 1


def test_import_csv_skip_samples_reference_lines(tmp_path):
    with _session(tmp_path) as s:
        u = _user(s)
        create_account(s, user_id=u.id, currency="BRL", name="Carteira")
        content = (
            "date,kind,account_name,category_name,amount,description\n"
            "2026-04-01,in,Carteira,,10,00,ok\n"
            "2026-04-02,in,Inexistente,,5,00,bad\n"
        )
        content = content.replace("10,00", '"10,00"').replace("5,00", '"5,00"')
        r = import_csv_content(s, user_id=u.id, content=content)
        assert r["created"] == 1
        assert r["skipped"] == 1
        samples = r.get("skip_samples") or []
        assert len(samples) == 1
        assert samples[0]["reason"] == "account_not_found"
        assert samples[0]["line"] == 3

