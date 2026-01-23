"""CLI helper to dump Twitch Get Channel Emotes JSON for a broadcaster.

Usage:
    python tools/dump_twitch_channel_emotes.py <broadcaster_id>

Writes a pretty-printed JSON file to `logs/twitch_channel_emotes_dump_<broadcaster_id>.json`.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.twitch_emotes import get_manager


def main():
    if len(sys.argv) < 2:
        print('Usage: python tools/dump_twitch_channel_emotes.py <broadcaster_id>')
        return
    broadcaster_id = sys.argv[1]
    mgr = get_manager()
    out = mgr.dump_channel_emotes(broadcaster_id)
    if out:
        print('Wrote channel emotes dump to', out)
    else:
        print('Failed to dump channel emotes; check logs and credentials.')


if __name__ == '__main__':
    main()
