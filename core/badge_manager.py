"""
Badge Manager - Download and cache Twitch badges
"""

import os
import json
try:
    import requests
except Exception:
    requests = None
from pathlib import Path
from typing import Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class BadgeManager:
    """Manages Twitch badge images"""
    
    def __init__(self, cache_dir: str = None):
        """Initialize badge manager"""
        if cache_dir is None:
            # Default to resources/badges directory
            script_dir = Path(__file__).parent.parent
            cache_dir = script_dir / 'resources' / 'badges'
        else:
            cache_dir = Path(cache_dir)
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.badge_urls = {}
        self.cache_file = self.cache_dir / 'badge_urls.json'
        
        # Load cached badge URLs
        self.load_cache()
    
    def load_cache(self):
        """Load cached badge URLs from file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.badge_urls = json.load(f)
            except Exception as e:
                logger.exception(f"Error loading badge cache: {e}")
                self.badge_urls = {}
    
    def save_cache(self):
        """Save badge URLs to cache file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.badge_urls, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving badge cache: {e}")
    
    def fetch_twitch_badges(self, client_id: str, access_token: str, channel_id: str = None):
        """
        Fetch Twitch badge URLs from API
        
        Args:
            client_id: Twitch client ID
            access_token: OAuth access token
            channel_id: Optional channel ID for channel-specific badges
        """
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}'
        }
        
        # Fetch global badges
        try:
            response = requests.get(
                'https://api.twitch.tv/helix/chat/badges/global',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                for badge_set in data.get('data', []):
                    set_id = badge_set['set_id']
                    for version in badge_set.get('versions', []):
                        version_id = version['id']
                        badge_key = f"{set_id}/{version_id}"
                        self.badge_urls[badge_key] = {
                            'url': version['image_url_1x'],
                            'url_2x': version['image_url_2x'],
                            'url_4x': version['image_url_4x'],
                            'title': version.get('title', badge_key)
                        }
                
                self.save_cache()
                logger.info(f"Fetched {len(self.badge_urls)} global Twitch badges")
            else:
                logger.warning(f"Failed to fetch badges: {response.status_code}")
                
        except Exception as e:
            logger.exception(f"Error fetching Twitch badges: {e}")
        
        # Fetch channel-specific badges if channel_id provided
        if channel_id:
            try:
                response = requests.get(
                    f'https://api.twitch.tv/helix/chat/badges?broadcaster_id={channel_id}',
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for badge_set in data.get('data', []):
                        set_id = badge_set['set_id']
                        for version in badge_set.get('versions', []):
                            version_id = version['id']
                            badge_key = f"channel/{set_id}/{version_id}"
                            self.badge_urls[badge_key] = {
                                'url': version['image_url_1x'],
                                'url_2x': version['image_url_2x'],
                                'url_4x': version['image_url_4x'],
                                'title': version.get('title', badge_key)
                            }
                    
                    self.save_cache()
                    logger.info(f"Fetched channel-specific badges for channel {channel_id}")
                    
            except Exception as e:
                logger.exception(f"Error fetching channel badges: {e}")
    
    def download_badge(self, badge_key: str, size: str = '1x') -> Optional[str]:
        """
        Download a badge image and return the local path
        
        Args:
            badge_key: Badge key (e.g., 'moderator/1')
            size: Image size ('1x', '2x', or '4x')
            
        Returns:
            Path to downloaded badge image, or None if not found
        """
        if badge_key not in self.badge_urls:
            logger.warning(f"Badge key {badge_key} not in badge_urls. Available keys: {len(self.badge_urls)}")
            return None
        
        badge_info = self.badge_urls[badge_key]
        url_key = f'url_{size}' if size != '1x' else 'url'
        url = badge_info.get(url_key)
        
        if not url:
            logger.warning(f"No URL found for badge {badge_key} with size {size}")
            return None
        
        # Create filename from badge key
        safe_key = badge_key.replace('/', '_')
        filename = f"{safe_key}_{size}.png"
        filepath = self.cache_dir / filename
        
        # Download if not cached
        if not filepath.exists():
            try:
                logger.info(f"Downloading badge from: {url}")
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Downloaded badge: {badge_key} to {filepath}")
                else:
                    logger.warning(f"Failed to download badge {badge_key}: HTTP {response.status_code}")
                    return None
            except Exception as e:
                logger.exception(f"Error downloading badge {badge_key}: {e}")
                return None
        
        return str(filepath)
    
    def get_badge_url(self, badge_key: str, size: str = '1x') -> Optional[str]:
        """Get the URL for a badge"""
        if badge_key not in self.badge_urls:
            return None
        
        badge_info = self.badge_urls[badge_key]
        url_key = f'url_{size}' if size != '1x' else 'url'
        return badge_info.get(url_key)
    
    def get_badge_title(self, badge_key: str) -> Optional[str]:
        """Get the title/description for a badge"""
        if badge_key not in self.badge_urls:
            return None
        
        badge_info = self.badge_urls[badge_key]
        return badge_info.get('title')
    
    def get_badge_path(self, badge_key: str, size: str = '1x') -> Optional[str]:
        """Get the local path for a cached badge"""
        safe_key = badge_key.replace('/', '_')
        filename = f"{safe_key}_{size}.png"
        filepath = self.cache_dir / filename
        
        if filepath.exists():
            return str(filepath)
        
        return None


# Global badge manager instance
_badge_manager = None


def get_badge_manager() -> BadgeManager:
    """Get the global badge manager instance"""
    global _badge_manager
    if _badge_manager is None:
        _badge_manager = BadgeManager()
    return _badge_manager
