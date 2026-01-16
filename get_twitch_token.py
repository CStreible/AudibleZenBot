"""
Twitch OAuth Token Generator
Generates a new Twitch OAuth token with required scopes for stream management
"""

import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import secrets

# Twitch OAuth configuration
CLIENT_ID = "h84tx3mvvpk9jyt8rv8p8utfzupz82"
REDIRECT_URI = "http://localhost:3000"
SCOPES = [
    "chat:read",
    "chat:edit",
    "user:edit:broadcast",
    "channel:manage:broadcast",
    "channel:read:redemptions",
    "channel:read:subscriptions",
    "bits:read",
    "moderator:read:followers"
]

# Store the token globally when received
received_token = None
received_error = None


class OAuthHandler(BaseHTTPRequestHandler):
    """Handle the OAuth callback from Twitch"""
    
    def do_GET(self):
        """Handle GET request from OAuth callback"""
        global received_token, received_error
        
        # Parse the query parameters
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        # Check for access token in fragment (implicit flow)
        if '#' in self.path:
            fragment = self.path.split('#')[1]
            fragment_params = urllib.parse.parse_qs(fragment)
            if 'access_token' in fragment_params:
                received_token = fragment_params['access_token'][0]
        
        # Check for error
        if 'error' in params:
            received_error = params['error_description'][0] if 'error_description' in params else params['error'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: #e74c3c;">❌ Error</h1>
                    <p>{received_error}</p>
                    <p>You can close this window and check the terminal.</p>
                </body>
                </html>
            """.encode())
            return
        
        # Check for access token in query (should be in fragment for implicit flow)
        if 'access_token' in params:
            received_token = params['access_token'][0]
        
        # Send success response
        if received_token:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write("""
                <html>
                <head>
                    <script>
                        // Extract token from URL fragment and send to server
                        const fragment = window.location.hash.substring(1);
                        const params = new URLSearchParams(fragment);
                        const token = params.get('access_token');
                        if (token) {
                            fetch('/token?access_token=' + token);
                        }
                    </script>
                </head>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: #9146ff;">✅ Authorization Successful!</h1>
                    <p>Your new Twitch token has been generated.</p>
                    <p>Check the terminal for your token.</p>
                    <p>You can close this window now.</p>
                </body>
                </html>
            """.encode())
        else:
            # Show page that will extract token from fragment
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write("""
                <html>
                <head>
                    <script>
                        // Extract token from URL fragment and send to server
                        const fragment = window.location.hash.substring(1);
                        const params = new URLSearchParams(fragment);
                        const token = params.get('access_token');
                        if (token) {
                            fetch('/token?access_token=' + encodeURIComponent(token))
                                .then(() => {
                                    document.body.innerHTML = '<div style="font-family: Arial; padding: 50px; text-align: center;"><h1 style="color: #9146ff;">✅ Authorization Successful!</h1><p>Your new Twitch token has been generated.</p><p>Check the terminal for your token.</p><p>You can close this window now.</p></div>';
                                });
                        } else {
                            document.body.innerHTML = '<div style="font-family: Arial; padding: 50px; text-align: center;"><h1 style="color: #e74c3c;">❌ No token found</h1><p>Please try again.</p></div>';
                        }
                    </script>
                </head>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <p>Processing authorization...</p>
                </body>
                </html>
            """.encode())
    
    def log_message(self, format, *args):
        """Suppress server log messages"""
        pass


def main():
    """Main function to generate Twitch OAuth token"""
    print("=" * 60)
    print("🎮 Twitch OAuth Token Generator")
    print("=" * 60)
    print()
    print("Scopes requested:")
    for scope in SCOPES:
        print(f"  • {scope}")
    print()
    print("📝 Instructions:")
    print("1. Your browser will open with Twitch authorization")
    print("2. Log in to Twitch (if not already logged in)")
    print("3. Click 'Authorize' to grant permissions")
    print("4. The token will appear here in the terminal")
    print()
    
    # Generate state for security
    state = secrets.token_urlsafe(16)
    
    # Build authorization URL (using implicit flow for simplicity)
    auth_params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'token',  # Implicit flow
        'scope': ' '.join(SCOPES),
        'state': state,
        'force_verify': 'true'  # Force re-authorization
    }
    
    auth_url = f"https://id.twitch.tv/oauth2/authorize?{urllib.parse.urlencode(auth_params)}"
    
    # Start local server to receive callback
    server = HTTPServer(('localhost', 3000), OAuthHandler)
    
    print("🌐 Opening browser for authorization...")
    print()
    webbrowser.open(auth_url)
    
    print("⏳ Waiting for authorization...")
    print("   (Server running on http://localhost:3000)")
    print()
    
    # Handle one request (the callback)
    server.handle_request()
    # Handle the token extraction request
    server.handle_request()
    
    server.server_close()
    
    if received_error:
        print()
        print("❌ Error occurred:")
        print(f"   {received_error}")
        print()
        sys.exit(1)
    
    if received_token:
        print()
        print("=" * 60)
        print("✅ SUCCESS! Your new Twitch OAuth token:")
        print("=" * 60)
        print()
        print(received_token)
        print()
        print("=" * 60)
        print()
        print("📋 Next steps:")
        print("1. Copy the token above")
        print("2. Open: C:\\Users\\cstre\\.audiblezenbot\\config.json")
        print("3. Find: platforms.twitch.oauth_token")
        print("4. Replace the old token with the new one")
        print("5. Save the file")
        print("6. Restart AudibleZenBot")
        print("7. Go to Stream Info and try saving again!")
        print()
    else:
        print()
        print("❌ No token received. Please try again.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
