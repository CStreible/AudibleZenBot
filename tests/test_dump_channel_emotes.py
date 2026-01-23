import os
import json
import tempfile
from unittest import mock
import os
import json
import tempfile
import unittest
from unittest import mock

from core.twitch_emotes import get_manager


class DumpChannelEmotesTest(unittest.TestCase):
    def test_writes_file(self):
        mgr = get_manager()
        # Set a temporary cache dir so we don't write into repo
        tmpdir = tempfile.mkdtemp()
        mgr.cache_dir = tmpdir
        # populate a small id_map/name_map for deterministic output
        mgr.id_map = {'1': {'id': '1', 'name': 'Kappa', 'images': {'url_1x': 'https://example.com/1.png'}}}
        mgr.name_map = {'Kappa': '1'}

        # Patch network fetch to avoid real HTTP calls
        with mock.patch.object(mgr, 'fetch_channel_emotes', lambda bid: None):
            out = mgr.dump_channel_emotes('853763018')

        self.assertIsNotNone(out)
        self.assertTrue(os.path.exists(out))
        with open(out, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data.get('broadcaster_id'), '853763018')
        self.assertIn('id_map', data)