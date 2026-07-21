"""Tests for transactional email HTML escaping."""

from app.services.email.templates import password_reset_email


def test_password_reset_email_plain_name_ok():
    rendered = password_reset_email(
        user_name="Ana",
        reset_url="https://app.example.com/reset?token=abc",
        expires_minutes=30,
    )
    assert "Olá Ana," in rendered.html
    assert "Olá Ana," in rendered.text
    assert 'href="https://app.example.com/reset?token=abc"' in rendered.html
    assert "https://app.example.com/reset?token=abc" in rendered.text


def test_password_reset_email_escapes_html_injection_in_name():
    malicious = 'Ana<img src=x onerror=alert(1)>'
    reset_url = "https://app.example.com/reset?token=abc"
    rendered = password_reset_email(
        user_name=malicious,
        reset_url=reset_url,
        expires_minutes=30,
    )

    assert "<img" not in rendered.html
    assert "&lt;img" in rendered.html
    assert "&gt;" in rendered.html

    # Plain text keeps the raw name readable
    assert malicious in rendered.text
    assert reset_url in rendered.text
