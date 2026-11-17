import socket

import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """No test may reach a real API (keys or not)."""
    def refuse(*a, **k):
        raise AssertionError("network access in tests is not allowed")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
