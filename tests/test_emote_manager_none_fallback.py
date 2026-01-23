import os
import base64
from types import SimpleNamespace
from ui.chat_page import build_data_uri_for_emote


def test_manager_none_fallback_to_disk():
    """Mock a manager that returns None for `get_emote_data_uri` and has
    a `cache_dir` pointing to `resources/emotes`. The UI fallback should read
    the disk file and return a valid data URI matching disk bytes.
    """
    cache_dir = os.path.join('resources', 'emotes')
    p = os.path.join(cache_dir, 'twitch_445.png')
    assert os.path.exists(p), "test prerequisite: twitch_445.png must exist in resources/emotes"

    mgr = SimpleNamespace()
    mgr.cache_dir = cache_dir
    def get_emote_data_uri(_id):
        return None
    mgr.get_emote_data_uri = get_emote_data_uri

    data_uri = build_data_uri_for_emote('445', mgr=mgr)
    assert data_uri is not None, "expected data URI from disk fallback when manager returns None"
    assert data_uri.startswith('data:image/png;base64,')

    b64 = data_uri.split(',', 1)[1]
    decoded = base64.b64decode(b64)

    with open(p, 'rb') as f:
        disk = f.read()
    assert decoded == disk
