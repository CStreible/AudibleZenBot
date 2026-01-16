"""
Test DLive user info query to find correct username
"""
import asyncio
import json
import websockets

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoidXNlciIsInVzZXJuYW1lIjoiYXVkaWJsZXplbmxpZmUiLCJleHAiOjE3NjgyNjY4MDh9.vwZmcVqxzqX7o7xh1FZKGww8s5zFV20b6OKt3TFqVoc"
USERNAME = "AudibleZenLife"
WS_URL = "wss://graphigostream.prd.dlive.tv"

async def query_user():
    print(f"Querying user info for: {USERNAME}")
    
    # Connect
    async with websockets.connect(
        WS_URL,
        subprotocols=["graphql-ws"],
        extra_headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    ) as ws:
        print("✓ WebSocket connected")
        
        # Send connection_init
        await ws.send(json.dumps({
            "type": "connection_init",
            "payload": {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        }))
        
        # Wait for ack
        msg = json.loads(await ws.recv())
        print(f"✓ Received: {msg.get('type')}")
        
        if msg.get("type") != "connection_ack":
            print(f"✗ Unexpected response: {msg}")
            return
        
        # Query user info
        query = """
        query UserQuery($displayname: String!) {
            userByDisplayName(displayname: $displayname) {
                id
                username
                displayname
                livestream {
                    id
                    title
                }
            }
        }
        """
        
        print(f"\n=== Querying user: {USERNAME} ===\n")
        
        await ws.send(json.dumps({
            "id": "query1",
            "type": "start",
            "payload": {
                "query": query,
                "variables": {"displayname": USERNAME}
            }
        }))
        
        # Wait for response
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            
            if data.get('type') == 'data' and data.get('id') == 'query1':
                print("✓ User data received:")
                print(json.dumps(data, indent=2))
                
                user = data.get('payload', {}).get('data', {}).get('userByDisplayName')
                if user:
                    print(f"\n📝 User Info:")
                    print(f"   ID: {user.get('id')}")
                    print(f"   Username: {user.get('username')}")
                    print(f"   Display Name: {user.get('displayname')}")
                    if user.get('livestream'):
                        print(f"   🔴 LIVE: {user['livestream'].get('title')}")
                        print(f"   Stream ID: {user['livestream'].get('id')}")
                    else:
                        print(f"   ⚫ OFFLINE")
                break
            elif data.get('type') == 'error':
                print(f"❌ Error: {json.dumps(data, indent=2)}")
                break
            elif data.get('type') == 'complete':
                print("Query completed")
                break

if __name__ == "__main__":
    try:
        asyncio.run(query_user())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
