"""
Test kickpython package using token from config
"""
import asyncio
import json
from kickpython import KickAPI

async def test_send():
    # Load token from config
    try:
        from pathlib import Path
        config_file = Path.home() / ".audiblezenbot" / "config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        kick_config = config.get('platforms', {}).get('kick', {})
        
        access_token = kick_config.get('streamer_token', '')
        username = kick_config.get('streamer_username', '')
        user_id = kick_config.get('streamer_user_id', '')
        
        if not access_token:
            print("✗ No access token found in config")
            return
        
        print(f"Loaded from config:")
        print(f"  Username: {username}")
        print(f"  User ID: {user_id}")
        print(f"  Token: {access_token[:20]}...")
        
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return
    
    # Your OAuth credentials
    client_id = "01KDPP3YN4SB6ZMSV6R6HM12C7"
    client_secret = "cf46287e05ebf1c68bc7a5fda41cb42da6015cd08c06ca788e6cbd3657a36e81"
    redirect_uri = "http://localhost:8890/callback"
    
    # Create API instance
    api = KickAPI(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )
    
    print(f"\nStep 1: Getting broadcaster ID from token...")
    try:
        broadcaster_id = await api.get_broadcaster_id(access_token)
        if broadcaster_id:
            print(f"  ✓ Broadcaster ID: {broadcaster_id}")
        else:
            print(f"  ✗ Could not get broadcaster ID")
            await api.close()
            return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        await api.close()
        return
    
    print(f"\nStep 2: Getting chatroom ID...")
    try:
        chatroom_id, channel_data = await api.get_chatroom_id(username)
        if chatroom_id:
            print(f"  ✓ Chatroom ID: {chatroom_id}")
        else:
            print(f"  ✗ Could not get chatroom ID")
            await api.close()
            return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        await api.close()
        return
    
    print(f"\nStep 3: Storing token in kickpython's database...")
    api._store_token(
        channel_id=str(broadcaster_id),
        access_token=access_token,
        refresh_token="dummy",
        expires_in=3600,
        scope="user:read channel:read channel:write chat:write events:subscribe"
    )
    print(f"  ✓ Token stored")
    
    print(f"\nStep 4: Attempting to send message...")
    try:
        result = await api.post_chat(
            channel_id=str(broadcaster_id),
            content="🤖 Test message from kickpython library"
        )
        print(f"  ✓ SUCCESS! Message sent!")
        print(f"  Response: {result}")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    await api.close()
    print(f"\nTest complete")

if __name__ == "__main__":
    asyncio.run(test_send())
