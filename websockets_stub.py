"""Local stub for the `websockets` package used when the real dependency
is not available. This is the original stub content moved to a separate
module so the package import resolution can prefer the installed
`websockets` package when present.
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
