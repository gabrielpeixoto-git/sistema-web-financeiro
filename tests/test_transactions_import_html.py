from __future__ import annotations

import re
import time
from io import BytesIO

import pytest


def _register_and_seed_account(client, email: str) -> None:
    from sqlmodel import Session

    from financas_app.app.db.engine import get_engine
    from financas_app.app.modules.accounts.service import create_account
    from financas_app.app.modules.auth.repo import get_user_by_email

    client.post(
        "/auth/register",
        data={"email": email, "name": "User", "password": "password123"},
        follow_redirects=False,
    )
    with Session(get_engine()) as session:
        user = get_user_by_email(session, email)
        assert user is not None
        create_account(session, user_id=user.id, currency="BRL", name="Carteira")


@pytest.mark.parametrize(
    ("filename", "raw", "expect"),
    [
        ("x.txt", b"x", "extensão"),
        ("bad.csv", b"\xff\xfe\x00\x00", "UTF-8"),
    ],
)
def test_transactions_import_html_validation_message(client, filename, raw, expect):
    _register_and_seed_account(client, f"html-imp-{filename}@test.com")
    files = {"file": (filename, BytesIO(raw), "text/csv")}
    r = client.post("/transactions/import", files=files)
    assert r.status_code == 200
    assert expect in r.text


def test_transactions_import_html_success_polls_status(client):
    _register_and_seed_account(client, "html-imp-ok@test.com")
    content = (
        "date,kind,account_name,category_name,amount,description\n"
        "2026-04-01,in,Carteira,,10,00,entrada\n"
    ).replace("10,00", '"10,00"')
    files = {"file": ("ok.csv", BytesIO(content.encode("utf-8")), "text/csv")}
    r = client.post("/transactions/import", files=files)
    assert r.status_code == 200
    m = re.search(r'import-status/([a-f0-9]{32})"', r.text)
    assert m, r.text
    task_id = m.group(1)
    html = ""
    for _ in range(80):
        sr = client.get(f"/transactions/import-status/{task_id}")
        assert sr.status_code == 200
        html = sr.text
        if "Importação concluída" in html:
            break
        time.sleep(0.03)
    assert "Importação concluída" in html
    assert "Incluídas:" in html


def test_transactions_import_html_unknown_task(client):
    _register_and_seed_account(client, "html-imp-miss@test.com")
    r = client.get("/transactions/import-status/" + "0" * 32)
    assert r.status_code == 200
    assert "Tarefa não encontrada" in r.text
