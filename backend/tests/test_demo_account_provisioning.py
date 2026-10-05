from app.core.config import Settings
from app.db.provision_demo_users import (
    CONFIRMATION_TEXT,
    provision_demo_users,
    require_development_opt_in,
)
from app.db.session import SessionLocal
from app.models import User, UserRole
from app.services.security import verify_password


def test_provisioner_requires_development_and_explicit_opt_in():
    require_development_opt_in("development", {"SMARTER_ALLOW_DEMO_PASSWORD_RESET": "true"})
    for app_env, environment in (
        ("production", {"SMARTER_ALLOW_DEMO_PASSWORD_RESET": "true"}),
        ("development", {}),
    ):
        try:
            require_development_opt_in(app_env, environment)
        except RuntimeError:
            continue
        raise AssertionError("Provisioning guard should reject this configuration")


def test_provisioner_hashes_passwords_and_preserves_roles(capsys):
    settings = Settings(app_env="development")
    passwords = iter(["admin-demo-password-123", "admin-demo-password-123", "triage-demo-password-456", "triage-demo-password-456", "authority-demo-password-789", "authority-demo-password-789"])
    with SessionLocal() as db:
        result = provision_demo_users(
            db,
            settings,
            {"SMARTER_ALLOW_DEMO_PASSWORD_RESET": "true"},
            confirm=lambda _: CONFIRMATION_TEXT,
            prompt_password=lambda _: next(passwords),
        )
        assert result == {"created": 3, "passwords_reset": 0}
        records = db.query(User).order_by(User.email).all()
        assert [(user.email, user.role) for user in records] == [
            ("admin@example.com", UserRole.ADMIN),
            ("authority@example.com", UserRole.HEALTH_AUTHORITY),
            ("triage@example.com", UserRole.TRIAGE_NURSE),
        ]
        for user, password in zip(records, ["admin-demo-password-123", "authority-demo-password-789", "triage-demo-password-456"]):
            assert password not in user.password_hash
            assert verify_password(password, user.password_hash)
    captured = capsys.readouterr()
    assert "admin-demo-password-123" not in captured.out
    assert "authority-demo-password-789" not in captured.out
    assert "triage-demo-password-456" not in captured.out


def test_manual_reset_changes_passwords_without_changing_roles():
    settings = Settings(app_env="development")
    first_passwords = iter(["admin-demo-password-123", "admin-demo-password-123", "triage-demo-password-456", "triage-demo-password-456", "authority-demo-password-789", "authority-demo-password-789"])
    second_passwords = iter(["admin-reset-password-1234", "admin-reset-password-1234", "triage-reset-password-5678", "triage-reset-password-5678", "authority-reset-password-9012", "authority-reset-password-9012"])
    opt_in = {"SMARTER_ALLOW_DEMO_PASSWORD_RESET": "true"}
    with SessionLocal() as db:
        created = provision_demo_users(db, settings, opt_in, confirm=lambda _: CONFIRMATION_TEXT, prompt_password=lambda _: next(first_passwords))
        assert created["created"] == 3
        reset = provision_demo_users(db, settings, opt_in, confirm=lambda _: CONFIRMATION_TEXT, prompt_password=lambda _: next(second_passwords))
        assert reset == {"created": 0, "passwords_reset": 3}
        roles = {user.email: UserRole(user.role) for user in db.query(User).all()}
        assert roles == {
            "admin@example.com": UserRole.ADMIN,
            "triage@example.com": UserRole.TRIAGE_NURSE,
            "authority@example.com": UserRole.HEALTH_AUTHORITY,
        }
        assert verify_password("admin-reset-password-1234", db.query(User).filter_by(email="admin@example.com").one().password_hash)


def test_provisioner_refuses_wrong_confirmation_without_database_changes():
    settings = Settings(app_env="development")
    with SessionLocal() as db:
        try:
            provision_demo_users(
                db,
                settings,
                {"SMARTER_ALLOW_DEMO_PASSWORD_RESET": "true"},
                confirm=lambda _: "no",
                prompt_password=lambda _: "unused-password-value",
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("Provisioning must require the exact confirmation phrase")
        assert db.query(User).count() == 0