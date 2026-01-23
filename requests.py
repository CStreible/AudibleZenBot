"""Environment-aware shim for `requests`.

This shim preserves the ability to run tests with a local stub while
delegating to the real installed `requests` distribution in production.

Key behavior:
- If `core.env.is_test()` is True, the local stub `requests.localstub.py`
  is loaded into this module's globals.
- Otherwise the shim temporarily removes the current module from
  `sys.modules` and removes the current working directory from
  `sys.path` so that `importlib.import_module('requests')` resolves to the
  installed package in `site-packages`. The real package's attributes
  are then copied into this module's globals.

This approach avoids accidental recursion where this file would be
imported in lieu of the real `requests` package.
"""

import os
import sys
import importlib
import importlib.util
from core.env import is_test


def _load_local_stub():
    stub_path = os.path.join(os.path.dirname(__file__), 'requests.localstub.py')
    spec = importlib.util.spec_from_file_location('requests_localstub', stub_path)
    stub = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stub)
    for k, v in vars(stub).items():
        if k.startswith('__'):
            continue
        globals()[k] = v


def _delegate_to_installed():
    # Remove this module entry (if present) so importlib will locate the
    # installed distribution instead of returning this file. Also strip the
    # current working directory from sys.path so local files do not shadow
    # site-packages. Restore both afterwards.
    modname = 'requests'
    orig_mod = sys.modules.pop(modname, None)
    _orig_sys_path = list(sys.path)
    try:
        cwd = os.path.abspath(os.getcwd())
        sys.path = [p for p in sys.path if p and os.path.abspath(p) != cwd]
        real = importlib.import_module('requests')
    finally:
        # restore sys.path and sys.modules exactly as they were
        sys.path[:] = _orig_sys_path
        if orig_mod is not None:
            sys.modules[modname] = orig_mod

    for k, v in vars(real).items():
        if k.startswith('__'):
            continue
        globals()[k] = v


if is_test():
    _load_local_stub()
else:
    _delegate_to_installed()
