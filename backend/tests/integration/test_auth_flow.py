"""Integration: health, guest, and OTP login. Requires PostgreSQL."""
import pytest

from ._helpers import login

pytestmark = pytest.mark.integration


async def test_health(client):
    r = await client.get("http://test/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_guest_login(client):
    r = await client.post("/auth/guest")
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["is_guest"] is True


async def test_otp_login_issues_tokens(client, _engine):
    body = await login(client, _engine, "+919000000100")
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["is_guest"] is False
    # /auth/me works with the issued token
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert "customer" in me.json()["roles"]


async def test_refresh_rotation(client, _engine):
    body = await login(client, _engine, "+919000000101")
    r = await client.post("/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert r.status_code == 200
    # old refresh token is now revoked → reuse must fail
    reuse = await client.post("/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert reuse.status_code == 401
