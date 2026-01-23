import webbrowser
from urllib.parse import urlencode

try:
    from core.config import ConfigManager
    cfg = ConfigManager()
    twitch_cfg = cfg.get_platform_config('twitch') or {}
    client_id = twitch_cfg.get('client_id', '')
    callback_port = cfg.get('ngrok', {}).get('callback_port', 8889)
except Exception:
    client_id = ''
    callback_port = 8889

redirect_uri = f"http://localhost:{callback_port}/callback"
scopes_needed = [
    'user:read:email',
    'user:read:chat',
    'chat:read',
    'chat:edit',
    'channel:read:subscriptions',
    'channel:manage:broadcast',
    'channel:read:redemptions',
    'bits:read',
    'moderator:read:followers',
    'user:write:chat'
]
params = {
    'response_type': 'code',
    'client_id': client_id,
    'redirect_uri': redirect_uri,
    'scope': ' '.join(scopes_needed),
    'force_verify': 'true'
}

oauth_url = f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"
print('Opening Twitch reauth URL:')
print(oauth_url)
try:
    webbrowser.open(oauth_url)
    print('Browser open attempted.')
except Exception as e:
    print('Failed to open browser:', e)
    print('Copy and paste the URL above into your browser.')
