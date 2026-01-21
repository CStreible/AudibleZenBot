"""Connector emission helpers.

Provides a small compatibility shim `emit_chat` that emits the canonical
four-argument message signal `(platform, username, message, metadata)` while
also preserving legacy emits for connectors that other code may still
listen to.
"""
from typing import Any, Callable, Optional
import asyncio
import logging
from contextlib import asynccontextmanager
import os


def safe_emit(signal, *args, **kwargs):
    """Safely emit a PyQt signal, swallowing RuntimeError when the
    underlying QObject has been deleted during shutdown.
    """
    try:
        signal.emit(*args, **kwargs)
    except RuntimeError:
        # QObject already deleted; ignore
        return
    except Exception:
        return


def emit_chat(connector: Any, platform: str, username: str, message: str, metadata: Optional[dict] = None) -> None:
    """Emit a canonical chat message while preserving legacy signals.

    This helper ensures connectors can emit both the modern
    `message_received_with_metadata(platform, username, message, metadata)`
    as well as legacy `message_received(platform, username, message)` or
    two-argument variants for backward compatibility.
    """
    if metadata is None:
        metadata = {}

    try:
        if hasattr(connector, 'message_received_with_metadata'):
            safe_emit(connector.message_received_with_metadata, platform, username, message, metadata)
    except Exception:
        pass

    try:
        if hasattr(connector, 'message_received'):
            safe_emit(connector.message_received, platform, username, message)
    except Exception:
        pass

    # Legacy two-arg signal
    try:
        if hasattr(connector, 'message_signal'):
            try:
                safe_emit(connector.message_signal, username, message)
            except TypeError:
                try:
                    safe_emit(connector.message_signal, username, message, metadata)
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
    """
    if logger is None:
        logger = logging.getLogger('platform_connectors')

    attempt = 0
    max_retries = max(1, int(retries))
    last_exc = None
    while attempt < max_retries:
        try:
            cm = connect_callable(uri, *args, **kwargs)
            async with cm as ws:
                yield ws
                return
        except Exception as e:
            last_exc = e
            attempt += 1
            wait = backoff_factor * (2 ** (attempt - 1))
            logger.warning(f"websockets connect failed attempt {attempt} for {uri}: {e}; retrying in {wait}s")
            if attempt >= max_retries:
                break
            try:
                await asyncio.sleep(wait)
            except Exception:
                # If sleep is interrupted, proceed to next retry
                pass
    # Log an error about exhausted retries for callers/tests that expect it
    try:
        logger.error(f"websockets connect failed after {max_retries} attempts for {uri}: {last_exc}")
    except Exception:
        pass

    raise RuntimeError(f"Failed to connect to {uri} after {max_retries} attempts")
