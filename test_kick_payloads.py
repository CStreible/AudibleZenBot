"""
Test different message formats with Kick API
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
user_id = kick_config.get('streamer_user_id', '')

print(f"Testing with:")
print(f"  Username: {username}")
print(f"  User ID: {user_id}")
print(f"  Token: {access_token[:20]}...")

url = "https://api.kick.com/public/v1/chat"
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}",
    "User-Agent": "AudibleZenBot/1.0"
}

# Try different payload variations
test_payloads = [
    {"content": "Test 1: content only"},
    {"content": "Test 2: with type", "type": "message"},
    {"content": "Test 3: with type bot", "type": "bot"},
    {"message": "Test 4: message field"},
    {"text": "Test 5: text field"},
    {"content": "Test 6: with chatroom", "chatroom_id": 3328548},
]

for idx, payload in enumerate(test_payloads, 1):
    print(f"\n=== Test {idx} ===")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print(f"✓ SUCCESS!")
            break
    except Exception as e:
        print(f"Error: {e}")
