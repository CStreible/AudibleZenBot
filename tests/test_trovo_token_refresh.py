import importlib
from types import SimpleNamespace
from unittest.mock import Mock


def make_response(status_code=200, json_data=None, text=''):
    class Resp:
        def __init__(self, status_code, json_data, text):
            self.status_code = status_code
            self._json = json_data or {}
            self.text = text

        def json(self):
            return self._json

    return Resp(status_code, json_data, text)


def test_refresh_access_token_success(tmp_path):
    mod = importlib.import_module('platform_connectors.trovo_connector')
    # Create a mock config that contains client creds and records set_platform_config calls
    cfg = Mock()
    cfg.get_platform_config.return_value = {'client_id': 'cid', 'client_secret': 'csec'}
    cfg.set_platform_config = Mock()

    conn = mod.TrovoConnector(config=cfg)
    conn.refresh_token = 'r1'

    # Mock session.post to return a 200 with tokens
    resp = make_response(200, {'access_token': 'newtok', 'refresh_token': 'newr'})
    class Session:
        def post(self, *args, **kwargs):
            return resp

    # Inject session via make_retry_session if available, else patch requests.Session
    if hasattr(mod, 'make_retry_session') and mod.make_retry_session:
        mod.make_retry_session = lambda: Session()
    else:
        mod.requests = SimpleNamespace(Session=lambda: Session(), exceptions=mod.requests.exceptions)

    ok = conn.refresh_access_token()
    assert ok is True
    assert conn.access_token == 'newtok'
    assert conn.refresh_token == 'newr'
    # Config should have been updated via set_platform_config calls
    cfg.set_platform_config.assert_any_call('trovo', 'access_token', 'newtok')
    cfg.set_platform_config.assert_any_call('trovo', 'refresh_token', 'newr')


def test_refresh_access_token_failure_status(tmp_path):
    mod = importlib.import_module('platform_connectors.trovo_connector')
    conn = mod.TrovoConnector(config=None)
    conn.refresh_token = 'r1'

    resp = make_response(400, None, 'bad')
    class Session:
        def post(self, *args, **kwargs):
            return resp

    if hasattr(mod, 'make_retry_session') and mod.make_retry_session:
        mod.make_retry_session = lambda: Session()
    else:
        mod.requests = SimpleNamespace(Session=lambda: Session(), exceptions=mod.requests.exceptions)

    ok = conn.refresh_access_token()
    assert ok is False


def test_send_message_refresh_retry(monkeypatch):
    mod = importlib.import_module('platform_connectors.trovo_connector')
    cfg = Mock()
    cfg.get_platform_config.return_value = {'streamer_channel_id': '123'}
    cfg.set_platform_config = Mock()

    conn = mod.TrovoConnector(config=cfg)
    conn.access_token = 'old'
    conn.refresh_token = 'r1'

    # Session.post will return 401 then 200
    class Session:
        def __init__(self):
            self.calls = 0

        def post(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return make_response(401, None, 'unauth')
            return make_response(200, None, 'ok')

    # Patch make_retry_session or requests
    if hasattr(mod, 'make_retry_session') and mod.make_retry_session:
        mod.make_retry_session = lambda: Session()
    else:
        mod.requests = SimpleNamespace(Session=lambda: Session(), exceptions=mod.requests.exceptions)

    # Patch refresh_access_token to set new token and return True
    def fake_refresh():
        conn.access_token = 'newtok'
        # emulate persistence
        if conn.config:
            conn.config.set_platform_config('trovo', 'access_token', conn.access_token)
        return True
    monkeypatch.setattr(conn, 'refresh_access_token', fake_refresh)

    ok = conn.send_message('hello')
    assert ok is True
    cfg.set_platform_config.assert_any_call('trovo', 'access_token', 'newtok')


def test_send_message_refresh_failure(monkeypatch):
    mod = importlib.import_module('platform_connectors.trovo_connector')
    cfg = SimpleNamespace()
    cfg._data = {'trovo': {'streamer_channel_id': '123'}}
    cfg.get_platform_config = lambda name: cfg._data.get(name, {})
    cfg.set_platform_config = lambda platform, key, val: cfg._data.setdefault(platform, {})

    conn = mod.TrovoConnector(config=cfg)
    conn.access_token = 'old'
    conn.refresh_token = 'r1'

    class Session:
        def post(self, *args, **kwargs):
            return make_response(401, None, 'unauth')

    if hasattr(mod, 'make_retry_session') and mod.make_retry_session:
        mod.make_retry_session = lambda: Session()
    else:
        mod.requests = SimpleNamespace(Session=lambda: Session(), exceptions=mod.requests.exceptions)

    monkeypatch.setattr(conn, 'refresh_access_token', lambda: False)

    ok = conn.send_message('hello')
    assert ok is False


def test_refresh_access_token_network_error(monkeypatch, capsys):
    mod = importlib.import_module('platform_connectors.trovo_connector')
    conn = mod.TrovoConnector(config=None)
    conn.refresh_token = 'r1'

    # session.post raises requests.exceptions.RequestException
    class Session:
        def post(self, *args, **kwargs):
            raise mod.requests.exceptions.RequestException('network')

    if hasattr(mod, 'make_retry_session') and mod.make_retry_session:
        mod.make_retry_session = lambda: Session()
    else:
        mod.requests = SimpleNamespace(Session=lambda: Session(), exceptions=mod.requests.exceptions)

    ok = conn.refresh_access_token()
    assert ok is False
    captured = capsys.readouterr()
    assert 'Network error refreshing token' in captured.err or 'Error refreshing token' in captured.err


def test_send_message_network_error(monkeypatch, capsys):
    mod = importlib.import_module('platform_connectors.trovo_connector')
    cfg = SimpleNamespace()
    cfg._data = {'trovo': {'streamer_channel_id': '123'}}
    cfg.get_platform_config = lambda name: cfg._data.get(name, {})
    cfg.set_platform_config = lambda platform, key, val: cfg._data.setdefault(platform, {})

    conn = mod.TrovoConnector(config=cfg)
    conn.access_token = 'old'

    class Session:
        def post(self, *args, **kwargs):
            raise mod.requests.exceptions.RequestException('network')

    if hasattr(mod, 'make_retry_session') and mod.make_retry_session:
        mod.make_retry_session = lambda: Session()
    else:
        mod.requests = SimpleNamespace(Session=lambda: Session(), exceptions=mod.requests.exceptions)

    ok = conn.send_message('hello')
    assert ok is False
    captured = capsys.readouterr()
    assert 'Network error sending message' in captured.err
