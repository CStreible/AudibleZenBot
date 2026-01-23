"""
Shared helper to create a requests.Session configured with urllib3 Retry
for transient network errors. Import `make_retry_session` in connectors.

This module will attempt to use the real installed `requests` and
`urllib3.util.Retry`/`requests.adapters.HTTPAdapter`. If those pieces
are not available (for example in isolated test environments where the
in-repo `requests` shim is active), it falls back to a minimal dummy
session implementation so callers don't need to guard for missing
network libs.
"""
from typing import Optional
import importlib
import os
from core.env import is_test

# Try to import the real requests + retry helpers. If anything in that
# import chain fails, fall back to the dummy session implementation.
_have_requests_with_retries = False
try:
    import requests
    try:
        from requests.adapters import HTTPAdapter  # type: ignore
        from urllib3.util import Retry  # type: ignore
        _have_requests_with_retries = True
    except Exception:
        _have_requests_with_retries = False
except Exception:
    requests = None
    _have_requests_with_retries = False

# If initial attempt failed because an in-repo shim shadowed the real
# `requests`, try to import the real installed package by temporarily
# removing the current working directory from `sys.path` and retrying.
if not _have_requests_with_retries:
    try:
        import sys, os
        cwd = os.path.abspath(os.getcwd())
        _orig_sys_path = list(sys.path)
        sys.path = [p for p in sys.path if p and os.path.abspath(p) != cwd]
        try:
            import importlib
            # Remove any already-imported local 'requests' modules so the
            # re-import picks up the installed package after we adjusted
            # sys.path.
            for _m in ('requests', 'requests.adapters', 'urllib3', 'urllib3.util'):
                if _m in sys.modules:
                    try:
                        del sys.modules[_m]
                    except Exception:
                        pass
            real_requests = importlib.import_module('requests')
            try:
                from requests.adapters import HTTPAdapter  # type: ignore
                from urllib3.util import Retry  # type: ignore
                requests = real_requests
                _have_requests_with_retries = True
            except Exception:
                _have_requests_with_retries = False
        finally:
            sys.path[:] = _orig_sys_path
    except Exception:
        _have_requests_with_retries = False

if _have_requests_with_retries:
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

        # Wrap session.request to log Twitch API calls (URL, params, masked headers)
        try:
            from core.logger import get_logger
            tlogger = get_logger('TwitchAPI')
            orig_request = session.request

            def _logged_request(method, url, **kwargs):
                try:
                    if isinstance(url, str) and 'twitch.tv' in url:
                        headers = kwargs.get('headers') or {}
                        params = kwargs.get('params') or {}
                        # mask Authorization for logs
                        hcopy = dict(headers) if isinstance(headers, dict) else dict(headers or {})
                        if 'Authorization' in hcopy and isinstance(hcopy['Authorization'], str):
                            try:
                                hcopy['Authorization'] = hcopy['Authorization'][:8] + '...'
                            except Exception:
                                hcopy['Authorization'] = '***'
                        tlogger.debug(f"Twitch API Request: method={method} url={url} params={params} headers={hcopy}")
                except Exception:
                    pass
                return orig_request(method, url, **kwargs)

            session.request = _logged_request
        except Exception:
            pass

        return session
    # `requests` is importable but the HTTPAdapter/Retry helpers weren't
    # available. Return a plain Session (no retry adapter) so callers can
    # still perform HTTP requests without the dummy session behavior.
    def make_retry_session(*args, **kwargs):
        session = requests.Session()
        try:
            from core.logger import get_logger
            tlogger = get_logger('TwitchAPI')
            orig_request = session.request

            def _logged_request(method, url, **kwargs):
                try:
                    if isinstance(url, str) and 'twitch.tv' in url:
                        headers = kwargs.get('headers') or {}
                        params = kwargs.get('params') or {}
                        hcopy = dict(headers) if isinstance(headers, dict) else dict(headers or {})
                        if 'Authorization' in hcopy and isinstance(hcopy['Authorization'], str):
                            try:
                                hcopy['Authorization'] = hcopy['Authorization'][:8] + '...'
                            except Exception:
                                hcopy['Authorization'] = '***'
                        tlogger.debug(f"Twitch API Request: method={method} url={url} params={params} headers={hcopy}")
                except Exception:
                    pass
                return orig_request(method, url, **kwargs)

            session.request = _logged_request
        except Exception:
            pass
        return session

else:
    # In test mode we provide a minimal fallback session so tests don't
    # require the real `requests` package. In production we require the
    # real packages to be installed to avoid silent no-op networking.
    if is_test():
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
    else:
        raise ImportError(
            "Required network packages not available: please install 'requests' and 'urllib3', "
            "and ensure no local 'requests.py' or similar stubs are shadowing the real packages.\n"
            "If you need to run tests without network libs, run with AUDIBLEZENBOT_ENV=test or set AUDIBLEZENBOT_CI=1."
        )
