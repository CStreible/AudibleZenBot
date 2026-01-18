"""
DLive OAuth2 Authorization Guide

DLive uses OAuth 2.0 for authentication. Follow these steps:

1. Register Your Application:
   - Go to: https://dlive.tv/s/settings?tab=developer
   - Create a new application
   - Set Redirect URI: http://localhost:8080
   - Save your Client ID and Client Secret

2. Get Authorization Code:
   - Open this URL in browser (replace YOUR_CLIENT_ID):
   
   https://dlive.tv/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8080&response_type=code&scope=chat:read+chat:write
   
   - After authorizing, you'll be redirected to localhost with a 'code' parameter
   - Copy the code from the URL

3. Exchange Code for Access Token:
   - Run this command (replace YOUR_CLIENT_ID, YOUR_CLIENT_SECRET, and YOUR_CODE):

   curl -X POST https://dlive.tv/oauth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=authorization_code" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "code=YOUR_CODE" \
     -d "redirect_uri=http://localhost:8080"

4. Save Access Token:
   - Add the access_token to your config.json:
   
    "dlive": {
       "username": "your_dlive_username",
       "access_token": "REPLACE_WITH_YOUR_TOKEN"
    }

Note: DLive GraphQL API endpoint is: wss://graphigo.prd.dlive.tv/
Protocol: graphql-ws (GraphQL over WebSocket)

For more information, visit: https://docs.dlive.tv/
"""

from core.logger import get_logger

logger = get_logger(__name__)

logger.info(__doc__)
