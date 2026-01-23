"""Local shim for `requests` preserved as a localshim to avoid
shadowing the real `requests` package in site-packages.

This file is a copy of the previous workspace shim `requests.py` and is
kept for test-mode usage. The top-level `requests.py` has been removed so
that imports resolve to the real installed `requests` package when running
in production/venv.
"""

import os
import sys
import importlib
import importlib.util
from core.env import is_test


if is_test():
    # Load the localstub implementation into this module's globals so
    # `import requests` behaves like the stub during tests.
    try:
        stub_path = os.path.join(os.path.dirname(__file__), 'requests.localstub.py')
        spec = importlib.util.spec_from_file_location('requests_localstub', stub_path)
        stub = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stub)
        for k, v in vars(stub).items():
            if k.startswith('__'):
                continue
            globals()[k] = v
    except Exception:
        raise
else:
    # Prefer the installed package. Temporarily remove CWD entries so the
    # local workspace files don't shadow the real distribution.
    _orig_sys_path = list(sys.path)
    try:
        cwd = os.path.abspath(os.getcwd())
        sys.path = [p for p in sys.path if p and os.path.abspath(p) != cwd]
        real = importlib.import_module('requests')
        for k, v in vars(real).items():
            if k.startswith('__'):
                continue
            globals()[k] = v
    finally:
        sys.path[:] = _orig_sys_path
