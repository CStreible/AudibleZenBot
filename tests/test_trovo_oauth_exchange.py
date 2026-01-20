import importlib
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


def test_exchange_v2_success(monkeypatch):
    mod = importlib.import_module('platform_connectors.trovo_oauth')

    fake_resp = make_response(200, {'access_token': 't', 'refresh_token': 'r'})

    class FakeSession:
        def post(self, *args, **kwargs):
            return fake_resp

    monkeypatch.setattr(mod, 'make_retry_session', lambda: FakeSession())

    res = mod.exchange_code_for_token_v2('code')
    assert res == {'access_token': 't', 'refresh_token': 'r'}


def test_trovo_exchange_token_success(monkeypatch):
    mod = importlib.import_module('platform_connectors.trovo_exchange_token')

    fake_resp = make_response(200, {'access_token': 'X', 'refresh_token': 'Y'})

    class FakeSession:
        def post(self, *args, **kwargs):
            return fake_resp

    monkeypatch.setattr(mod, 'make_retry_session', lambda: FakeSession())

    res = mod.exchange_code_for_token('code')
    assert res == {'access_token': 'X', 'refresh_token': 'Y'}
