import requests

TROVO_CLIENT_ID = "b239c1cc698e04e93a164df321d142b3"
TROVO_CLIENT_SECRET = "a6a9471aed462e984c85feb04e39882e"
TROVO_REDIRECT_URI = "https://mistilled-declan-unendable.ngrok-free.dev/callback"
TROVO_TOKEN_URL = "https://open-api.trovo.live/openplatform/exchangetoken"

def exchange_code_for_token(auth_code):
    headers = {
        "Accept": "application/json",
        "client-id": TROVO_CLIENT_ID,
        "Content-Type": "application/json"
    }
    data = {
        "client_secret": TROVO_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": TROVO_REDIRECT_URI
    }
    resp = requests.post(TROVO_TOKEN_URL, headers=headers, json=data)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"[Trovo OAuth] Error: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    code = "6ea05778baf9b07755d84541de8dced4"  # Replace with your code if needed
    token_data = exchange_code_for_token(code)
    if token_data:
        print("Access Token Response:")
        print(token_data)
    else:
        print("Failed to obtain access token.")