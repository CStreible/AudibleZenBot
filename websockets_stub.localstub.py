"""Local stub for the `websockets` package used when the real dependency
is not available. This file is a renamed copy so the top-level
`websockets.py` doesn't shadow the installed package.
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
    class _Conn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def recv(self):
            return ''

        async def send(self, data):
            return None

    return _Conn()
