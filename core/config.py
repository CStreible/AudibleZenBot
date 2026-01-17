"""
Configuration Manager - Save and load application settings
"""

import json
import os
import threading
from typing import Dict, Any
from pathlib import Path


class ConfigManager:
    """Manages application configuration and settings"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize config manager
        
        Args:
            config_file: Path to configuration file
        """
        # Get user's home directory for config storage
        self.config_dir = Path.home() / ".audiblezenbot"
        self.config_dir.mkdir(exist_ok=True)
        
        self.config_file = self.config_dir / config_file
        self._lock = threading.RLock()
        # Verbose config saves can be enabled by env var AZB_VERBOSE_CONFIG=1
        try:
            self.verbose = bool(int(os.environ.get('AZB_VERBOSE_CONFIG', '0')))
        except Exception:
            self.verbose = False
        self.config: Dict[str, Any] = self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file"""
        with self._lock:
            if self.config_file.exists():
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Error loading config: {e}")
                    return self.get_default_config()
            else:
                return self.get_default_config()
    
    def save(self):
        """Save configuration to file"""
        with self._lock:
            try:
                # Debug: Check if trovo streamer_user_id is in config before saving
                if self.verbose:
                    if "platforms" in self.config and "trovo" in self.config["platforms"]:
                        trovo_keys = list(self.config["platforms"]["trovo"].keys())
                        has_user_id = "streamer_user_id" in trovo_keys
                        print(f"[ConfigManager] DEBUG save(): Trovo keys = {trovo_keys}")
                        print(f"[ConfigManager] DEBUG save(): Has streamer_user_id = {has_user_id}")
                        if has_user_id:
                            print(f"[ConfigManager] DEBUG save(): streamer_user_id value = {self.config['platforms']['trovo']['streamer_user_id']}")
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force OS to write to disk
            except Exception as e:
                print(f"Error saving config: {e}")
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "ui": {
                "show_platform_icons": True,
                "sidebar_expanded": False,
                "theme": "dark"
            },
            "platforms": {
                "twitch": {
                    "username": "",
                    "connected": False,
                    "disabled": False,
                    "oauth_token": "vwjvk83rarr5x8sw4agwgc3ciq09br",
                    "refresh_token": "olha5lgahozz0eqhe8me2c1sbkhn9qli9o4wxezitgj96212ul"
                },
                "youtube": {
                    "channel_id": "",
                    "connected": False,
                    "disabled": False,
                    "oauth_token": ""
                },
                "trovo": {
                    "client_id": "",
                    "client_secret": "",
                    "username": "",
                    "connected": False,
                    "disabled": False,
                    "access_token": "892ea7e2c9ad3e719a6e977ab5d69275",
                    "refresh_token": "1a12c7060eecf605b47f1b7da86e6087"
                },
                "kick": {
                    "username": "",
                    "connected": False,
                    "disabled": False,
                    "access_token": "<INSERT_KICK_ACCESS_TOKEN_IF_KNOWN>",
                    "refresh_token": "<INSERT_KICK_REFRESH_TOKEN_IF_KNOWN>",
                    "client_id": "",
                    "client_secret": ""
                },
                "dlive": {
                    "username": "",
                    "connected": False,
                    "disabled": False
                },
                "twitter": {
                    "username": "",
                    "connected": False,
                    "disabled": False,
                    "oauth_token": "AAAAAAAAAAAAAAAAAAAAAASl6gEAAAAAU78VyhsdsRMEEuZccGjLgdZWtd8%3DcmmWESSLcyJ7I6ri4S0kvf3f4vox6h90puDHkPF0p865WgnJgl",
                    "access_token": "1601310606291771392-iq1PD7w2iRPZhJboHSrSGqbwpDUWvQ",
                    "access_token_secret": "E82NKHmYJLOB0phfB0ph5hJ3nA0zB35HdReCVFiuw3IiT"
                }
            },
            "chat": {
                "max_messages": 500,
                "auto_scroll": True,
                "show_timestamps": False
            },
            "ngrok": {
                "auth_token": "",
                "auto_start": True,
                "region": "us",
                "tunnels": {
                    "kick": {"enabled": True, "port": 8889},
                    "trovo": {"enabled": False, "port": 5000}
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value
        
        Args:
            key: Configuration key (use dot notation for nested keys, e.g., 'ui.theme')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        with self._lock:
            keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set a configuration value
        
        Args:
            key: Configuration key (use dot notation for nested keys)
            value: Value to set
        """
        with self._lock:
            # CRITICAL: Reload config before modifying to avoid overwriting other platforms' data
            self.config = self.load()
            keys = key.split('.')
            config = self.config
            # Navigate to the parent dictionary
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            # Set the value
            config[keys[-1]] = value
            # Save to file
            self.save()
    
    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """Get configuration for a specific platform"""
        with self._lock:
          return self.config.get("platforms", {}).get(platform, {})
    
    def set_platform_config(self, platform: str, key: str, value: Any):
        """Set configuration for a specific platform"""
        with self._lock:
            # CRITICAL: Reload config before modifying to avoid overwriting other platforms' data
            self.config = self.load()
            if "platforms" not in self.config:
                self.config["platforms"] = {}
            if platform not in self.config["platforms"]:
                self.config["platforms"][platform] = {}
            self.config["platforms"][platform][key] = value
            self.save()
    
    def reset(self):
        """Reset configuration to defaults"""
        with self._lock:
            self.config = self.get_default_config()
            self.save()

    def merge_platform_stream_info(self, platform: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Atomically merge provided stream_info updates into the stored config for a platform.

        This method reloads the latest config under the lock, deep-merges the
        `updates` dict into `config['platforms'][platform]['stream_info']`,
        saves once, and returns the resulting stream_info dictionary.
        """
        with self._lock:
            # Reload latest config to avoid stomping concurrent changes
            self.config = self.load()
            if 'platforms' not in self.config:
                self.config['platforms'] = {}
            if platform not in self.config['platforms']:
                self.config['platforms'][platform] = {}
            if 'stream_info' not in self.config['platforms'][platform]:
                self.config['platforms'][platform]['stream_info'] = {}

            existing = self.config['platforms'][platform]['stream_info']
            # Shallow-merge updates into existing stream_info (fields are simple strings/lists)
            for k, v in (updates or {}).items():
                existing[k] = v

            # Persist merged config once
            self.save()

            # Return the merged stream_info
            return existing
