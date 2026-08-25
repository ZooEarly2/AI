def test_health_check_needs_no_api_key(client):
    """헬스체크는 인증 밖에 있다 — API_KEY 를 채운 배포에서도 그대로 돌아야 한다."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
