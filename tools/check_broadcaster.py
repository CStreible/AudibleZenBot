import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.twitch_emotes import get_manager

mgr = get_manager()
print('has_client_id=', bool(getattr(mgr, 'client_id', None)))
print('has_oauth=', bool(getattr(mgr, 'oauth_token', None)))
print('get_broadcaster_id->', mgr.get_broadcaster_id())
