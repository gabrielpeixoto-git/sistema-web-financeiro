from __future__ import annotations

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


def test_import_rejects_non_csv_extension(client):
    _register_and_seed_account(client, "import-ext@test.com")
    files = {"file": ("data.txt", BytesIO(b"x"), "text/plain")}
    r = client.post("/api/transactions/import", files=files)
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "invalid_file_extension"
    assert ".csv" in body["detail"]


def test_import_rejects_invalid_encoding_with_rate_limit_headers(client):
    _register_and_seed_account(client, "import-encoding@test.com")
    files = {"file": ("bad.csv", BytesIO(b"\xff\xfe\x00\x00"), "text/csv")}
    r = client.post("/api/transactions/import", files=files)
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "invalid_csv_encoding"
    assert "UTF-8" in body["detail"]
    assert r.headers.get("x-ratelimit-limit")
    assert r.headers.get("x-ratelimit-remaining") is not None
    assert r.headers.get("x-ratelimit-reset")
    assert r.headers.get("x-ratelimit-policy")


def test_import_rejects_invalid_header_with_rate_limit_headers(client):
    _register_and_seed_account(client, "import-header@test.com")
    content = "date,kind,amount\n2026-04-01,in,10,00\n"
    files = {"file": ("bad.csv", BytesIO(content.encode("utf-8")), "text/csv")}
    r = client.post("/api/transactions/import", files=files)
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "invalid_csv_header"
    assert "account_name" in body["missing_columns"]
    assert "description" in body["missing_columns"]
    assert r.headers.get("x-ratelimit-limit")
    assert r.headers.get("x-ratelimit-remaining") is not None
    assert r.headers.get("x-ratelimit-reset")
    assert r.headers.get("x-ratelimit-policy")


def test_import_success_includes_rate_limit_headers(client):
    _register_and_seed_account(client, "import-ok@test.com")
    content = (
        "date,kind,account_name,category_name,amount,description\n"
        "2026-04-01,in,Carteira,,10,00,entrada\n"
    )
    content = content.replace("10,00", '"10,00"')
    files = {"file": ("ok.csv", BytesIO(content.encode("utf-8")), "text/csv")}
    r = client.post("/api/transactions/import", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending"
    assert body["task_id"]
    assert r.headers.get("x-ratelimit-limit")
    assert r.headers.get("x-ratelimit-remaining") is not None
    assert r.headers.get("x-ratelimit-reset")
    assert r.headers.get("x-ratelimit-policy")


def test_import_task_done_includes_meta(client):
    _register_and_seed_account(client, "import-meta@test.com")
    content = (
        "date,kind,account_name,category_name,amount,description\n"
        "2026-04-01,in,Carteira,,10,00,entrada\n"
    )
    content = content.replace("10,00", '"10,00"')
    files = {"file": ("ok.csv", BytesIO(content.encode("utf-8")), "text/csv")}
    r = client.post("/api/transactions/import", files=files)
    assert r.status_code == 200
    task_id = r.json()["task_id"]
    body: dict = {}
    for _ in range(80):
        r2 = client.get(f"/api/transactions/tasks/{task_id}")
        body = r2.json()
        if body.get("status") == "done":
            break
        time.sleep(0.03)
    assert body.get("status") == "done"
    assert body.get("meta", {}).get("created") == 1
    assert "skipped" in body["meta"]
    assert "skip_samples" in body["meta"]
