"""Connector emission helpers.

Provides a small compatibility shim `emit_chat` that emits the canonical
four-argument message signal `(platform, username, message, metadata)` while
also preserving legacy emits for connectors that other code may still
listen to.
"""
from typing import Any


def emit_chat(connector: Any, platform: str, username: str, message: str, metadata: dict | None = None) -> None:
    if metadata is None:
        metadata = {}

    # Preferred canonical emits
    try:
        if hasattr(connector, 'message_received_with_metadata'):
            try:
                connector.message_received_with_metadata.emit(platform, username, message, metadata)
            except Exception:
                pass
    except Exception:
        pass

    try:
        if hasattr(connector, 'message_received'):
            try:
                connector.message_received.emit(platform, username, message, metadata)
            except Exception:
                pass
    except Exception:
        pass

    # Backwards-compatible legacy emits (username, message[, metadata])
    try:
        if hasattr(connector, 'message_signal_with_metadata'):
            try:
                connector.message_signal_with_metadata.emit(username, message, metadata)
            except Exception:
                pass
    except Exception:
        pass

    try:
        if hasattr(connector, 'message_signal'):
            try:
                # Some legacy connectors expect two args
                connector.message_signal.emit(username, message)
            except TypeError:
                try:
                    connector.message_signal.emit(username, message, metadata)
                except Exception:
                    pass
            except Exception:
                pass
    except Exception:
        pass
