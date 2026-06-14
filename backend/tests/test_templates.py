def test_template_crud(client, auth_headers):
    create = client.post(
        "/templates",
        json={
            "name": "Gym",
            "payload": {
                "dormir_fora": "Não",
                "destino": "Academia",
                "motivo": "Passeio",
                "com_quem": "Sozinho",
                "hora_saida": "18:00",
                "hora_retorno": "21:00",
            },
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    template_id = create.json()["id"]

    listing = client.get("/templates", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    updated = client.put(
        f"/templates/{template_id}",
        json={"name": "Gym updated", "payload": create.json()["payload"]},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Gym updated"

    deleted = client.delete(f"/templates/{template_id}", headers=auth_headers)
    assert deleted.status_code == 204

    missing = client.get(f"/templates/{template_id}", headers=auth_headers)
    assert missing.status_code == 404


def test_template_ownership(client, auth_headers):
    client.post(
        "/auth/register",
        json={"ra": "888001", "password": "pass888"},
    )
    other_token = client.post(
        "/auth/login",
        data={"username": "888001", "password": "pass888"},
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    created = client.post(
        "/templates",
        json={"name": "Mine", "payload": {"destino": "X"}},
        headers=auth_headers,
    ).json()

    forbidden = client.delete(
        f"/templates/{created['id']}",
        headers=other_headers,
    )
    assert forbidden.status_code == 404
