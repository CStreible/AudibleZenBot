"""Shim that prefers the installed `websockets` package but falls back
to the bundled `websockets_stub.py` when the real package isn't present.

This avoids accidental shadowing of the real dependency by a top-level
file while keeping the lightweight stub available for offline tests.
"""

from importlib import import_module
import sys
import os

# Attempt to import the real `websockets` package from site-packages by
# temporarily removing the project directory from `sys.path` so that
# local files do not shadow the distribution.
_this_dir = os.path.dirname(__file__)
_removed = False
_real = None
try:
    if _this_dir in sys.path:
        sys.path.remove(_this_dir)
        _removed = True
    try:
        _real = import_module('websockets')
    except Exception:
        _real = None
finally:
    if _removed:
        sys.path.insert(0, _this_dir)

if _real is not None:
    # Re-export everything from the real package
    globals().update({k: v for k, v in _real.__dict__.items() if not k.startswith('__')})
    # Ensure a top-level `connect` symbol exists for legacy code/tests that
    # expect `websockets.connect`. Some websockets versions expose connect in
    # a submodule (e.g. websockets.client.connect); try to locate it.
    if 'connect' not in globals():
        _connect = getattr(_real, 'connect', None)
        if _connect is None:
            _client = getattr(_real, 'client', None)
            _connect = getattr(_client, 'connect', None) if _client is not None else None
        if _connect is not None:
            globals()['connect'] = _connect
else:
    # Fall back to the bundled stub (import by name to work when this
    # module is executing as a top-level script/module).
    import importlib as _il
    _stub = _il.import_module('websockets_stub')
    _stub_dict = {k: v for k, v in _stub.__dict__.items() if not k.startswith('__')}
    globals().update(_stub_dict)
    # Ensure common symbols are explicitly provided
    if 'connect' not in globals() and hasattr(_stub, 'connect'):
        globals()['connect'] = getattr(_stub, 'connect')
    if 'exceptions' not in globals() and hasattr(_stub, 'exceptions'):
        globals()['exceptions'] = getattr(_stub, 'exceptions')

# As a last resort, ensure the module object in sys.modules has a `connect`
# attribute so modules that imported earlier get the symbol available for
# patching in tests.
try:
    import sys as _sys
    if 'connect' in globals():
        setattr(_sys.modules[__name__], 'connect', globals()['connect'])
    if 'exceptions' in globals():
        setattr(_sys.modules[__name__], 'exceptions', globals()['exceptions'])
except Exception:
    pass
