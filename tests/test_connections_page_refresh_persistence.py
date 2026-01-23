import importlib
import time
from unittest.mock import Mock


def _make_fake_config(initial=None):
    class FakeConfigManager:
        _store = {} if initial is None else dict(initial)

        def __init__(self, *a, **k):
            pass

        def get_platform_config(self, platform):
            return FakeConfigManager._store.setdefault(platform, {})

        def set_platform_config(self, platform, key, val):
            p = FakeConfigManager._store.setdefault(platform, {})
            p[key] = val

        def load(self):
            return {'platforms': FakeConfigManager._store}

    return FakeConfigManager


class FakeResponse:
    def __init__(self, status=200, data=None, text=''):
        self.status_code = status
        self._data = data or {}
        self.text = text

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f'status {self.status_code}')

    def json(self):
        return self._data


def test_refresh_trovo_persists(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PCW = mod.PlatformConnectionWidget

    # Prepare fake config with a refresh token and client creds
    fake_store = {'trovo': {'streamer_refresh_token': 'rref', 'client_id': 'cid', 'client_secret': 'csec'}}
    FakeCfg = _make_fake_config(initial=fake_store)
    monkeypatch.setattr('core.config.ConfigManager', FakeCfg)

    # Mock requests.post to return new tokens
    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse(200, {'access_token': 'newtok', 'refresh_token': 'newr'})

    import requests as _requests
    monkeypatch.setattr(_requests, 'post', fake_post)

    fake = type('F', (), {})()
    fake.platform_id = 'trovo'

    # Call refreshToken and assert persistence
    res = PCW.refreshToken(fake, 'streamer')
    assert res == 'newtok'
    cfg = FakeCfg()
    saved = cfg.get_platform_config('trovo')
    assert saved.get('streamer_token') == 'newtok'
    assert saved.get('streamer_refresh_token') == 'newr'
    assert isinstance(saved.get('streamer_token_timestamp'), int)


def test_refresh_youtube_persists(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PCW = mod.PlatformConnectionWidget

    fake_store = {'youtube': {'streamer_refresh_token': 'yrref', 'client_id': 'yid', 'client_secret': 'ysec'}}
    FakeCfg = _make_fake_config(initial=fake_store)
    monkeypatch.setattr('core.config.ConfigManager', FakeCfg)

    def fake_post(url, data=None, timeout=None):
        return FakeResponse(200, {'access_token': 'ytnew', 'refresh_token': 'ytnewr'})

    import requests as _requests
    monkeypatch.setattr(_requests, 'post', fake_post)

    fake = type('F', (), {})()
    fake.platform_id = 'youtube'

    res = PCW.refreshToken(fake, 'streamer')
    assert res == 'ytnew'
    cfg = FakeCfg()
    saved = cfg.get_platform_config('youtube')
    assert saved.get('streamer_token') == 'ytnew'
    assert saved.get('streamer_refresh_token') == 'ytnewr'


def test_refresh_twitch_requires_client_secret(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PCW = mod.PlatformConnectionWidget

    # No twitch client_secret configured -> refresh should return None
    fake_store = {'twitch': {'client_id': 'tid'}}
    FakeCfg = _make_fake_config(initial=fake_store)
    monkeypatch.setattr('core.config.ConfigManager', FakeCfg)

    fake = type('F', (), {})()
    fake.platform_id = 'twitch'

    res = PCW.refreshToken(fake, 'streamer')
    assert res is None

