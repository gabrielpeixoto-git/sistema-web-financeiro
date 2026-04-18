from __future__ import annotations

import re
import time
from io import BytesIO


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


def test_transactions_import_preview_then_confirm(client):
    _register_and_seed_account(client, "imp-preview@test.com")
    content = (
        "date,kind,account_name,category_name,amount,description\n"
        "2026-04-01,in,Carteira,,10,00,entrada\n"
    ).replace("10,00", '"10,00"')
    files = {"file": ("ok.csv", BytesIO(content.encode("utf-8")), "text/csv")}

    r = client.post("/transactions/import/preview", files=files)
    assert r.status_code == 200
    assert "Pré-visualização" in r.text
    m = re.search(r'name=\"task_id\" value=\"([a-f0-9]{32})\"', r.text)
    assert m, r.text
    task_id = m.group(1)

    r2 = client.post("/transactions/import/confirm", data={"task_id": task_id})
    assert r2.status_code == 200
    assert "Processando importação" in r2.text

    html = ""
    for _ in range(80):
        sr = client.get(f"/transactions/import-status/{task_id}")
        assert sr.status_code == 200
        html = sr.text
        if "Importação concluída" in html:
            break
        time.sleep(0.03)
    assert "Importação concluída" in html

