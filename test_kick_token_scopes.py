"""
Test if the token has the right scopes by checking token info
"""
import requests
from pathlib import Path
import json

# Load config
config_file = Path.home() / ".audiblezenbot" / "config.json"
with open(config_file, 'r') as f:
    config = json.load(f)

kick_config = config.get('platforms', {}).get('kick', {})
access_token = kick_config.get('streamer_token', '')
user_id = kick_config.get('streamer_user_id', '')

print(f"Testing token scopes and permissions")
print(f"  User ID: {user_id}")
print(f"  Token: {access_token[:20]}...")

# Test 1: Check if we can get our own channel info
print(f"\n=== Test 1: GET /channels (verify token works) ===")
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json"
}

response = requests.get(
    "https://api.kick.com/public/v1/channels",
    headers=headers,
    timeout=10
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}")

if response.status_code == 200:
    data = response.json()
    print(f"\n✓ Token is valid!")
    if 'data' in data and len(data['data']) > 0:
        channel = data['data'][0]
        print(f"  Channel: {channel.get('slug')}")
        print(f"  Broadcaster ID: {channel.get('broadcaster_user_id')}")
else:
    print(f"\n✗ Token may be expired or invalid")

# Test 2: Try sending message with exact format from docs
print(f"\n=== Test 2: POST /chat (send message) ===")
url = "https://api.kick.com/public/v1/chat"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

payload = {
    "broadcaster_user_id": int(user_id),
    "content": "Test from verification script",
    "type": "user"
}

print(f"URL: {url}")
print(f"Payload: {payload}")

response = requests.post(url, headers=headers, json=payload, timeout=10)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    print(f"\n✓ ✓ ✓ SUCCESS! Message sent!")
else:
    print(f"\n✗ Failed to send message")
    
    # Check if it's a scope issue
    if response.status_code == 403:
        print(f"  → 403 Forbidden: Token may be missing required scope 'chat:write'")
    elif response.status_code == 401:
        print(f"  → 401 Unauthorized: Token may be expired or invalid")
        print(f"  → Try re-authenticating in the app")
