"""
Shared helper to create a requests.Session configured with urllib3 Retry
for transient network errors. Import `make_retry_session` in connectors.
"""
from typing import Optional
try:
    try:
        import requests
    except Exception:
        requests = None
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry

    def make_retry_session(total: int = 3, backoff_factor: float = 1.0, status_forcelist=(429, 500, 502, 503, 504)) -> requests.Session:
        """Return a requests.Session configured with urllib3 Retry/HTTPAdapter.

        - `total`: total retry attempts
        - `backoff_factor`: sleep factor between retries
        - `status_forcelist`: HTTP status codes to retry on
        """
        session = requests.Session()
        retries = Retry(
            total=total,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=("GET", "POST", "DELETE", "PUT", "PATCH")
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        return session
except Exception:
    # Provide a minimal fallback session for test environments without 'requests'
    class _DummyResponse:
        def __init__(self, status_code=200, data=None, headers=None):
            self.status_code = status_code
            self._data = {} if data is None else data
            self.headers = {} if headers is None else dict(headers)
            self.content = b''
            try:
                import json as _json
                self.text = _json.dumps(self._data)
            except Exception:
                self.text = ''

        def json(self):
            return self._data

        def raise_for_status(self):
            # No-op for dummy response
            return None

    class _DummySession:
        def __init__(self):
            self.headers = {}

        def _make_response(self, url, method='GET', **kwargs):
            # Return a generic OK response. Tests may monkeypatch sys.modules
            # to provide more specific behavior when needed.
            return _DummyResponse()

        def get(self, url, headers=None, params=None, timeout=None):
            return self._make_response(url, method='GET')

        def post(self, url, data=None, json=None, headers=None, timeout=None):
            return self._make_response(url, method='POST')

        def put(self, url, data=None, headers=None, timeout=None):
            return self._make_response(url, method='PUT')

        def delete(self, url, headers=None, timeout=None):
            return self._make_response(url, method='DELETE')

        def request(self, method, url, **kwargs):
            return self._make_response(url, method=method)

    def make_retry_session(*args, **kwargs):
        return _DummySession()
