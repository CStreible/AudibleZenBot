#!/usr/bin/env python3
import sys
import argparse
import json
from core.config import ConfigManager

TROVO_TOKEN_URL = "https://open-api.trovo.live/openplatform/exchangetoken"

def main():
    parser = argparse.ArgumentParser(description='Manual Trovo token exchange debug')
    parser.add_argument('--code', '-c', help='Authorization code from callback')
    parser.add_argument('--redirect', '-r', help='Redirect URI used during auth', default='https://mistilled-declan-unendable.ngrok-free.dev/callback')
    args = parser.parse_args()

    cfg = ConfigManager()
    trovo_cfg = cfg.get_platform_config('trovo') or {}
    client_id = trovo_cfg.get('client_id')
    client_secret = trovo_cfg.get('client_secret')

    if not client_id or not client_secret:
        print('Trovo client_id or client_secret missing in config. Please set them in Settings or config.json')
        sys.exit(1)

    code = args.code
    if not code:
        code = input('Paste the authorization code: ').strip()
        if not code:
            print('No code provided; aborting')
            sys.exit(1)

    headers = {
        'Accept': 'application/json',
        'client-id': client_id,
        'Content-Type': 'application/json',
    }
    data = {
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': args.redirect,
    }

    print('Posting to', TROVO_TOKEN_URL)
    print('Request headers:', headers)
    print('Request JSON body:', json.dumps(data))

    try:
        import requests
    except Exception:
        print('requests library not available')
        sys.exit(1)

    try:
        s = requests.Session()
        resp = s.post(TROVO_TOKEN_URL, headers=headers, json=data, timeout=15)
    except Exception as e:
        print('Network error:', e)
        sys.exit(1)

    out = {
        'status_code': resp.status_code,
        'response_text': getattr(resp, 'text', ''),
        'response_json': None,
        'response_headers': dict(getattr(resp, 'headers', {})),
    }
    try:
        out['response_json'] = resp.json()
    except Exception:
        out['response_json'] = None

    print('Status:', resp.status_code)
    print('Response headers:', out['response_headers'])
    print('Response body:', out['response_text'])

    # Save to file for inspection
    try:
        with open('tools/trovo_exchange_debug.txt', 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2)
        print('Saved response to tools/trovo_exchange_debug.txt')
    except Exception as e:
        print('Failed to write debug file:', e)


if __name__ == '__main__':
    main()
