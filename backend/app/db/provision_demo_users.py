"""Explicit development-only creation/reset of the three documented demo users."""

from __future__ import annotations

import getpass
import os
from collections.abc import Callable, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models import User, UserRole
from app.services.security import hash_password

OPT_IN_VARIABLE = "SMARTER_ALLOW_DEMO_PASSWORD_RESET"
CONFIRMATION_TEXT = "RESET SMARTER DEVELOPMENT DEMO ACCOUNTS"
MIN_PASSWORD_LENGTH = 14

DEMO_ACCOUNTS = (
    ("demo_admin_email", UserRole.ADMIN, "SmartER Administrator"),
    ("demo_triage_email", UserRole.TRIAGE_NURSE, "Demo Triage Nurse"),
    ("demo_health_authority_email", UserRole.HEALTH_AUTHORITY, "Demo Health Authority"),
)


def require_development_opt_in(app_env: str, environment: Mapping[str, str]) -> None:
    if app_env.strip().lower() not in {"development", "dev", "local"}:
        raise RuntimeError("Demo account provisioning is disabled unless APP_ENV is development, dev, or local.")
    if environment.get(OPT_IN_VARIABLE, "").strip().lower() != "true":
        raise RuntimeError(f"Set {OPT_IN_VARIABLE}=true for this one-time command to continue.")


def provision_demo_users(
    db: Session,
    settings: Settings,
    environment: Mapping[str, str],
    *,
    confirm: Callable[[str], str] = input,
    prompt_password: Callable[[str], str] = getpass.getpass,
) -> dict[str, int]:
    """Create missing demo users or reset their passwords after explicit confirmation."""
    require_development_opt_in(settings.app_env, environment)
    emails = [(getattr(settings, setting_name).strip().lower(), role, full_name) for setting_name, role, full_name in DEMO_ACCOUNTS]
    if any(not email for email, _, _ in emails) or len({email for email, _, _ in emails}) != len(DEMO_ACCOUNTS):
        raise RuntimeError("Demo account emails must be set and unique in local configuration.")

    print("This will create or reset only the documented SmartER development demo accounts.")
    print("Passwords are entered hidden and stored only as Argon2 hashes.")
    if confirm(f"Type '{CONFIRMATION_TEXT}' to continue: ") != CONFIRMATION_TEXT:
        raise RuntimeError("Confirmation did not match; no accounts were changed.")

    passwords: dict[str, str] = {}
    for email, role, _ in emails:
        first = prompt_password(f"New password for {email} ({role.value}): ")
        second = prompt_password(f"Confirm password for {email}: ")
        if len(first) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password for {email} must be at least {MIN_PASSWORD_LENGTH} characters.")
        if first != second:
            raise ValueError(f"Password confirmation did not match for {email}.")
        passwords[email] = first

    created = 0
    updated = 0
    try:
        for email, role, full_name in emails:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, full_name=full_name, password_hash=hash_password(passwords[email]), role=role, is_active=True)
                db.add(user)
                created += 1
                continue
            if UserRole(user.role) != role:
                raise RuntimeError(f"Existing account {email} has an unexpected role; no role changes were made.")
            if not user.is_active:
                raise RuntimeError(f"Existing account {email} is inactive; provisioning will not reactivate accounts.")
            user.password_hash = hash_password(passwords[email])
            updated += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"created": created, "passwords_reset": updated}


def main() -> None:
    settings = get_settings()
    require_development_opt_in(settings.app_env, os.environ)
    with SessionLocal() as db:
        result = provision_demo_users(db, settings, os.environ)
    print(f"Provisioning complete: {result['created']} created, {result['passwords_reset']} passwords reset.")


if __name__ == "__main__":
    main()