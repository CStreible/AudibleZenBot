"""
Configuration Manager - Save and load application settings
"""

import json
import os
import threading
from typing import Dict, Any
from pathlib import Path
from core import secret_store
from copy import deepcopy
from core.logger import get_logger

logger = get_logger(__name__)

# Keys considered sensitive and should be encrypted on disk
SENSITIVE_KEYS = ['bot_token', 'streamer_token', 'access_token', 'refresh_token', 'client_secret', 'access_token_secret', 'api_key', 'streamer_cookies', 'oauth_token']


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
                        loaded = json.load(f)
                        # Decrypt any sensitive fields stored as ENC:... in platforms
                        try:
                            platforms = loaded.get('platforms', {}) if isinstance(loaded, dict) else {}
                            for pname, pdata in (platforms or {}).items():
                                if not isinstance(pdata, dict):
                                    continue
                                for sk in SENSITIVE_KEYS:
                                    if sk in pdata and isinstance(pdata[sk], str) and pdata[sk].startswith('ENC:'):
                                        try:
                                            pdata[sk] = secret_store.unprotect_string(pdata[sk])
                                        except Exception:
                                            pdata[sk] = ''
                        except Exception:
                            pass
                        return loaded
                except Exception as e:
                    logger.exception(f"Error loading config: {e}")
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
                            logger.debug(f"[ConfigManager] DEBUG save(): Trovo keys = {trovo_keys}")
                            logger.debug(f"[ConfigManager] DEBUG save(): Has streamer_user_id = {has_user_id}")
                            if has_user_id:
                                logger.debug(f"[ConfigManager] DEBUG save(): streamer_user_id value = {self.config['platforms']['trovo']['streamer_user_id']}")
                # Make a deep copy and encrypt sensitive fields before writing
                write_copy = deepcopy(self.config)
                try:
                    platforms = write_copy.get('platforms', {}) if isinstance(write_copy, dict) else {}
                    for pname, pdata in (platforms or {}).items():
                        if not isinstance(pdata, dict):
                            continue
                        for sk in SENSITIVE_KEYS:
                            if sk in pdata and isinstance(pdata[sk], str) and pdata[sk]:
                                val = pdata[sk]
                                # If already encrypted (starts with ENC:), leave as-is
                                if not val.startswith('ENC:'):
                                    try:
                                        pdata[sk] = secret_store.protect_string(val)
                                    except Exception:
                                        pass
                except Exception:
                    pass

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(write_copy, f, indent=4)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force OS to write to disk
            except Exception as e:
                logger.exception(f"Error saving config: {e}")
    
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
                    "oauth_token": "",
                    "refresh_token": ""
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
                    "access_token": "",
                    "refresh_token": ""
                },
                "kick": {
                    "username": "",
                    "connected": False,
                    "disabled": False,
                    "access_token": "",
                    "refresh_token": "",
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
                    "oauth_token": "",
                    "access_token": "",
                    "access_token_secret": ""
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
                    "kill_existing_on_startup": False,
                    "callback_port": 8889,
                    "tunnels": {
                    "kick": {"enabled": True, "port": 8889},
                    "trovo": {"enabled": False, "port": 5000}
                }
            }
            ,
            "debug": {
                "all": False
            },
            "logging": {
                "enabled": False,
                "folder": "",
                "levels": {
                    "TRACE": False,
                    "DIAG": False,
                    "DEBUG": False,
                    "INFO": True,
                    "WARN": True,
                    "ERROR": True,
                    "CRITICAL": True
                },
                # Per-category overrides structure: {"category": {"DEBUG": True, ...}}
                "category_levels": {}
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
            raw = self.config.get("platforms", {}).get(platform, {})
            # Return a decrypted copy for sensitive fields
            if not raw:
                return {}
            result = dict(raw)
            # Decrypt known sensitive keys if present
            sensitive = ['bot_token', 'streamer_token', 'access_token', 'refresh_token', 'client_secret', 'access_token_secret', 'api_key', 'streamer_cookies']
            for k in sensitive:
                if k in result and isinstance(result[k], str) and result[k].startswith('ENC:'):
                    try:
                        result[k] = secret_store.unprotect_string(result[k])
                    except Exception:
                        result[k] = ''
            return result
    
    def set_platform_config(self, platform: str, key: str, value: Any):
        """Set configuration for a specific platform"""
        with self._lock:
            # CRITICAL: Reload config before modifying to avoid overwriting other platforms' data
            self.config = self.load()
            if "platforms" not in self.config:
                self.config["platforms"] = {}
            if platform not in self.config["platforms"]:
                self.config["platforms"][platform] = {}
            # Encrypt sensitive keys before persisting
            sensitive = ['bot_token', 'streamer_token', 'access_token', 'refresh_token', 'client_secret', 'access_token_secret', 'api_key', 'streamer_cookies']
            store_value = value
            try:
                if key in sensitive and isinstance(value, str) and value:
                    store_value = secret_store.protect_string(value)
            except Exception:
                store_value = value
            self.config["platforms"][platform][key] = store_value
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
