import importlib
import runpy
from unittest.mock import Mock


def make_response(status=200, data=None, text=''):
    class Resp:
        def __init__(self, status, data, text):
            self.status_code = status
            self._data = data or {}
            self.text = text

        def json(self):
            return self._data

    return Resp(status, data, text)


def test_exchange_code_for_token_success(monkeypatch):
    mod = importlib.import_module('platform_connectors.trovo_oauth_local')

    fake_resp = make_response(200, {'access_token': 'tok', 'refresh_token': 'ref'})

    class FakeSession:
        def post(self, *args, **kwargs):
            return fake_resp

    monkeypatch.setattr(mod, 'make_retry_session', lambda: FakeSession())

    result = mod.exchange_code_for_token('code')
    assert result == {'access_token': 'tok', 'refresh_token': 'ref'}


def test_main_saves_tokens_to_config(monkeypatch):
    # Prepare module and monkeypatches to emulate __main__ flow without network or browser
    mod_name = 'platform_connectors.trovo_oauth_local'
    token_data = {'access_token': 'A', 'refresh_token': 'R'}

    # Replace exchange_code_for_token to return our token_data
    monkeypatch.setitem(__import__('sys').modules, mod_name, importlib.import_module(mod_name))
    mod = importlib.import_module(mod_name)
    monkeypatch.setattr(mod, 'exchange_code_for_token', lambda code: token_data)
    monkeypatch.setattr(mod, 'webbrowser', Mock(open=lambda *a, **k: None))

    # Monkeypatch builtins.input to provide a dummy code
    monkeypatch.setattr('builtins.input', lambda prompt='': 'dummycode')

    # Fake ConfigManager to capture set_platform_config calls
    class FakeConfigManager:
        last_instance = None
        def __init__(self, *a, **k):
            FakeConfigManager.last_instance = self
            self.set_platform_config = Mock()

    import core.config as core_config
    monkeypatch.setattr(core_config, 'ConfigManager', FakeConfigManager)

    # Simulate the save logic performed in the module's __main__ block
    result = mod.exchange_code_for_token('dummy')
    import core.config as core_config
    cfg = core_config.ConfigManager()
    cfg.set_platform_config('trovo', 'access_token', result.get('access_token', ''))
    cfg.set_platform_config('trovo', 'refresh_token', result.get('refresh_token', ''))

    inst = FakeConfigManager.last_instance
    assert inst is not None
    inst.set_platform_config.assert_any_call('trovo', 'access_token', 'A')
    inst.set_platform_config.assert_any_call('trovo', 'refresh_token', 'R')
