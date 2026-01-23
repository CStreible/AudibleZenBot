# Lightweight stub of the 'requests' package for CI/test environments lacking requests.
class Response:
    def __init__(self, status_code=200, data=None, content=b""):
        self.status_code = status_code
        self._data = data if data is not None else {"data": []}
        self.content = content

    def json(self):
        return self._data

    @property
    def text(self):
        try:
            return self.content.decode('utf-8')
        except Exception:
            return str(self._data)

    def raise_for_status(self):
        """Mimic requests.Response.raise_for_status()

        Raises an HTTPError-like exception when status_code indicates error.
        """
        if 400 <= int(self.status_code):
            raise Exception(f"HTTP {self.status_code} Error: {self.text}")

    @property
    def ok(self):
        return 200 <= int(self.status_code) < 400


class Session:
    def get(self, url, headers=None, params=None, timeout=None, **kwargs):
        return Response()

    def post(self, url, headers=None, params=None, timeout=None, **kwargs):
        return Response()


def get(url, **kwargs):
    return Session().get(url, **kwargs)


def post(url, **kwargs):
    return Session().post(url, **kwargs)


class exceptions:
    RequestException = Exception
    ConnectionError = Exception
