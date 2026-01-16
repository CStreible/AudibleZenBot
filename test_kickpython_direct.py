"""
Test kickpython package directly to see if it can send messages
"""
import asyncio
from kickpython import KickAPI

async def test_send():
    # Your OAuth credentials
    client_id = "01KDPP3YN4SB6ZMSV6R6HM12C7"
    client_secret = "cf46287e05ebf1c68bc7a5fda41cb42da6015cd08c06ca788e6cbd3657a36e81"
    redirect_uri = "http://localhost:8890/callback"
    
    # Your access token (from your most recent authentication)
    access_token = "ZMQYNDK0MDGTNDC2ZC0Z..."  # Replace with full token from logs
    
    # Your channel info
    broadcaster_user_id = "3403590"
    chatroom_id = "3328548"
    
    print(f"Testing kickpython with:")
    print(f"  Broadcaster ID: {broadcaster_user_id}")
    print(f"  Chatroom ID: {chatroom_id}")
    print(f"  Token: {access_token[:20]}...")
    
    # Create API instance
    api = KickAPI(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )
    
    # Manually store the token in its database
    api._store_token(
        channel_id=broadcaster_user_id,  # Store with broadcaster ID as key
        access_token=access_token,
        refresh_token="dummy",  # Won't need this for test
        expires_in=3600,
        scope="user:read channel:read channel:write chat:write events:subscribe"
    )
    
    print(f"\nAttempting to send message via kickpython...")
    
    try:
        # Try to send a message using kickpython
        result = await api.post_chat(
            channel_id=broadcaster_user_id,  # Use broadcaster ID as channel_id
            content="Test from kickpython direct"
        )
        print(f"✓ Success! Response: {result}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    
    await api.close()

if __name__ == "__main__":
    asyncio.run(test_send())
