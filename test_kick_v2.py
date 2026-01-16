"""
Test v2 API endpoints
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
username = kick_config.get('streamer_username', '')
chatroom_id = 3328548

print(f"Testing v2 endpoints")
print(f"  Username: {username}")
print(f"  Chatroom ID: {chatroom_id}")
print(f"  Token: {access_token[:20]}...")

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}",
    "User-Agent": "AudibleZenBot/1.0"
}

# Try v2 endpoints
test_endpoints = [
    ("https://api.kick.com/v2/chat", {"content": "Test v2 chat"}),
    ("https://api.kick.com/v2/chat/send", {"content": "Test v2 chat/send"}),
    (f"https://api.kick.com/v2/chat/{chatroom_id}", {"content": "Test v2 with chatroom in URL"}),
    (f"https://api.kick.com/v2/chat/{chatroom_id}/send", {"content": "Test v2 chatroom/send"}),
    (f"https://api.kick.com/v2/chatrooms/{chatroom_id}/messages", {"content": "Test v2 chatrooms/messages"}),
    ("https://kick.com/api/v2/messages/send", {"chatroom_id": chatroom_id, "content": "Test messages/send"}),
]

for url, payload in test_endpoints:
    print(f"\n{'='*60}")
    print(f"URL: {url}")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print(f"✓ ✓ ✓ SUCCESS! ✓ ✓ ✓")
            print(f"Working endpoint: {url}")
            print(f"Working payload: {payload}")
            break
    except Exception as e:
        print(f"Error: {e}")
