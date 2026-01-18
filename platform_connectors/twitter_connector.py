"""
Twitter (X) Platform Connector
Connects to Twitter/X API v2 for tweet streams and mentions
"""

import time
import requests
from platform_connectors.base_connector import BasePlatformConnector
from PyQt6.QtCore import QThread, pyqtSignal
from core.logger import get_logger

logger = get_logger(__name__)


class TwitterConnector(BasePlatformConnector):
    """Connector for Twitter/X tweet streams and mentions"""
    
    # OAuth credentials from oauth_handler
    DEFAULT_CLIENT_ID = ""
    DEFAULT_CLIENT_SECRET = ""
    DEFAULT_API_KEY = ""
    DEFAULT_API_SECRET = ""
    
    def __init__(self, config=None):
        super().__init__()
        self.worker_thread = None
        self.worker = None
        self.config = config
        self.oauth_token = None
        self.refresh_token = None
        self.client_id = self.DEFAULT_CLIENT_ID
        self.client_secret = self.DEFAULT_CLIENT_SECRET
        self.api_key = self.DEFAULT_API_KEY
        self.api_secret = self.DEFAULT_API_SECRET
        
        # Load token from config if available
        self.access_token = None
        self.access_token_secret = None
        if self.config:
            twitter_config = self.config.get_platform_config('twitter')
            logger.debug(f"[TwitterConnector] Twitter config: {twitter_config}")
            token = twitter_config.get('oauth_token', '')
            if token:
                self.oauth_token = token
                logger.debug(f"[TwitterConnector] Loaded OAuth token from config")
            refresh = twitter_config.get('refresh_token', '')
            if refresh:
                self.refresh_token = refresh
            # Load OAuth 1.0a credentials
            self.access_token = twitter_config.get('access_token', '')
            self.access_token_secret = twitter_config.get('access_token_secret', '')
            logger.debug(f"[TwitterConnector] Access token from config: {self.access_token[:20] if self.access_token else 'None'}...")
            logger.debug(f"[TwitterConnector] Access secret from config: {self.access_token_secret[:20] if self.access_token_secret else 'None'}...")
            if self.access_token and self.access_token_secret:
                logger.debug(f"[TwitterConnector] Loaded OAuth 1.0a credentials")
            # Load client credentials from config if present
            try:
                cid = twitter_config.get('client_id', '')
                csec = twitter_config.get('client_secret', '')
                if cid:
                    self.client_id = cid
                if csec:
                    self.client_secret = csec
            except Exception:
                pass
    
    def set_token(self, token: str):
        """Set OAuth token"""
        self.oauth_token = token
        if self.config:
            self.config.set_platform_config('twitter', 'oauth_token', token)
    
    def set_refresh_token(self, refresh_token: str):
        """Set OAuth refresh token"""
        self.refresh_token = refresh_token
        if self.config:
            self.config.set_platform_config('twitter', 'refresh_token', refresh_token)
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            return False
        
        try:
            response = requests.post(
                'https://api.twitter.com/2/oauth2/token',
                auth=(self.client_id, self.client_secret),
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.oauth_token = data.get('access_token')
                new_refresh = data.get('refresh_token')
                if new_refresh:
                    self.refresh_token = new_refresh
                    if self.config:
                        self.config.set_platform_config('twitter', 'refresh_token', new_refresh)
                logger.info("Twitter token refreshed successfully")
                return True
            else:
                logger.error(f"Twitter token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"Error refreshing Twitter token: {e}")
            return False
    
    def connect(self, username: str):
        """Connect to Twitter/X for a specific user's mentions and timeline"""
        # DISABLED: Twitter chat API does not support live broadcast chat rooms
        # The /chat feature is not accessible via Twitter's public API
        # Implementation kept for future use if API becomes available
        logger.info(f"[TwitterConnector] Twitter/X integration is currently disabled")
        logger.info(f"[TwitterConnector] Live broadcast chat is not available via Twitter API")
        self.error_occurred.emit("Twitter/X chat integration is currently disabled. Live broadcast chat not supported by API.")
        return
        
        # Try to refresh token if we have a refresh token
        if self.refresh_token:
            self.refresh_access_token()
        
        # Create worker thread
        self.worker = TwitterWorker(
            username,
            self.oauth_token,
            self.client_id,
            self.client_secret,
            self.refresh_token,
            self.access_token,
            self.access_token_secret,
            self.api_key,
            self.api_secret,
            self.broadcast_hashtag
        )
        self.worker_thread = QThread()
        
        self.worker.moveToThread(self.worker_thread)
        self.worker.message_signal.connect(self.onMessageReceived)
        self.worker.status_signal.connect(self.onStatusChanged)
        self.worker.error_signal.connect(self.onError)
        
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()
    
    def disconnect(self):
        """Disconnect from Twitter"""
        if self.worker:
            self.worker.stop()
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self.connected = False
        self.connection_status.emit(False)
    
    def send_message(self, message: str):
        """Send a tweet"""
        if self.worker and self.connected:
            self.worker.send_tweet(message)
    
    def onMessageReceived(self, username: str, message: str, metadata: dict):
        """Handle received message"""
        logger.debug(f"[TwitterConnector] onMessageReceived: {username}, {message}")
        self.message_received_with_metadata.emit('twitter', username, message, metadata)
    
    def onStatusChanged(self, connected: bool):
        """Handle connection status change"""
        self.connected = connected
        self.connection_status.emit(connected)
    
    def onError(self, error: str):
        """Handle error"""
        self.error_occurred.emit(error)


class TwitterWorker(QThread):
    """Worker thread for Twitter API v2 connection"""
    
    message_signal = pyqtSignal(str, str, dict)  # username, message, metadata
    status_signal = pyqtSignal(bool)  # connected
    error_signal = pyqtSignal(str)  # error
    
    API_BASE = 'https://api.twitter.com/2'
    
    def __init__(self, username: str, oauth_token: str | None = None,
                 client_id: str | None = None, client_secret: str | None = None,
                 refresh_token: str | None = None,
                 access_token: str | None = None, access_token_secret: str | None = None,
                 api_key: str | None = None, api_secret: str | None = None,
                 broadcast_hashtag: str | None = None):
        super().__init__()
        self.username = username
        self.oauth_token = oauth_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.api_key = api_key
        self.api_secret = api_secret
        self.broadcast_hashtag = broadcast_hashtag or f"#{username}Live"
        self.running = False
        self.user_id = None
        self.processed_tweets = set()
        self.last_token_refresh = time.time()
        self.since_id = None  # Track last processed tweet
    
    def run(self):
        """Run the Twitter connection"""
        logger.info(f"[TwitterWorker] Starting worker for user: {self.username}")
        logger.debug(f"[TwitterWorker] OAuth Token: {'Set' if self.oauth_token else 'Not set'}")
        logger.debug(f"[TwitterWorker] Access Token: {'Set' if self.access_token else 'Not set'}")
        logger.debug(f"[TwitterWorker] Access Token Secret: {'Set' if self.access_token_secret else 'Not set'}")
        logger.debug(f"[TwitterWorker] API Key: {'Set' if self.api_key else 'Not set'}")
        logger.debug(f"[TwitterWorker] API Secret: {'Set' if self.api_secret else 'Not set'}")
        
        self.running = True
        
        if not self.oauth_token:
            error_msg = "No OAuth token provided. Cannot connect to Twitter."
            print(f"[TwitterWorker] ERROR: {error_msg}")
            self.error_signal.emit(error_msg)
            self.status_signal.emit(False)
            return
        
        try:
            # Get user ID from username
            if not self.get_user_id():
                self.error_signal.emit(f"Could not find user: {self.username}")
                self.status_signal.emit(False)
                return
            
            self.status_signal.emit(True)
            
            # Poll for timeline and relevant tweets
            while self.running:
                try:
                    # Refresh token if needed (every 50 minutes)
                    if time.time() - self.last_token_refresh > 3000:
                        if self.refresh_access_token():
                            self.last_token_refresh = time.time()
                    
                    # Search for broadcast-related tweets
                    self.search_broadcast_tweets()
                    
                    # Fetch mentions
                    self.fetch_mentions()
                    
                    # Sleep before next poll (increased to reduce rate limit hits)
                    time.sleep(30)  # Poll every 30 seconds to stay within rate limits
                    
                except Exception as e:
                    self.error_signal.emit(f"Error fetching tweets: {str(e)}")
                    time.sleep(15)
                    
        except Exception as e:
            self.error_signal.emit(f"Connection error: {str(e)}")
            self.status_signal.emit(False)
    
    def get_user_id(self) -> bool:
        """Get the user ID from username"""
        try:
            # Use OAuth 1.0a if available, otherwise bearer token
            if self.access_token and self.access_token_secret:
                from requests_oauthlib import OAuth1
                auth = OAuth1(
                    self.api_key,
                    self.api_secret,
                    self.access_token,
                    self.access_token_secret
                )
                response = requests.get(
                    f'{self.API_BASE}/users/by/username/{self.username}',
                    auth=auth
                )
            else:
                headers = {
                    'Authorization': f'Bearer {self.oauth_token}'
                }
                response = requests.get(
                    f'{self.API_BASE}/users/by/username/{self.username}',
                    headers=headers
                )
            
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get('data', {}).get('id')
                logger.info(f"[TwitterWorker] Found user ID: {self.user_id}")
                return self.user_id is not None
            else:
                logger.error(f"[TwitterWorker] Error getting user ID: {response.status_code}")
                logger.debug(f"[TwitterWorker] Response: {response.text}")
                return False
                
        except Exception as e:
            logger.exception(f"[TwitterWorker] Exception getting user ID: {e}")
            return False
    
    def search_broadcast_tweets(self):
        """Search for tweets related to live broadcast (hashtag, mentions during stream)"""
        try:
            # Search for: hashtag OR mentions of username (recent tweets)
            query = f"{self.broadcast_hashtag} OR @{self.username}"
            
            params = {
                'query': query,
                'max_results': 10,
                'tweet.fields': 'created_at,author_id,conversation_id',
                'expansions': 'author_id',
                'user.fields': 'username,name,profile_image_url',
                'sort_order': 'recency'
            }
            
            # Add since_id if we have it
            if self.since_id:
                params['since_id'] = self.since_id
            
            # Use OAuth 1.0a
            if self.access_token and self.access_token_secret:
                from requests_oauthlib import OAuth1
                auth = OAuth1(
                    self.api_key,
                    self.api_secret,
                    self.access_token,
                    self.access_token_secret
                )
                response = requests.get(
                    f'{self.API_BASE}/tweets/search/recent',
                    auth=auth,
                    params=params
                )
            else:
                headers = {
                    'Authorization': f'Bearer {self.oauth_token}'
                }
                response = requests.get(
                    f'{self.API_BASE}/tweets/search/recent',
                    headers=headers,
                    params=params
                )
            
            if response.status_code == 200:
                data = response.json()
                
                # Update since_id for next request
                meta = data.get('meta', {})
                if 'newest_id' in meta:
                    self.since_id = meta['newest_id']
                
                tweets = data.get('data', [])
                users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
                
                # Process tweets in chronological order
                for tweet in reversed(tweets):
                    tweet_id = tweet['id']

                    # Skip if already processed
                    if tweet_id in self.processed_tweets:
                        continue

                    self.processed_tweets.add(tweet_id)

                    # Get author info
                    author_id = tweet.get('author_id')
                    author = users.get(author_id, {})
                    author_username = author.get('username', 'unknown')
                    author_name = author.get('name', author_username)

                    # Get tweet text
                    text = tweet.get('text', '')

                    # Prepare metadata
                    metadata = {
                        'tweet_id': tweet_id,
                        'author_id': author_id,
                        'created_at': tweet.get('created_at', ''),
                        'profile_image_url': author.get('profile_image_url', ''),
                        'verified': author.get('verified', False),
                        'badges': []
                    }

                    # Emit the message
                    logger.info(f"[TwitterWorker] Broadcasting tweet from {author_name}: {text[:50]}...")
                    self.message_signal.emit(author_name, text, metadata)
                
                # Keep only last 1000 tweet IDs to avoid memory issues
                if len(self.processed_tweets) > 1000:
                    self.processed_tweets = set(list(self.processed_tweets)[-1000:])
            
            elif response.status_code == 429:
                logger.warning("[TwitterWorker] Rate limit hit on search, waiting longer...")
                time.sleep(60)
            else:
                logger.error(f"[TwitterWorker] Error searching broadcasts: {response.status_code}")
                logger.debug(f"[TwitterWorker] Response: {response.text}")
                
        except Exception as e:
            logger.exception(f"[TwitterWorker] Exception searching broadcasts: {e}")
    
    def fetch_mentions(self):
        """Fetch mentions for the user"""
        if not self.user_id:
            return
        
        try:
            params = {
                'max_results': 10,
                'tweet.fields': 'created_at,author_id,conversation_id',
                'expansions': 'author_id',
                'user.fields': 'username,name,profile_image_url'
            }
            
            # Use OAuth 1.0a
            if self.access_token and self.access_token_secret:
                from requests_oauthlib import OAuth1
                auth = OAuth1(
                    self.api_key,
                    self.api_secret,
                    self.access_token,
                    self.access_token_secret
                )
                response = requests.get(
                    f'{self.API_BASE}/users/{self.user_id}/mentions',
                    auth=auth,
                    params=params
                )
            else:
                return
            
            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])
                users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
                
                # Process new mentions
                for tweet in reversed(tweets):
                    tweet_id = tweet['id']
                    
                    if tweet_id in self.processed_tweets:
                        continue
                    
                    self.processed_tweets.add(tweet_id)
                    
                    author_id = tweet.get('author_id')
                    author = users.get(author_id, {})
                    author_name = author.get('name', author.get('username', 'unknown'))
                    text = tweet.get('text', '')
                    
                    metadata = {
                        'tweet_id': tweet_id,
                        'author_id': author_id,
                        'created_at': tweet.get('created_at', ''),
                        'profile_image_url': author.get('profile_image_url', ''),
                        'verified': author.get('verified', False),
                        'badges': []
                    }
                    
                    print(f"[TwitterWorker] Mention from {author_name}: {text[:50]}...")
                    self.message_signal.emit(author_name, text, metadata)
                    
        except Exception as e:
            print(f"[TwitterWorker] Exception fetching mentions: {e}")
    
    def fetch_home_timeline(self):
        """Fetch home timeline tweets (from accounts you follow)"""
        if not self.user_id:
            return
        
        try:
            params = {
                'max_results': 10,
                'tweet.fields': 'created_at,author_id,conversation_id,in_reply_to_user_id',
                'expansions': 'author_id,in_reply_to_user_id',
                'user.fields': 'username,name,profile_image_url'
            }
            
            # Add since_id if we have it
            if self.since_id:
                params['since_id'] = self.since_id
            
            # Use OAuth 1.0a if available
            if self.access_token and self.access_token_secret:
                from requests_oauthlib import OAuth1
                auth = OAuth1(
                    self.api_key,
                    self.api_secret,
                    self.access_token,
                    self.access_token_secret
                )
                # Get user's timeline (tweets from followed accounts)
                response = requests.get(
                    f'{self.API_BASE}/users/{self.user_id}/timelines/reverse_chronological',
                    auth=auth,
                    params=params
                )
            else:
                headers = {
                    'Authorization': f'Bearer {self.oauth_token}'
                }
                response = requests.get(
                    f'{self.API_BASE}/users/{self.user_id}/timelines/reverse_chronological',
                    headers=headers,
                    params=params
                )
            
            if response.status_code == 200:
                data = response.json()
                
                # Update since_id for next request
                meta = data.get('meta', {})
                if 'newest_id' in meta:
                    self.since_id = meta['newest_id']
                
                tweets = data.get('data', [])
                users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
                
                # Process tweets in chronological order
                for tweet in reversed(tweets):
                    tweet_id = tweet['id']
                    
                    # Skip if already processed
                    if tweet_id in self.processed_tweets:
                        continue
                    
                    self.processed_tweets.add(tweet_id)
                    
                    # Get author info
                    author_id = tweet.get('author_id')
                    author = users.get(author_id, {})
                    author_username = author.get('username', 'unknown')
                    author_name = author.get('name', author_username)
                    
                    # Get tweet text
                    text = tweet.get('text', '')
                    
                    # Prepare metadata
                    metadata = {
                        'tweet_id': tweet_id,
                        'author_id': author_id,
                        'created_at': tweet.get('created_at', ''),
                        'profile_image_url': author.get('profile_image_url', ''),
                        'verified': author.get('verified', False),
                        'badges': []
                    }
                    
                    # Emit the message
                    self.message_signal.emit(author_name, text, metadata)
                
                # Keep only last 1000 tweet IDs to avoid memory issues
                if len(self.processed_tweets) > 1000:
                    self.processed_tweets = set(list(self.processed_tweets)[-1000:])
            
            elif response.status_code == 429:
                print("[TwitterWorker] Rate limit hit, waiting longer...")
                time.sleep(60)
            else:
                print(f"[TwitterWorker] Error fetching timeline: {response.status_code}")
                
        except Exception as e:
            print(f"[TwitterWorker] Exception fetching timeline: {e}")
    
    def fetch_tweet_replies(self):
        """Fetch replies to the user's recent tweets"""
        if not self.user_id:
            return
        
        try:
            # First, get user's recent tweets
            params = {
                'max_results': 5,
                'tweet.fields': 'created_at,conversation_id'
            }
            
            if self.access_token and self.access_token_secret:
                from requests_oauthlib import OAuth1
                auth = OAuth1(
                    self.api_key,
                    self.api_secret,
                    self.access_token,
                    self.access_token_secret
                )
                response = requests.get(
                    f'{self.API_BASE}/users/{self.user_id}/tweets',
                    auth=auth,
                    params=params
                )
            else:
                return
            
            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])
                
                # For each recent tweet, search for replies
                for tweet in tweets[:2]:  # Only check 2 most recent to avoid rate limits
                    conversation_id = tweet.get('id')
                    self.fetch_conversation(conversation_id)
            
        except Exception as e:
            print(f"[TwitterWorker] Exception fetching tweet replies: {e}")
    
    def fetch_conversation(self, conversation_id: str):
        """Fetch tweets in a conversation thread"""
        try:
            params = {
                'query': f'conversation_id:{conversation_id}',
                'max_results': 10,
                'tweet.fields': 'created_at,author_id,conversation_id',
                'expansions': 'author_id',
                'user.fields': 'username,name,profile_image_url'
            }
            
            if self.access_token and self.access_token_secret:
                from requests_oauthlib import OAuth1
                auth = OAuth1(
                    self.api_key,
                    self.api_secret,
                    self.access_token,
                    self.access_token_secret
                )
                response = requests.get(
                    f'{self.API_BASE}/tweets/search/recent',
                    auth=auth,
                    params=params
                )
            else:
                return
            
            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])
                users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
                
                # Process tweets in chronological order
                for tweet in reversed(tweets):
                    tweet_id = tweet['id']
                    
                    if tweet_id in self.processed_tweets:
                        continue
                    
                    self.processed_tweets.add(tweet_id)
                    
                    author_id = tweet.get('author_id')
                    author = users.get(author_id, {})
                    author_username = author.get('username', 'unknown')
                    author_name = author.get('name', author_username)
                    
                    text = tweet.get('text', '')
                    
                    metadata = {
                        'tweet_id': tweet_id,
                        'author_id': author_id,
                        'created_at': tweet.get('created_at', ''),
                        'profile_image_url': author.get('profile_image_url', ''),
                        'verified': author.get('verified', False),
                        'badges': []
                    }
                    
                    self.message_signal.emit(author_name, text, metadata)
                
        except Exception as e:
            print(f"[TwitterWorker] Exception fetching conversation: {e}")
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            return False
        
        try:
            response = requests.post(
                'https://api.twitter.com/2/oauth2/token',
                auth=(self.client_id, self.client_secret),
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.oauth_token = data.get('access_token')
                new_refresh = data.get('refresh_token')
                if new_refresh:
                    self.refresh_token = new_refresh
                print("[TwitterWorker] Token refreshed successfully")
                return True
            else:
                print(f"[TwitterWorker] Token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[TwitterWorker] Error refreshing token: {e}")
            return False
    
    def send_tweet(self, message: str):
        """Send a tweet"""
        if not self.oauth_token:
            print("[TwitterWorker] Cannot send tweet: No OAuth token")
            return
        
        try:
            headers = {
                'Authorization': f'Bearer {self.oauth_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'text': message
            }
            
            response = requests.post(
                f'{self.API_BASE}/tweets',
                headers=headers,
                json=data
            )
            
            if response.status_code == 201:
                print(f"[TwitterWorker] Tweet sent successfully")
            else:
                print(f"[TwitterWorker] Failed to send tweet: {response.status_code}")
                print(f"[TwitterWorker] Response: {response.text}")
                
        except Exception as e:
            print(f"[TwitterWorker] Error sending tweet: {e}")
    
    def stop(self):
        """Stop the worker"""
        self.running = False
