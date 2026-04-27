import pytest

from server.auth_db import AuthDb, hash_password, verify_password


def test_hash_and_verify_password_roundtrip():
    stored = hash_password("correct horse battery staple")
    assert stored != "correct horse battery staple"

    assert verify_password("correct horse battery staple", stored) is True
    assert verify_password("wrong password", stored) is False


def test_auth_db_create_and_authenticate(tmp_path):
    db_path = tmp_path / "auth.db"
    db = AuthDb(db_path)
    db.init()

    user = db.create_user(
        email="Alice@Example.com",
        password="super-secret-password",
    )

    assert user.id
    assert user.email == "alice@example.com"
    assert user.username == "alice"

    authed = db.authenticate(email="alice@example.com", password="super-secret-password")
    assert authed is not None
    assert authed.id == user.id

    assert db.authenticate(email="alice@example.com", password="wrong") is None

    fetched = db.get_user_by_id(user.id)
    assert fetched is not None
    assert fetched.email == "alice@example.com"


def test_auth_db_generated_username_is_unique(tmp_path):
    db_path = tmp_path / "auth.db"
    db = AuthDb(db_path)
    db.init()

    first = db.create_user(email="one@example.com", password="password-123")
    second = db.create_user(email="one@other.com", password="password-123")

    assert first.username == "one"
    assert second.username == "one1"


def test_auth_db_unique_email_or_username(tmp_path):
    db_path = tmp_path / "auth.db"
    db = AuthDb(db_path)
    db.init()

    db.create_user(email="one@example.com", username="one", password="password-123")

    with pytest.raises(ValueError):
        db.create_user(email="one@example.com", password="password-123")

    with pytest.raises(ValueError):
        db.create_user(email="two@example.com", username="one", password="password-123")


def test_auth_db_update_username(tmp_path):
    db_path = tmp_path / "auth.db"
    db = AuthDb(db_path)
    db.init()

    first = db.create_user(email="first@example.com", password="password-123")
    second = db.create_user(email="second@example.com", password="password-123")

    updated = db.update_username(user_id=first.id, username="renamed")
    assert updated.username == "renamed"

    with pytest.raises(ValueError):
        db.update_username(user_id=first.id, username=second.username)
