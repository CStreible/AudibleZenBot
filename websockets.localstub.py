"""Renamed local stub for `websockets` to avoid shadowing the real package.

Tests can still import this explicitly if needed; production will import
the real `websockets` package from site-packages.
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
