from datetime import UTC, datetime, timedelta


def test_register_login_me(client):
    r = client.post(
        "/auth/register",
        data={"email": "a@a.com", "name": "A", "password": "password123"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = client.get("/me")
    assert r.status_code == 200
    assert r.json()["email"] == "a@a.com"

    client.post("/auth/logout", follow_redirects=False)
    r = client.get("/me")
    assert r.status_code == 401


def test_forgot_password_generic_message_registered_and_unknown(client):
    msg_snippet = "Se o email existir"
    r = client.post("/auth/forgot", data={"email": "unknown@x.com"}, follow_redirects=False)
    assert r.status_code == 200
    assert msg_snippet in r.text

    client.post(
        "/auth/register",
        data={"email": "b@b.com", "name": "B", "password": "password123"},
        follow_redirects=False,
    )
    r = client.post("/auth/forgot", data={"email": "b@b.com"}, follow_redirects=False)
    assert r.status_code == 200
    assert msg_snippet in r.text


def test_password_reset_request_and_login(client):
    from sqlmodel import Session

    from financas_app.app.db.engine import get_engine
    from financas_app.app.modules.auth import service

    client.post(
        "/auth/register",
        data={"email": "c@c.com", "name": "C", "password": "password123"},
        follow_redirects=False,
    )
    with Session(get_engine()) as session:
        token = service.request_password_reset(session, email="c@c.com")
        assert token

    r = client.post(
        "/auth/reset",
        data={"token": token, "password": "newpass99"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers.get("location", "").endswith("/auth/login")

    client.post("/auth/logout", follow_redirects=False)
    r = client.post(
        "/auth/login",
        data={"email": "c@c.com", "password": "newpass99"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    r = client.get("/me")
    assert r.status_code == 200


def test_password_reset_invalid_token(client):
    r = client.post(
        "/auth/reset",
        data={"token": "0" * 64, "password": "newpass99"},
        follow_redirects=False,
    )
    assert r.status_code == 400
    assert "Token inválido" in r.text


def test_password_reset_expired_token(client):
    from sqlmodel import Session

    from financas_app.app.common.security import sha256_hex
    from financas_app.app.db.engine import get_engine
    from financas_app.app.modules.auth import service
    from financas_app.app.modules.auth.models import PasswordResetToken

    client.post(
        "/auth/register",
        data={"email": "d@d.com", "name": "D", "password": "password123"},
        follow_redirects=False,
    )
    raw = "e" * 64
    with Session(get_engine()) as session:
        u = service.login(session, email="d@d.com", password="password123")
        session.add(
            PasswordResetToken(
                user_id=u.id,
                token_hash=sha256_hex(raw),
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        session.commit()

    r = client.post(
        "/auth/reset",
        data={"token": raw, "password": "newpass99"},
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_password_reset_token_single_use(client):
    from sqlmodel import Session

    from financas_app.app.db.engine import get_engine
    from financas_app.app.modules.auth import service

    client.post(
        "/auth/register",
        data={"email": "e@e.com", "name": "E", "password": "password123"},
        follow_redirects=False,
    )
    with Session(get_engine()) as session:
        token = service.request_password_reset(session, email="e@e.com")
        assert token

    r = client.post(
        "/auth/reset",
        data={"token": token, "password": "firstpass1"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = client.post(
        "/auth/reset",
        data={"token": token, "password": "secondpass2"},
        follow_redirects=False,
    )
    assert r.status_code == 400

    client.post("/auth/logout", follow_redirects=False)
    r = client.post(
        "/auth/login",
        data={"email": "e@e.com", "password": "firstpass1"},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_refresh_without_cookies_includes_rate_limit_headers(client):
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401
    assert r.headers.get("x-ratelimit-limit")
    assert r.headers.get("x-ratelimit-remaining") is not None
    assert r.headers.get("x-ratelimit-reset")
    assert r.headers.get("x-ratelimit-policy")


def test_login_invalid_credentials_includes_rate_limit_headers(client):
    r = client.post(
        "/auth/login",
        data={"email": "none@x.com", "password": "wrongpass"},
        follow_redirects=False,
    )
    assert r.status_code == 401
    assert "Email ou senha inválidos." in r.text
    assert r.headers.get("x-ratelimit-limit")
    assert r.headers.get("x-ratelimit-remaining") is not None
    assert r.headers.get("x-ratelimit-reset")
    assert r.headers.get("x-ratelimit-policy")


def test_register_duplicate_email_includes_rate_limit_headers(client):
    client.post(
        "/auth/register",
        data={"email": "dup@x.com", "name": "Dup", "password": "password123"},
        follow_redirects=False,
    )
    r = client.post(
        "/auth/register",
        data={"email": "dup@x.com", "name": "Dup2", "password": "password123"},
        follow_redirects=False,
    )
    assert r.status_code == 400
    assert "Não foi possível criar a conta com esses dados." in r.text
    assert r.headers.get("x-ratelimit-limit")
    assert r.headers.get("x-ratelimit-remaining") is not None
    assert r.headers.get("x-ratelimit-reset")
    assert r.headers.get("x-ratelimit-policy")


def test_forgot_password_includes_rate_limit_headers(client):
    r = client.post("/auth/forgot", data={"email": "unknown@x.com"}, follow_redirects=False)
    assert r.status_code == 200
    assert r.headers.get("x-ratelimit-limit")
    assert r.headers.get("x-ratelimit-remaining") is not None
    assert r.headers.get("x-ratelimit-reset")
    assert r.headers.get("x-ratelimit-policy")


def test_protected_menu_pages_redirect_to_login_when_logged_out(client):
    paths = [
        "/account",
        "/accounts",
        "/categories",
        "/transactions",
        "/recurring",
        "/budgets",
        "/goals",
        "/dashboard",
        "/reports",
        "/notifications",
        "/audit",
    ]
    for path in paths:
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303
        location = r.headers.get("location", "")
        assert location.startswith("/auth/login?msg=")


def test_protected_page_htmx_request_sets_hx_redirect_when_logged_out(client):
    r = client.get("/dashboard", headers={"HX-Request": "true"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location", "").startswith("/auth/login?msg=")
    assert r.headers.get("hx-redirect", "").startswith("/auth/login?msg=")


def test_protected_page_htmx_request_with_invalid_token_sets_hx_redirect(client):
    client.cookies.set("access_token", "invalid.token.value")
    r = client.get("/dashboard", headers={"HX-Request": "true"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location", "").startswith("/auth/login?msg=")
    assert r.headers.get("hx-redirect", "").startswith("/auth/login?msg=")