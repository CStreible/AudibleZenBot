import os
from unittest.mock import Mock

import core.chat_manager as chat_manager


def test_connect_bot_account_in_ci_mode_persists_credentials(monkeypatch):
    monkeypatch.setenv('AUDIBLEZENBOT_CI', '1')

    fake_cfg = Mock()
    fake_cfg.get = Mock(return_value={})
    fake_cfg.get_platform_config = Mock(return_value={})
    fake_cfg.set_platform_config = Mock()

    mgr = chat_manager.ChatManager(config=fake_cfg)

    res = mgr.connectBotAccount('testplat', 'botuser', 'tok123', refresh_token='rref')
    assert res is True

    fake_cfg.set_platform_config.assert_any_call('testplat', 'bot_username', 'botuser')
    fake_cfg.set_platform_config.assert_any_call('testplat', 'bot_token', 'tok123')
    fake_cfg.set_platform_config.assert_any_call('testplat', 'bot_refresh_token', 'rref')


def test_disconnect_platform_clears_bot_state(monkeypatch):
    # Ensure no heavy connectors are constructed during ChatManager init
    monkeypatch.setenv('AUDIBLEZENBOT_CI', '1')

    fake_cfg = Mock()
    fake_cfg.set_platform_config = Mock()
    fake_cfg.get = Mock(return_value={})
    mgr = chat_manager.ChatManager(config=fake_cfg)

    class FakeBot:
        def disconnect(self):
            pass

    mgr.bot_connectors['xplatform'] = FakeBot()
    mgr.disconnectPlatform('xplatform')

    fake_cfg.set_platform_config.assert_any_call('xplatform', 'bot_connected', False)
