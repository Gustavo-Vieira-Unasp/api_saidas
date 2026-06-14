def test_schedule_validation(client, auth_headers):
    bad = client.post(
        "/schedules",
        json={
            "name": "Bad",
            "trigger_type": "once",
            "enabled": True,
        },
        headers=auth_headers,
    )
    assert bad.status_code == 422

    good = client.post(
        "/schedules",
        json={
            "name": "Daily gym",
            "template_id": None,
            "payload": {"destino": "Academia"},
            "trigger_type": "daily",
            "hour": 18,
            "minute": 0,
            "date_strategy": "today",
            "enabled": True,
        },
        headers=auth_headers,
    )
    assert good.status_code == 201
    schedule_id = good.json()["id"]

    updated = client.put(
        f"/schedules/{schedule_id}",
        json={"enabled": False},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False

    deleted = client.delete(f"/schedules/{schedule_id}", headers=auth_headers)
    assert deleted.status_code == 204
