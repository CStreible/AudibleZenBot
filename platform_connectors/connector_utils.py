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
import time
from core.logger import get_logger

logger = get_logger('connector_utils')


def safe_emit(signal, *args, **kwargs):
    """Safely emit a PyQt signal, swallowing RuntimeError when the
    underlying QObject has been deleted during shutdown.
    """
    # Lightweight tracing: record attempted emits to a local diagnostics file
    try:
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, 'connector_emit_attempts.log'), 'a', encoding='utf-8', errors='replace') as f:
                f.write(f"{time.time():.3f} ATTEMPT emit signal={repr(signal)} args={repr(args)[:200]} kwargs_keys={list(kwargs.keys())}\n")
        except Exception:
            pass
        signal.emit(*args, **kwargs)
        try:
            with open(os.path.join(log_dir, 'connector_emit_attempts.log'), 'a', encoding='utf-8', errors='replace') as f:
                f.write(f"{time.time():.3f} SUCCESS emit signal={repr(signal)}\n")
        except Exception:
            pass
    except RuntimeError:
        # QObject already deleted; ignore
        try:
            with open(os.path.join(log_dir, 'connector_emit_attempts.log'), 'a', encoding='utf-8', errors='replace') as f:
                f.write(f"{time.time():.3f} RUNTIME_ERROR emit signal={repr(signal)}\n")
        except Exception:
            pass
        return
    except Exception as e:
        try:
            with open(os.path.join(log_dir, 'connector_emit_attempts.log'), 'a', encoding='utf-8', errors='replace') as f:
                f.write(f"{time.time():.3f} EXCEPTION emit signal={repr(signal)} err={repr(e)}\n")
        except Exception:
            pass
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

    # Try instance-level attribute first; some QObject/signal implementations
    # may raise or behave oddly with `hasattr()` in cross-thread contexts.
    try:
        sig_obj = None
        try:
            sig_obj = getattr(connector, 'message_received_with_metadata', None)
        except Exception:
            sig_obj = None

        if sig_obj is not None:
            try:
                safe_emit(sig_obj, platform, username, message, metadata)
            except Exception:
                # Last-ditch: try to retrieve the signal descriptor from the
                # class and bind it to the instance (some PyQt signal objects
                # require descriptor access via the class).
                try:
                    desc = getattr(type(connector), 'message_received_with_metadata', None)
                    if desc is not None and hasattr(desc, '__get__'):
                        bound = desc.__get__(connector, type(connector))
                        safe_emit(bound, platform, username, message, metadata)
                    else:
                        logger.debug("emit_chat: message_received_with_metadata descriptor unavailable on class")
                except Exception:
                    logger.exception("emit_chat: failed to emit via class descriptor fallback")
        else:
            logger.debug("emit_chat: instance has no message_received_with_metadata attribute (getattr returned None)")
            # Additional diagnostics: enumerate ChatManager instances and their
            # connector instance ids so we can correlate which connector the
            # ChatManager wired vs. the connector that is attempting to emit.
            try:
                import gc, traceback, threading, datetime
                diag = []
                diag.append(f"emit_chat_diag: emitter_connector_id={id(connector)} thread={threading.get_ident()} time={datetime.datetime.utcnow().isoformat()}\n")
                # small stack snapshot of caller
                stack = ''.join(traceback.format_stack(limit=8))
                diag.append("caller_stack:\n")
                diag.append(stack)
                # Attempt to locate ChatManager instances
                try:
                    from core.chat_manager import ChatManager
                    managers = [o for o in gc.get_objects() if isinstance(o, ChatManager)]
                except Exception:
                    managers = []
                if managers:
                    for m in managers:
                        try:
                            cids = {k: id(v) for k, v in getattr(m, 'connectors', {}).items()}
                            diag.append(f"Found ChatManager id={id(m)} connectors={cids}\n")
                        except Exception:
                            diag.append(f"Found ChatManager id={id(m)} but failed to read connectors\n")
                else:
                    diag.append("No ChatManager instances found via gc.get_objects()\n")
                # Write diagnostics to a dedicated file so it's easy to find
                try:
                    log_dir = os.path.join(os.getcwd(), 'logs')
                    os.makedirs(log_dir, exist_ok=True)
                    with open(os.path.join(log_dir, 'connector_creation_diagnostics.log'), 'a', encoding='utf-8', errors='replace') as f:
                        f.write('\n'.join(diag) + '\n' + ('-'*60) + '\n')
                except Exception:
                    pass
                # Also emit the diagnostics to the main logger at INFO level
                logger.info(''.join(diag))
            except Exception:
                logger.exception('emit_chat: failed while writing extended diagnostics')
    except Exception:
        logger.exception("emit_chat: unexpected error probing message_received_with_metadata")

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
