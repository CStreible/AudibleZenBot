from unittest.mock import Mock

import platform_connectors.trovo_connector as trovo


def test_trovo_refresh_persists_tokens(monkeypatch):
    # Fake response object
    class FakeResponse:
        status_code = 200

        def json(self):
            return {'access_token': 'newtok', 'refresh_token': 'newr'}

    class FakeSession:
        def post(self, *a, **k):
            return FakeResponse()

    fake_cfg = Mock()
    fake_cfg.get_platform_config = Mock(return_value={'client_id': 'cid', 'client_secret': 'csec'})
    fake_cfg.set_platform_config = Mock()

    monkeypatch.setattr(trovo, 'make_retry_session', lambda: FakeSession())

    conn = trovo.TrovoConnector(config=fake_cfg)
    conn.refresh_token = 'oldr'
    conn.CLIENT_ID = 'cid'
    conn.CLIENT_SECRET = 'csec'

    res = conn.refresh_access_token()
    assert res is True
    fake_cfg.set_platform_config.assert_any_call('trovo', 'access_token', 'newtok')
    fake_cfg.set_platform_config.assert_any_call('trovo', 'refresh_token', 'newr')
