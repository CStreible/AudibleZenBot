"""
YouTube OAuth2 Authorization Flow (Automated with Local Server)
Gets OAuth token for YouTube Data API v3 access
"""
import requests
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# YouTube OAuth credentials from youtube_connector.py
YOUTUBE_CLIENT_ID = "44621719812-l23h29dbhqjfm6ln6buoojenmiocv1cp.apps.googleusercontent.com"
YOUTUBE_CLIENT_SECRET = "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"
YOUTUBE_REDIRECT_URI = "http://localhost:8080"
YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Required scopes for YouTube chat
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

# Global variable to store the authorization code
auth_code_received = None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from Google"""
    
    def do_GET(self):
        global auth_code_received
        
        # Parse the query parameters
        query_components = parse_qs(urlparse(self.path).query)
        
        if 'code' in query_components:
            auth_code_received = query_components['code'][0]
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            success_html = """
                <html>
                <head><title>Authorization Successful</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: green;">&#10004; Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            """
            self.wfile.write(success_html.encode())
        else:
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            error_html = """
                <html>
                <head><title>Authorization Failed</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: red;">&#10008; Authorization Failed</h1>
                    <p>No authorization code received.</p>
                </body>
                </html>
            """
            self.wfile.write(error_html.encode())
    
    def log_message(self, format, *args):
        # Suppress HTTP logs
        pass

def get_authorization_url():
    """Generate YouTube OAuth authorization URL"""
    params = {
        "response_type": "code",
        "client_id": YOUTUBE_CLIENT_ID,
        "redirect_uri": YOUTUBE_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    url = f"{YOUTUBE_AUTH_URL}?{urlencode(params)}"
    return url

def exchange_code_for_token(auth_code):
    """Exchange authorization code for access token"""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": YOUTUBE_REDIRECT_URI
    }
    
    print(f"\n[DEBUG] Exchanging code with redirect_uri: {YOUTUBE_REDIRECT_URI}")
    resp = requests.post(YOUTUBE_TOKEN_URL, headers=headers, data=data)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"[YouTube OAuth] Error: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("YouTube OAuth2 Authorization Flow (Automated)")
    print("=" * 60)
    print("\nStarting local callback server on port 8080...")
    
    # Start local HTTP server in background
    server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()
    
    print("✓ Local server running")
    print("\nOpening browser for authorization...")
    print("After authorizing, you'll be redirected back automatically.\n")
    
    url = get_authorization_url()
    webbrowser.open(url)
    
    print("=" * 60)
    print("Waiting for authorization...")
    print("(Browser should open automatically)")
    print("=" * 60)
    
    # Wait for the callback (timeout after 2 minutes)
    server_thread.join(timeout=120)
    
    if auth_code_received is None:
        print("\n✗ Timeout: No authorization code received.")
        print("Please try again and complete the authorization quickly.")
        exit(1)
    
    print(f"\n✓ Authorization code received!")
    print(f"\nExchanging code for token...")
    token_data = exchange_code_for_token(auth_code_received)
    
    if token_data:
        print("\n" + "=" * 60)
        print("SUCCESS! Access Token Obtained")
        print("=" * 60)
        print(f"\nAccess Token: {token_data.get('access_token', 'N/A')[:50]}...")
        print(f"Refresh Token: {token_data.get('refresh_token', 'N/A')[:50]}...")
        print(f"Expires In: {token_data.get('expires_in', 'N/A')} seconds")
        print(f"Token Type: {token_data.get('token_type', 'N/A')}")
        
        # Save to config.json
        try:
            import sys, os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from core.config import ConfigManager
            
            config = ConfigManager()
            config.set_platform_config('youtube', 'oauth_token', token_data.get('access_token', ''))
            config.set_platform_config('youtube', 'refresh_token', token_data.get('refresh_token', ''))
            print("\n✓ YouTube oauth_token and refresh_token saved to config.json!")
        except Exception as e:
            print(f"\n✗ Error saving tokens to config: {e}")
            print("\nYou can manually add them to config.json:")
            print(f'  "youtube": {{')
            print(f'    "oauth_token": "{token_data.get("access_token", "")}",')
            print(f'    "refresh_token": "{token_data.get("refresh_token", "")}"')
            print(f'  }}')
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("1. Start the main app: python main.py")
        print("2. Go to Connections → YouTube tab")
        print("3. Enter your Channel ID")
        print("4. Leave token field empty (uses saved token)")
        print("5. Make sure you have an ACTIVE LIVE STREAM running")
        print("6. Click 'Connect & Authorize'")
        print("=" * 60)
    else:
        print("\n✗ Failed to obtain access token.")
        print("Please check the authorization code and try again.")
