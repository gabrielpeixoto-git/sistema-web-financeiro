def test_notifications_filter_and_read_all(client):
    client.post(
        "/auth/register",
        data={"email": "u1@example.com", "name": "U1", "password": "password123"},
        follow_redirects=False,
    )
    r = client.get("/notifications", follow_redirects=False)
    assert r.status_code == 200
    assert 'action="/notifications/read_all"' in r.text
    assert 'name="kind"' in r.text

    r = client.get("/notifications?kind=daily_summary", follow_redirects=False)
    assert r.status_code == 200

    r = client.post("/notifications/read_all", data={"kind": "daily_summary"}, follow_redirects=False)
    assert r.status_code == 303

