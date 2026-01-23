import importlib
from unittest.mock import Mock


def test_connections_page_on_oauth_success_persists_streamer_and_bot(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PlatformConnectionWidget = mod.PlatformConnectionWidget

    # Fake self with minimal attributes used by onOAuthSuccess
    fake = type('F', (), {})()
    fake.platform_id = 'myplat'
    fake.streamer_display_name = type('T', (), {'setText': lambda self, v: None})()
    fake.bot_display_name = type('T', (), {'setText': lambda self, v: None})()
    fake.streamer_login_btn = type('B', (), {'setText': lambda self, v: None, 'setEnabled': lambda self, v: None, 'text': lambda self: 'Login'})()
    fake.bot_login_btn = type('B', (), {'setText': lambda self, v: None, 'setEnabled': lambda self, v: None, 'text': lambda self: 'Login'})()
    fake.append_status_message = lambda v: None
    fake.connect_requested = Mock()
    fake.chat_manager = None

    # Fake ConfigManager that records set_platform_config calls and returns load data
    class FakeConfigManager:
        _store = {}

        def __init__(self, *a, **k):
            # ensure shared store exists
            FakeConfigManager._store = FakeConfigManager._store or {}

        def set_platform_config(self, platform, key, val):
            p = FakeConfigManager._store.setdefault(platform, {})
            p[key] = val

        def get_platform_config(self, platform):
            return FakeConfigManager._store.get(platform, {})

        def load(self):
            return {'platforms': FakeConfigManager._store}

    import core.config as core_config
    monkeypatch.setattr(core_config, 'ConfigManager', FakeConfigManager)

    user_info = {'username': 'alice', 'display_name': 'Alice', 'user_id': 'UID123'}

    # Call as unbound method on the widget class
    PlatformConnectionWidget.onOAuthSuccess(fake, 'streamer', user_info, 'tok123', 'rref')

    # Verify that ConfigManager saved expected keys
    cfg = core_config.ConfigManager()
    saved = cfg.load().get('platforms', {}).get('myplat', {})
    assert saved.get('streamer_username') == 'alice'
    assert saved.get('streamer_token') == 'tok123'
    assert saved.get('streamer_refresh_token') == 'rref'
    assert saved.get('streamer_logged_in') is True
