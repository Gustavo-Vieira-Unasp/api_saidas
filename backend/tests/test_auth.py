def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert "scheduler_running" in body


def test_register_and_login(client):
    reg = client.post(
        "/auth/register",
        json={
            "ra": "999001",
            "password": "pass1234",
            "profile": "Aluno Graduação",
        },
    )
    assert reg.status_code == 201
    assert reg.json()["ra"] == "999001"
    assert reg.json()["has_unasp_credentials"] is True

    dup = client.post(
        "/auth/register",
        json={"ra": "999001", "password": "other"},
    )
    assert dup.status_code == 409

    bad_login = client.post(
        "/auth/login",
        data={"username": "999001", "password": "wrong"},
    )
    assert bad_login.status_code == 401

    ok = client.post(
        "/auth/login",
        data={"username": "999001", "password": "pass1234"},
    )
    assert ok.status_code == 200
    assert "access_token" in ok.json()


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_update_profile_and_password(client, auth_headers):
    profile = client.put(
        "/auth/me/profile",
        json={"profile": "Funcionário"},
        headers=auth_headers,
    )
    assert profile.status_code == 200
    assert profile.json()["unasp_profile"] == "Funcionário"

    bad_pw = client.put(
        "/auth/me/password",
        json={"current_password": "wrong", "new_password": "newsecret"},
        headers=auth_headers,
    )
    assert bad_pw.status_code == 400

    ok_pw = client.put(
        "/auth/me/password",
        json={"current_password": "secret123", "new_password": "newsecret"},
        headers=auth_headers,
    )
    assert ok_pw.status_code == 200

    login = client.post(
        "/auth/login",
        data={"username": "123456", "password": "newsecret"},
    )
    assert login.status_code == 200
