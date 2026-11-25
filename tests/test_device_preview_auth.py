"""DevTools can change User-Agent between page, token and fetch requests."""

import pytest

DESKTOP_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
PHONE_CHROME = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 Chrome/131.0.0.0 Mobile Safari/537.36"
DESKTOP_EDGE = DESKTOP_CHROME + " Edg/131.0.0.0"
PHONE_EDGE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1 EdgiOS/131.0.0.0"


@pytest.mark.parametrize(
    "desktop,phone",
    [(DESKTOP_CHROME, PHONE_CHROME), (DESKTOP_EDGE, PHONE_EDGE)],
    ids=["chrome-device-preview", "edge-device-preview"],
)
def test_switching_phone_preview_keeps_signed_in_session(browser, desktop, phone):
    client = browser.client
    # Starting from the existing sign-in, change device identity repeatedly.
    for agent in (desktop, phone, desktop, phone):
        response = client.get("/api/auth/me", headers={"User-Agent": agent})
        assert response.status_code == 200
        assert response.json["data"]["email"] == "student@example.com"
        assert (
            client.get("/dashboard", headers={"User-Agent": agent}).status_code == 200
        )


@pytest.mark.parametrize(
    "desktop,phone",
    [(DESKTOP_CHROME, PHONE_CHROME), (DESKTOP_EDGE, PHONE_EDGE)],
    ids=["chrome-device-preview", "edge-device-preview"],
)
def test_phone_login_survives_mixed_page_and_fetch_user_agents(browser, desktop, phone):
    client = browser.client
    browser.request("/auth/logout", "POST", {})
    assert client.get("/login", headers={"User-Agent": phone}).status_code == 200
    token = client.get("/api/auth/csrf", headers={"User-Agent": desktop}).json["data"][
        "csrf_token"
    ]
    result = client.post(
        "/api/auth/login",
        json={
            "email": "student@example.com",
            "password": "StrongPassword123!",
        },
        headers={"User-Agent": phone, "X-CSRFToken": token},
    )
    assert result.status_code == 200
    assert client.get("/dashboard", headers={"User-Agent": desktop}).status_code == 200
    assert client.get("/api/auth/me", headers={"User-Agent": phone}).status_code == 200
    assert (
        client.get("/api/profile", headers={"User-Agent": desktop}).status_code == 200
    )


def test_preview_identity_change_still_requires_password_for_credentials(browser):
    client = browser.client
    assert (
        client.get("/api/auth/me", headers={"User-Agent": PHONE_CHROME}).status_code
        == 200
    )
    token = client.get("/api/auth/csrf", headers={"User-Agent": PHONE_CHROME}).json[
        "data"
    ]["csrf_token"]
    headers = {"User-Agent": PHONE_CHROME, "X-CSRFToken": token}
    assert (
        client.patch(
            "/api/profile", json={"email": "updated@example.com"}, headers=headers
        ).status_code
        == 400
    )
    result = client.patch(
        "/api/profile",
        json={"email": "updated@example.com", "current_password": "StrongPassword123!"},
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json["data"]["email"] == "updated@example.com"
