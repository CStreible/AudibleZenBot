# Minimal stub for the 'websockets' package used in some tests.
class ConnectionClosed(Exception):
    pass

async def connect(uri, *args, **kwargs):
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
