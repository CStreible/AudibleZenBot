"""Minimal local stub for the `websockets` package used in tests and
local development when the real `websockets` package isn't available.

This module intentionally provides a small async-compatible API surface
so connector code (which uses `async with websockets.connect(...)` and
`except websockets.exceptions.*`) can run without the real dependency.

Notes:
- `connect()` is a synchronous factory that returns an object implementing
  the asynchronous context manager protocol (async __aenter__/__aexit__).
- An `exceptions` namespace is provided with commonly used exception
  classes so `websockets.exceptions.ConnectionClosed` etc. resolve.
"""

class WebSocketException(Exception):
    """Base exception for the stub."""


class ConnectionClosed(WebSocketException):
    pass


class _ExceptionsNamespace:
    WebSocketException = WebSocketException
    ConnectionClosed = ConnectionClosed


exceptions = _ExceptionsNamespace()


def connect(uri, *args, **kwargs):
    """Return a simple async context manager that mimics a websocket
    connection. This object supports `async with` and has `recv`/`send`
    coroutines for basic interoperability in tests.
    """
    class _Conn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def recv(self):
            # Return an empty string to indicate no data by default
            return ''

        async def send(self, data):
            return None

    return _Conn()
