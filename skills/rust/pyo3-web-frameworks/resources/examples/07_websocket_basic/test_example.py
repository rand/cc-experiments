"""Test suite for websocket_basic."""

import pytest
import websocket_basic


def test_websocket_handler():
    """Test WebSocket message handling."""
    handler = websocket_basic.WebSocketHandler()
    handler.add_message(b"hello")
    handler.add_message(b"world")

    messages = handler.get_messages()
    assert len(messages) == 2
    assert messages[0] == b"hello"


def test_process_ws_message():
    """Test WebSocket message processing."""
    result = websocket_basic.process_ws_message(b"test")
    assert len(result) == 4
    assert all(result[i] == b"test"[i] + 1 for i in range(4))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
