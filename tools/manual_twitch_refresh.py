#!/usr/bin/env python3
import sys, json
sys.path.insert(0, '.')
from core.config import ConfigManager

OUT_PATH = 'tools/twitch_refresh_debug.txt'

def main():
    cfg = ConfigManager()
    t = cfg.get_platform_config('twitch') or {}
    client_id = t.get('client_id')
    client_secret = t.get('client_secret')
    # Prefer bot refresh token for bot login
    refresh_token = t.get('bot_refresh_token') or t.get('streamer_refresh_token') or t.get('bot_token') or ''

    if not client_id or not client_secret or not refresh_token:
        print('Missing client_id/client_secret/refresh_token in twitch config')
        print('twitch config:', repr(t))
        sys.exit(1)

    print('Using client_id prefix:', client_id[:8]+'...')
    print('Using refresh_token prefix:', refresh_token[:8]+'...')

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }

    try:
        import requests
    except Exception:
        print('requests not available in environment')
        sys.exit(1)

    try:
        resp = requests.post('https://id.twitch.tv/oauth2/token', data=data, timeout=15)
    except Exception as e:
        print('Network error:', e)
        sys.exit(1)

    out = {'status_code': getattr(resp, 'status_code', None), 'text': getattr(resp, 'text', ''), 'json': None}
    try:
        out['json'] = resp.json()
    except Exception:
        out['json'] = None

    print('Status:', out['status_code'])
    print('Response body:', out['text'])
    try:
        with open(OUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2)
        print('Saved debug to', OUT_PATH)
    except Exception as e:
        print('Failed to save debug file:', e)

if __name__ == '__main__':
    main()
