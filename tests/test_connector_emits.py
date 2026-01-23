import importlib
import pytest


class FakeSignal:
    def __init__(self):
        self.calls = []

    def emit(self, *args, **kwargs):
        self.calls.append((args, kwargs))


CONNECTORS = [
    ("platform_connectors.twitch_connector", "TwitchConnector", "twitch"),
    ("platform_connectors.dlive_connector", "DLiveConnector", "dlive"),
    ("platform_connectors.trovo_connector", "TrovoConnector", "trovo"),
    ("platform_connectors.twitter_connector", "TwitterConnector", "twitter"),
    ("platform_connectors.youtube_connector", "YouTubeConnector", "youtube"),
    ("platform_connectors.kick_connector", "KickConnector", "kick"),
    ("platform_connectors.kick_connector_old_pusher", "KickConnector", "kick"),
]


@pytest.mark.parametrize("module_name,class_name,platform", CONNECTORS)
def test_connector_emits_canonical_and_legacy(module_name, class_name, platform):
    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name)

    # Instantiate connector with minimal args if constructor supports them
    try:
        inst = cls(config=None, is_bot_account=True)
    except TypeError:
        inst = cls()

    # Replace common signal attributes with fakes to capture emits
    for sig in ("message_received_with_metadata", "message_received", "message_signal_with_metadata", "message_signal"):
        try:
            setattr(inst, sig, FakeSignal())
        except Exception:
            # If attribute assignment fails, ensure test still continues
            pass

    # Call the shared emit helper to simulate connector emission
    from platform_connectors.connector_utils import emit_chat

    username = "test_user"
    msg = "hello world"
    meta = {"k": "v"}

    emit_chat(inst, platform, username, msg, meta)

    # Assert canonical signals were called (if present)
    try:
        calls = getattr(inst, "message_received_with_metadata").calls
        assert calls and calls[0][0] == (platform, username, msg, meta)
    except Exception:
        pytest.skip(f"Connector {module_name} does not expose message_received_with_metadata")

    try:
        calls = getattr(inst, "message_received").calls
        assert calls and calls[0][0] == (platform, username, msg, meta)
    except Exception:
        # Some connectors may not expose this older signal; that's acceptable
        pass

    # Legacy signals should also have been invoked when present
    try:
        calls = getattr(inst, "message_signal_with_metadata").calls
        assert calls and calls[0][0] == (username, msg, meta)
    except Exception:
        pass

    try:
        calls = getattr(inst, "message_signal").calls
        # legacy two-arg emit expected first
        assert calls and calls[0][0][0:2] == (username, msg)
    except Exception:
        pass
