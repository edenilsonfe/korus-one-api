"""Caregiver email validation — blank ok, invalid rejected."""

import pytest
from pydantic import ValidationError

from app.schemas.patient import CaregiverCreate, CaregiverUpdate


def test_caregiver_create_allows_blank_email():
    c = CaregiverCreate(name="Ana", email="")
    assert c.email == ""


def test_caregiver_create_normalizes_valid_email():
    c = CaregiverCreate(name="Ana", email="  Mae@Example.COM ")
    # email-validator lowercases the domain portion
    assert c.email == "Mae@example.com"


def test_caregiver_create_rejects_invalid_email():
    with pytest.raises(ValidationError):
        CaregiverCreate(name="Ana", email="not-an-email")


def test_caregiver_create_rejects_control_chars():
    with pytest.raises(ValidationError):
        CaregiverCreate(name="Ana", email="a\nb@example.com")


def test_caregiver_update_none_passthrough():
    u = CaregiverUpdate(email=None)
    assert u.email is None


def test_caregiver_update_validates_when_set():
    u = CaregiverUpdate(email="ok@example.com")
    assert u.email == "ok@example.com"
    with pytest.raises(ValidationError):
        CaregiverUpdate(email="bad")
