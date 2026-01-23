import importlib
from unittest.mock import Mock


def _make_fake_cfg_store():
    class FakeConfigManager:
        _store = {}

        def __init__(self, *a, **k):
            pass

        def set_platform_config(self, platform, key, val):
            FakeConfigManager._store.setdefault(platform, {})[key] = val

        def get_platform_config(self, platform):
            return FakeConfigManager._store.get(platform, {})

        def get(self, key, default=None):
            return default

        def load(self):
            return {'platforms': FakeConfigManager._store}

    return FakeConfigManager


def _fake_response_with_tokens():
    class Resp:
        status_code = 200

        text = ''

        def raise_for_status(self):
            return None

        def json(self):
            return {'access_token': 'ATOK', 'refresh_token': 'RTOK'}

    return Resp()


def test_exchange_saves_trovo_client_creds(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PlatformConnectionWidget = mod.PlatformConnectionWidget

    FakeCfg = _make_fake_cfg_store()
    import core.config as core_config
    monkeypatch.setattr(core_config, 'ConfigManager', FakeCfg)

    # ensure requests.post returns success by patching top-level requests.post
    import requests as _requests
    fake_post = lambda *a, **k: _fake_response_with_tokens()
    monkeypatch.setattr(_requests, 'post', fake_post)

    # stub out fetchUserInfo and onOAuthSuccess to avoid filesystem/config reloads
    monkeypatch.setattr(PlatformConnectionWidget, 'fetchUserInfo', lambda self, t: {'username': 'u', 'display_name': 'd'})
    monkeypatch.setattr(PlatformConnectionWidget, 'onOAuthSuccess', lambda self, a, u, t, r='': None)

    fake = type('F', (), {})()
    fake.platform_id = 'trovo'
    fake.onOAuthFailed = lambda a, m: None

    # Call exchangeCodeForToken which should save client creds into ConfigManager
    PlatformConnectionWidget.exchangeCodeForToken(fake, 'streamer', 'CODE123')

    cfg = FakeCfg()
    saved = cfg.load().get('platforms', {}).get('trovo', {})
    assert 'client_id' in saved
    assert 'client_secret' in saved


def test_exchange_saves_youtube_client_creds(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PlatformConnectionWidget = mod.PlatformConnectionWidget

    FakeCfg = _make_fake_cfg_store()
    import core.config as core_config
    monkeypatch.setattr(core_config, 'ConfigManager', FakeCfg)

    import requests as _requests
    monkeypatch.setattr(_requests, 'post', lambda *a, **k: _fake_response_with_tokens())
    monkeypatch.setattr(PlatformConnectionWidget, 'fetchUserInfo', lambda self, t: {'username': 'u'})
    monkeypatch.setattr(PlatformConnectionWidget, 'onOAuthSuccess', lambda self, a, u, t, r='': None)

    fake = type('F', (), {})()
    fake.platform_id = 'youtube'
    fake.onOAuthFailed = lambda a, m: None
    PlatformConnectionWidget.exchangeCodeForToken(fake, 'streamer', 'CODE_YT')

    cfg = FakeCfg()
    saved = cfg.load().get('platforms', {}).get('youtube', {})
    assert 'client_id' in saved
    assert 'client_secret' in saved


def test_exchange_saves_kick_client_creds(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PlatformConnectionWidget = mod.PlatformConnectionWidget

    FakeCfg = _make_fake_cfg_store()
    import core.config as core_config
    monkeypatch.setattr(core_config, 'ConfigManager', FakeCfg)

    import requests as _requests
    monkeypatch.setattr(_requests, 'post', lambda *a, **k: _fake_response_with_tokens())
    monkeypatch.setattr(PlatformConnectionWidget, 'fetchUserInfo', lambda self, t: {'username': 'u'})
    monkeypatch.setattr(PlatformConnectionWidget, 'onOAuthSuccess', lambda self, a, u, t, r='': None)

    fake = type('F', (), {})()
    fake.platform_id = 'kick'
    fake.onOAuthFailed = lambda a, m: None
    PlatformConnectionWidget.exchangeCodeForToken(fake, 'streamer', 'CODE_K')

    cfg = FakeCfg()
    saved = cfg.load().get('platforms', {}).get('kick', {})
    assert 'client_id' in saved
    assert 'client_secret' in saved
