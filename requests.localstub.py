"""
Local shim for `requests` preserved as `.localstub` to avoid
shadowing the real `requests` package in production.

This file is a byte-for-byte copy of the original workspace shim
and is intentionally renamed so production runs import the real
`requests` from site-packages. Tests can still import the stub
explicitly if needed.
"""

import sys
import os
import importlib.util
import sysconfig

def _find_real_requests_init():
    candidates = []
    try:
        purelib = sysconfig.get_paths().get('purelib')
        if purelib:
            candidates.append(os.path.join(purelib, 'requests', '__init__.py'))
    except Exception:
        pass
    try:
        import site
        for p in site.getsitepackages():
            candidates.append(os.path.join(p, 'requests', '__init__.py'))
    except Exception:
        pass
    # Walk sys.path but skip current working directory to avoid this file
    cwd = os.path.abspath(os.getcwd())
    for p in sys.path:
        try:
            if not p:
                p = os.getcwd()
            p_abs = os.path.abspath(p)
            if p_abs == cwd:
                continue
            candidates.append(os.path.join(p_abs, 'requests', '__init__.py'))
        except Exception:
            pass
    for cand in candidates:
        try:
            if cand and os.path.exists(cand):
                return cand
        except Exception:
            pass
    return None

# Prefer a normal import of the installed `requests` package first.
try:
    _orig_sys_path = list(sys.path)
    try:
        cwd = os.path.abspath(os.getcwd())
        sys.path = [p for p in sys.path if p and os.path.abspath(p) != cwd]
        import importlib
        _real_requests = importlib.import_module('requests')
        for _k, _v in vars(_real_requests).items():
            if _k.startswith('__'):
                continue
            globals()[_k] = _v
        _init_path = True
    finally:
        sys.path[:] = _orig_sys_path
except Exception:
    _init_path = _find_real_requests_init()
    if _init_path:
        try:
            spec = importlib.util.spec_from_file_location('requests', _init_path)
            if spec and spec.loader:
                real_mod = importlib.util.module_from_spec(spec)
                sys.modules['requests'] = real_mod
                spec.loader.exec_module(real_mod)
                for k, v in vars(real_mod).items():
                    if k.startswith('__'):
                        continue
                    globals()[k] = v
        except Exception:
            _init_path = None

if not _init_path:
    try:
        stub_path = os.path.join(os.path.dirname(__file__), 'requests_stub.py')
        spec = importlib.util.spec_from_file_location('requests_stub', stub_path)
        stub = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stub)
        for k, v in vars(stub).items():
            if k.startswith('__'):
                continue
            globals()[k] = v
    except Exception:
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

        __all__ = ['Response', 'Session', 'get', 'post', 'exceptions']
