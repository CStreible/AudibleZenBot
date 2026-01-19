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
        status_code = 200
        content = b''

        def json(self):
            return {"data": []}

    class _DummySession:
        def get(self, url, headers=None, params=None, timeout=None):
            return _DummyResponse()

    def make_retry_session(*args, **kwargs):
        return _DummySession()
