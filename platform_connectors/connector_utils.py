"""Connector emission helpers.

Provides a small compatibility shim `emit_chat` that emits the canonical
four-argument message signal `(platform, username, message, metadata)` while
also preserving legacy emits for connectors that other code may still
listen to.
"""
from typing import Any
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Callable, Optional
import os


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


def startup_allowed() -> bool:
    """Return True if connectors are allowed to start network threads/workers.

    Honor the environment variable `AUDIBLEZENBOT_CI`. When set to '1',
    connectors should avoid starting background threads or making outbound
    network calls during test/CI runs.
    """
    return os.environ.get('AUDIBLEZENBOT_CI', '') != '1'


@asynccontextmanager
async def connect_with_retry(connect_callable: Callable, uri: str, *args, retries: int = 5, backoff_factor: float = 0.5, logger: Optional[logging.Logger] = None, **kwargs):
    """Async context manager that attempts to establish a websocket connection
    using ``connect_callable`` (typically ``websockets.connect``). Retries
    on failure with exponential backoff and logs attempts.

    Usage:
        async with connect_with_retry(websockets.connect, uri) as ws:
            ...
    """
    if logger is None:
        logger = logging.getLogger('platform_connectors')

    attempt = 0
    last_exc = None
    while attempt < max(1, int(retries)):
        try:
            # connect_callable should return an async context manager
            cm = connect_callable(uri, *args, **kwargs)
            async with cm as ws:
                yield ws
                return
        except Exception as e:
            last_exc = e
            attempt += 1
            if attempt >= retries:
                break
            wait = backoff_factor * (2 ** (attempt - 1))
            try:
                logger.warning(f"[connectors][WARN] websockets connect failed attempt {attempt}/{retries} for {uri}: {e}; retrying in {wait:.1f}s")
            except Exception:
                pass
            try:
                await asyncio.sleep(wait)
            except asyncio.CancelledError:
                raise

    try:
        logger.error(f"[connectors][ERROR] websockets connect failed after {retries} attempts for {uri}: {last_exc}")
    except Exception:
        pass
    if last_exc:
        raise last_exc
    raise RuntimeError("websockets.connect failed without exception")

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
