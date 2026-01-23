import os
import base64
import shutil
from types import SimpleNamespace
from pathlib import Path

import pytest

from ui.chat_page import build_data_uri_for_emote


def test_manager_provided_data_uri_precedence():
    """If the manager provides a data URI it should be returned verbatim."""
    sample_bytes = b'fakepngbytes'
    sample_b64 = base64.b64encode(sample_bytes).decode()
    data_uri = f'data:image/png;base64,{sample_b64}'

    mgr = SimpleNamespace()
    mgr.cache_dir = "does/not/exist"
    mgr.get_emote_data_uri = lambda _id: data_uri

    out = build_data_uri_for_emote('445', mgr=mgr)
    assert out == data_uri


def test_missing_emote_returns_none():
    """When no manager and no disk file exist, function returns None."""
    out = build_data_uri_for_emote('this_id_should_not_exist_12345', mgr=None)
    assert out is None


def test_cache_dir_override_with_tmp_path(tmp_path):
    """If manager provides a `cache_dir`, that directory is searched for emote files."""
    # Ensure we have a real PNG to copy
    src = Path('resources') / 'emotes' / 'twitch_445.png'
    assert src.exists(), "prerequisite: resources/emotes/twitch_445.png must exist"

    dst = tmp_path / 'twitch_999.png'
    shutil.copy(src, dst)

    mgr = SimpleNamespace()
    mgr.cache_dir = str(tmp_path)
    mgr.get_emote_data_uri = lambda _id: None

    out = build_data_uri_for_emote('999', mgr=mgr)
    assert out is not None
    assert out.startswith('data:image/png;base64,')

    b64 = out.split(',', 1)[1]
    decoded = base64.b64decode(b64)
    with open(dst, 'rb') as f:
        disk = f.read()
    assert decoded == disk


def test_gif_handling_if_present():
    """If a GIF cache file exists, it should be returned as image/gif data URI."""
    emote_dir = Path('resources') / 'emotes'
    gifs = list(emote_dir.glob('twitch_*.gif'))
    if not gifs:
        pytest.skip('No GIF emote files present in resources/emotes')

    gif_path = gifs[0]
    emid = gif_path.stem.split('twitch_')[-1]

    out = build_data_uri_for_emote(emid, mgr=None)
    assert out is not None
    assert out.startswith('data:image/gif;base64,')

    b64 = out.split(',', 1)[1]
    decoded = base64.b64decode(b64)
    with open(gif_path, 'rb') as f:
        disk = f.read()
    assert decoded == disk
