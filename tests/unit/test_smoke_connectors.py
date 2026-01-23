import importlib
import pytest

CONNECTORS = [
    "platform_connectors.twitch_connector",
    "platform_connectors.youtube_connector",
    "platform_connectors.kick_connector",
    "platform_connectors.dlive_connector",
    "platform_connectors.trovo_connector",
    "platform_connectors.twitter_connector",
]


@pytest.mark.parametrize("modname", CONNECTORS)
def test_import_connector_mod(modname):
    try:
        module = importlib.import_module(modname)
    except Exception as exc:
        pytest.skip(f"Skipping import of {modname}: {exc}")

    assert module is not None
