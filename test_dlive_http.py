"""
Test DLive user info via HTTP GraphQL
"""
import requests
import json

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoidXNlciIsInVzZXJuYW1lIjoiYXVkaWJsZXplbmxpZmUiLCJleHAiOjE3NjgyNjY4MDh9.vwZmcVqxzqX7o7xh1FZKGww8s5zFV20b6OKt3TFqVoc"
USERNAME = "AudibleZenLife"
GRAPHQL_URL = "https://graphigo.prd.dlive.tv/"

def query_user():
    print(f"Querying user info for: {USERNAME}")
    
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
                watchingCount
            }
        }
    }
    """
    
    response = requests.post(
        GRAPHQL_URL,
        headers={
            "Authorization": ACCESS_TOKEN,
            "Content-Type": "application/json"
        },
        json={
            "query": query,
            "variables": {"displayname": USERNAME}
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"\nFull response:")
    print(json.dumps(data, indent=2))
    
    if 'errors' in data:
        print(f"\n❌ Errors: {data['errors']}")
        return
    
    user = data.get('data', {}).get('userByDisplayName')
    if user:
        print(f"\n📝 User Info:")
        print(f"   ID: {user.get('id')}")
        print(f"   Username: {user.get('username')}")
        print(f"   Display Name: {user.get('displayname')}")
        if user.get('livestream'):
            print(f"   🔴 LIVE: {user['livestream'].get('title')}")
            print(f"   Stream ID: {user['livestream'].get('id')}")
            print(f"   Viewers: {user['livestream'].get('watchingCount')}")
        else:
            print(f"   ⚫ OFFLINE")
    else:
        print(f"\n❌ User not found")

if __name__ == "__main__":
    try:
        query_user()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
