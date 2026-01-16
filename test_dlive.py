"""
Test DLive WebSocket subscription directly
"""
import asyncio
import json
import websockets

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoidXNlciIsInVzZXJuYW1lIjoiYXVkaWJsZXplbmxpZmUiLCJleHAiOjE3NjgyNjY4MDh9.vwZmcVqxzqX7o7xh1FZKGww8s5zFV20b6OKt3TFqVoc"
USERNAME = "AudibleZenLife"
WS_URL = "wss://graphigostream.prd.dlive.tv"

async def test_connection():
    print(f"Testing DLive WebSocket for: {USERNAME}")
    print(f"Token: {ACCESS_TOKEN[:50]}...")
    
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
        print("✓ Sent connection_init")
        
        # Wait for ack
        msg = json.loads(await ws.recv())
        print(f"✓ Received: {msg.get('type')}")
        
        if msg.get("type") != "connection_ack":
            print(f"✗ Unexpected response: {msg}")
            return
        
        # Try alternative subscription format
        print("\n=== Testing different subscription formats ===\n")
        
        # Format 1: streamMessageReceived with displayname
        subscription1 = """
        subscription StreamMessages($displayname: String!) {
            streamMessageReceived(displayname: $displayname) {
                type
                ... on ChatText {
                    id
                    content
                    sender {
                        displayname
                        username
                    }
                }
            }
        }
        """
        
        await ws.send(json.dumps({
            "id": "sub1",
            "type": "start",
            "payload": {
                "query": subscription1,
                "variables": {"displayname": USERNAME}
            }
        }))
        print(f"✓ Subscribed (format 1 - displayname): {USERNAME}")
        
        # Wait for any immediate error
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            data = json.loads(msg)
            if data.get('type') == 'error' and data.get('id') == 'sub1':
                print(f"✗ Format 1 error: {data.get('payload')}")
        except asyncio.TimeoutError:
            pass
        
        # Format 2: streamMessageReceived with username (lowercase)
        subscription2 = """
        subscription StreamMessages2($streamer: String!) {
            streamMessageReceived(streamer: $streamer) {
                type
                ... on ChatText {
                    id
                    content
                    sender {
                        displayname
                        username
                    }
                }
            }
        }
        """
        
        await ws.send(json.dumps({
            "id": "sub2",
            "type": "start",
            "payload": {
                "query": subscription2,
                "variables": {"streamer": USERNAME.lower()}
            }
        }))
        print(f"✓ Subscribed (format 2 - lowercase): {USERNAME.lower()}")
        
        # Wait for any immediate error
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            data = json.loads(msg)
            if data.get('type') == 'error' and data.get('id') == 'sub2':
                print(f"✗ Format 2 error: {data.get('payload')}")
        except asyncio.TimeoutError:
            pass
        
        # Listen for messages
        print("\nListening for messages (send 'test' in DLive chat)...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                msg_type = data.get("type")
                
                if msg_type == "ka":
                    print(".", end="", flush=True)  # Keep-alive dot
                elif msg_type == "data":
                    print(f"\n\n📩 MESSAGE RECEIVED:")
                    print(json.dumps(data, indent=2))
                elif msg_type == "error":
                    print(f"\n\n❌ ERROR:")
                    print(json.dumps(data, indent=2))
                else:
                    print(f"\n\n📬 {msg_type.upper()}:")
                    print(json.dumps(data, indent=2))
                    
        except KeyboardInterrupt:
            print("\n\nStopping...")

if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
