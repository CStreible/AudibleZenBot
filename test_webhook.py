"""
Test script to verify Kick webhook server is working
"""
import requests
import json

# Test if webhook server is responding
test_url = "http://localhost:8889"

print("Testing webhook server...")
print(f"URL: {test_url}")

try:
    # Test GET request
    response = requests.get(test_url, timeout=2)
    print(f"✓ GET request successful: {response.status_code}")
    print(f"  Response: {response.text[:100]}")
except requests.exceptions.ConnectionError:
    print("✗ Connection failed - server not responding")
    print("  Make sure AudibleZenBot is running")
except Exception as e:
    print(f"✗ Error: {e}")

print("\nAttempting POST request with fake chat message...")
try:
    fake_message = {
        "message_id": "test-123",
        "sender": {
            "username": "TestUser",
            "user_id": 12345,
            "identity": {
                "username_color": "#FF0000",
                "badges": []
            }
        },
        "content": "Test message from script",
        "created_at": "2025-12-31T00:00:00Z",
        "emotes": []
    }
    
    response = requests.post(
        test_url,
        json=fake_message,
        headers={
            "Kick-Event-Type": "chat.message.sent",
            "Kick-Event-Version": "1"
        },
        timeout=2
    )
    print(f"✓ POST request successful: {response.status_code}")
    print("  Check AudibleZenBot console for '[Webhook] Chat message from TestUser'")
except requests.exceptions.ConnectionError:
    print("✗ Connection failed - server not responding")
except Exception as e:
    print(f"✗ Error: {e}")
