import pytest


@pytest.fixture(autouse=True)
def fixed_user(monkeypatch):
    monkeypatch.setattr("getpass.getuser", lambda: "testuser")