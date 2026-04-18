def test_account_timezone_update(client):
    r = client.post(
        "/auth/register",
        data={"email": "u1@example.com", "name": "U1", "password": "password123"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = client.post("/account/timezone", data={"timezone": "UTC"}, follow_redirects=False)
    assert r.status_code == 303

    r = client.get("/account")
    assert r.status_code == 200
    assert "UTC" in r.text

