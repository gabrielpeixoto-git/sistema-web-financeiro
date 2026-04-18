def test_audit_page_requires_login(client):
    r = client.get("/audit", follow_redirects=False)
    assert r.status_code == 303


def test_audit_page_lists_login_event(client):
    client.post(
        "/auth/register",
        data={"email": "u1@example.com", "name": "U1", "password": "password123"},
        follow_redirects=False,
    )
    client.post("/auth/login", data={"email": "u1@example.com", "password": "password123"})

    r = client.get("/audit")
    assert r.status_code == 200
    assert "auth.login" in r.text

