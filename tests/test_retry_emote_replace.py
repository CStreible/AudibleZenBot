import os
import base64
from ui.chat_page import build_data_uri_for_emote


def test_build_data_uri_from_cache():
    # Arrange: create a dummy manager that returns None but points at the cache_dir
    class DummyMgr:
        def __init__(self, cache_dir):
            self.cache_dir = cache_dir
        def get_emote_data_uri(self, emote_id):
            return None

    cache_dir = os.path.join(os.getcwd(), 'resources', 'emotes')
    mgr = DummyMgr(cache_dir)

    # Use a known cached emote present in the repository
    emote_id = '445'
    expected_path = os.path.join(cache_dir, f'twitch_{emote_id}.png')
    assert os.path.exists(expected_path), f"Expected cached emote file {expected_path} to exist for test"

    # Act
    data_uri = build_data_uri_for_emote(emote_id, mgr)

    # Assert
    assert data_uri is not None, "Data URI should be produced from cached file"
    assert data_uri.startswith('data:image/'), "Data URI should start with image mime type"

    # Validate the base64 payload decodes to the same file bytes prefix
    prefix = data_uri.split(',', 1)[1]
    decoded = base64.b64decode(prefix)
    with open(expected_path, 'rb') as f:
        on_disk = f.read()
    # The cached file is relatively small; ensure decoded content equals file content
    assert decoded == on_disk
