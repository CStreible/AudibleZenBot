import types, sys, importlib

def make_session_429():
    return types.SimpleNamespace(get=lambda *a, **k: types.SimpleNamespace(status_code=429, json=lambda: {'data': []}, content=b''))

fake = types.SimpleNamespace()
fake.make_retry_session = lambda: make_session_429()
sys.modules['core.http_session'] = fake

import os
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
import sys
sys.path.insert(0, repo_root)
import core.twitch_emotes as te
importlib.reload(te)
from core.twitch_emotes import get_manager
mgr = get_manager()
print('manager.session:', type(mgr.session), mgr.session)
try:
    mgr.prefetch_global(background=False)
except Exception as e:
    print('prefetch_global raised:', e)
print('last_attempts:', getattr(mgr, '_last_request_attempts', None))
print('id_map:', mgr.id_map)
