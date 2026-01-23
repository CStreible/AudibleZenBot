import os
import base64
from ui.chat_page import build_data_uri_for_emote


def test_emote_disk_file_exists():
    """Sanity check: the disk-cache emote file used in other tests exists."""
    p = os.path.join("resources", "emotes", "twitch_445.png")
    assert os.path.exists(p), f"expected emote file at {p}"


def test_build_data_uri_from_disk_is_well_formed():
    """Call `build_data_uri_for_emote` with no manager and verify the returned
    data URI decodes to the exact disk bytes for `twitch_445.png`.
    """
    p = os.path.join("resources", "emotes", "twitch_445.png")
    assert os.path.exists(p), "test prerequisite: twitch_445.png must exist in resources/emotes"

    data_uri = build_data_uri_for_emote('445', mgr=None)
    assert data_uri is not None, "expected a data URI from disk fallback"
    assert data_uri.startswith('data:image/png;base64,'), "expected a PNG data URI"

    b64 = data_uri.split(',', 1)[1]
    decoded = base64.b64decode(b64)

    with open(p, 'rb') as f:
        disk = f.read()
    assert decoded == disk, "decoded data URI bytes should match disk bytes"
