from datetime import UTC
from unittest.mock import AsyncMock, patch

from app.automation.pensionato import SubmitResult
from app.services.submission import SubmissionError


@patch("app.services.submission.submit_exit", new_callable=AsyncMock)
def test_send_exit(mock_submit, client, auth_headers):
    mock_submit.return_value = SubmitResult(
        status="sent", message="Submitted successfully", screenshot_path=None
    )

    response = client.post(
        "/exits/send",
        json={
            "payload": {
                "dormir_fora": "Não",
                "destino": "Academia",
                "motivo": "Passeio",
                "com_quem": "Sozinho",
                "data_saida": "2026-06-20",
                "hora_saida": "18:00",
                "hora_retorno": "21:00",
            },
            "dry_run": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    mock_submit.assert_awaited_once()


@patch("app.api.routes.exits.run_submission_async", new_callable=AsyncMock)
def test_batch_partial_failure(mock_run, client, auth_headers):
    from datetime import datetime

    from app.models.exit_request import ExitRequest

    ok_record = ExitRequest(
        id=1,
        user_id=1,
        schedule_id=None,
        payload={"data_saida": "2026-06-16"},
        status="sent",
        message="ok",
        source="batch",
        screenshot_path=None,
        created_at=datetime.now(UTC),
    )

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise SubmissionError("day 2 failed")
        return ok_record

    mock_run.side_effect = side_effect

    response = client.post(
        "/exits/batch",
        json={
            "payload": {
                "dormir_fora": "Não",
                "destino": "X",
                "motivo": "Passeio",
                "com_quem": "Sozinho",
                "hora_saida": "18:00",
                "hora_retorno": "21:00",
            },
            "start_date": "2026-06-16",
            "end_date": "2026-06-17",
            "weekdays_only": True,
            "dry_run": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["sent"]) == 1
    assert len(body["failed"]) == 1
    assert body["failed"][0]["error"] == "day 2 failed"


def test_list_exits_filter(client, auth_headers):
    listing = client.get("/exits?status=sent", headers=auth_headers)
    assert listing.status_code == 200
    assert isinstance(listing.json(), list)
