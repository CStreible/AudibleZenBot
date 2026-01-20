import importlib
from unittest.mock import Mock


def test_youtube_set_token_persists():
    mod = importlib.import_module('platform_connectors.youtube_connector')
    YouTubeConnector = mod.YouTubeConnector

    cfg = Mock()
    cfg.get_platform_config.return_value = {}
    cfg.set_platform_config = Mock()

    conn = YouTubeConnector(config=cfg)
    conn.set_token('yt-token')

    cfg.set_platform_config.assert_called_with('youtube', 'oauth_token', 'yt-token')


def test_youtube_set_refresh_token_persists():
    mod = importlib.import_module('platform_connectors.youtube_connector')
    YouTubeConnector = mod.YouTubeConnector

    cfg = Mock()
    cfg.get_platform_config.return_value = {}
    cfg.set_platform_config = Mock()

    conn = YouTubeConnector(config=cfg)
    conn.set_refresh_token('yt-refresh')

    cfg.set_platform_config.assert_called_with('youtube', 'refresh_token', 'yt-refresh')
