"""Environment-aware shim for `websockets`.

This shim loads a local stub in test mode and delegates to the installed
`websockets` distribution in production. To avoid importing this shim
instead of the installed package it temporarily removes this module from
`sys.modules` and strips the current working directory from `sys.path`
while performing the import.
"""

import os
import sys
import importlib
import importlib.util
from core.env import is_test


def _load_local_stub():
    stub_path = os.path.join(os.path.dirname(__file__), 'websockets.localstub.py')
    spec = importlib.util.spec_from_file_location('websockets_localstub', stub_path)
    stub = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stub)
    for k, v in vars(stub).items():
        if k.startswith('__'):
            continue
        globals()[k] = v


def _delegate_to_installed():
    modname = 'websockets'
    orig_mod = sys.modules.pop(modname, None)
    _orig_sys_path = list(sys.path)
    try:
        cwd = os.path.abspath(os.getcwd())
        sys.path = [p for p in sys.path if p and os.path.abspath(p) != cwd]
        real = importlib.import_module('websockets')
        # Replace this shim in sys.modules with the real package so that
        # submodule imports like `websockets.legacy` resolve correctly.
        sys.modules[modname] = real
    finally:
        sys.path[:] = _orig_sys_path

    # Copy public attributes from installed package for convenience
    for k, v in vars(real).items():
        if k.startswith('__'):
            continue
        globals()[k] = v


if is_test():
    _load_local_stub()
else:
    _delegate_to_installed()
