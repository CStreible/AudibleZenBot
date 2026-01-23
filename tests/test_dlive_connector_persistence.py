from unittest.mock import Mock

import platform_connectors.dlive_connector as dlive


def test_dlive_set_token_persists_to_config():
    fake_cfg = Mock()
    fake_cfg.get_platform_config = Mock(return_value={})
    fake_cfg.set_platform_config = Mock()

    conn = dlive.DLiveConnector(config=fake_cfg)
    conn.set_token('dlive-token-xyz')

    fake_cfg.set_platform_config.assert_called_with('dlive', 'access_token', 'dlive-token-xyz')
