from unittest.mock import Mock

import platform_connectors.kick_connector as kick


def test_kick_set_token_persists_streamer_and_bot():
    fake_cfg = Mock()
    fake_cfg.get_platform_config = Mock(return_value={})
    fake_cfg.set_platform_config = Mock()

    conn = kick.KickConnector(config=fake_cfg)

    # streamer token
    conn.set_token('streamer-token-1', is_bot=False)
    fake_cfg.set_platform_config.assert_any_call('kick', 'streamer_token', 'streamer-token-1')

    # bot token
    conn.set_token('bot-token-2', is_bot=True)
    fake_cfg.set_platform_config.assert_any_call('kick', 'bot_token', 'bot-token-2')
