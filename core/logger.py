"""
Logging Module - Handles logging of all debug messages to file
"""

import sys
import os
from datetime import datetime
from typing import Optional
import re


class TeeOutput:
    """Redirects output to both console and file"""
    
    def __init__(self, original_stream, log_file=None, manager=None):
        self.original_stream = original_stream
        self.log_file = log_file
        self.enabled = False
        # Optional LogManager instance to consult for filtering
        self.manager = manager
    
    def write(self, message):
        """Write to both console and log file"""
        # Allow LogManager to filter verbose/trace messages
        try:
            allow = True
            if self.manager and hasattr(self.manager, 'should_emit'):
                allow = self.manager.should_emit(message)
        except Exception:
            allow = True

        if not allow:
            return

        # Always write to console
        self.original_stream.write(message)

        # Write to file if enabled
        if self.enabled and self.log_file and not self.log_file.closed:
            try:
                self.log_file.write(message)
                self.log_file.flush()  # Ensure immediate write
            except Exception as e:
                # Prevent infinite loop by writing error only to console
                try:
                    self.original_stream.write(f"[Logger] Error writing to log file: {e}\n")
                except Exception:
                    pass
    
    def flush(self):
        """Flush both streams"""
        self.original_stream.flush()
        if self.enabled and self.log_file and not self.log_file.closed:
            try:
                self.log_file.flush()
            except:
                pass
    
    def enable(self):
        """Enable logging to file"""
        self.enabled = True
    
    def disable(self):
        """Disable logging to file"""
        self.enabled = False
    
    def set_log_file(self, log_file):
        """Update the log file"""
        self.log_file = log_file
        

class LogManager:
    """Manages application logging to file"""
    
    def __init__(self, config=None):
        self.config = config
        self.log_file = None
        self.log_folder = None
        self.enabled = False
        
        # Store original stdout/stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Create Tee objects
        self.tee_stdout = TeeOutput(self.original_stdout, manager=self)
        self.tee_stderr = TeeOutput(self.original_stderr, manager=self)
        
        # Replace stdout/stderr with Tee objects
        sys.stdout = self.tee_stdout
        sys.stderr = self.tee_stderr
        
        # Load settings from config
        if self.config:
            self.enabled = self.config.get('logging.enabled', False)
            self.log_folder = self.config.get('logging.folder', None)
            # Debug map controls whether verbose messages (TRACE/DIAG/DEBUG)
            # are emitted for given components. Example config:
            # "debug": {"chatmanager": true, "all": false}
            try:
                self.debug_map = self.config.get('debug', {}) or {}
            except Exception:
                self.debug_map = {}
            
            if self.enabled and self.log_folder:
                self.start_logging()
        else:
            self.debug_map = {}

        # Default debug schema - maps keys to human friendly labels
        # UI will use this schema to render toggles
        self._debug_schema = [
            ("all", "Enable all debug messages"),
            ("chatmanager", "Chat pipeline (de-dup / canonical)"),
            ("connectors", "Connector lifecycle (connect/disconnect)"),
            ("connectors.twitch", "Twitch connector verbose"),
            ("connectors.trovo", "Trovo connector verbose"),
            ("sends", "Send operations (bot / streamer traces)"),
            ("network", "Network / HTTP requests"),
            ("auth", "Auth / OAuth flows"),
            ("persistence", "Persistent diagnostic file writes")
        ]
        # Default per-level toggles
        self._level_keys = [
            ('DEBUG', 'Debug messages'),
            ('INFO', 'Informational messages'),
            ('WARN', 'Warnings'),
            ('ERROR', 'Errors'),
            ('CRITICAL', 'Critical failures'),
            ('TRACE', 'Trace / very verbose traces'),
            ('DIAG', 'Diagnostic lines (DIAG)')
        ]
        try:
            self.level_map = self.config.get('logging.levels', {}) if self.config else {}
        except Exception:
            self.level_map = {}
        # Ensure defaults if not present
        for k, _ in self._level_keys:
            if k not in self.level_map:
                # default: allow INFO+ and suppress DEBUG/TRACE/DIAG
                self.level_map[k] = True if k in ('INFO', 'WARN', 'ERROR', 'CRITICAL') else False

    def should_emit(self, message: str) -> bool:
        """Decide whether a message should be emitted to console/log based on
        debug settings. Suppresses verbose tags like [TRACE], [DIAG], [DEBUG]
        unless enabled globally or for the originating component.
        """
        try:
            if not message:
                return True
            # Always allow errors and critical runtime markers
            lowered = message.lower()
            if any(tag in lowered for tag in ['unhandled exception', '[error]', '[✗', 'traceback']):
                return True

            # Check message log level (expects format [Component][LEVEL] ...)
            try:
                tokens = re.findall(r'\[([^\]]+)\]', message)
                level = None
                if len(tokens) >= 2:
                    # tokens[1] expected to be level like DEBUG, INFO
                    level = tokens[1].strip().upper()
                if level:
                    # Map WARN to WARN key used in UI/config
                    if level == 'WARNING':
                        level = 'WARN'
                    if not self.level_map.get(level, True):
                        return False
            except Exception:
                pass

            # If global debug is enabled, allow everything
            if self.debug_map.get('all') or self.debug_map.get('global'):
                return True

            # If message contains verbose tags, consult per-component flags
            verbose_tags = ['[trace]', '[diag]', '[debug]']
            if not any(t in lowered for t in verbose_tags):
                # Not a verbose message; allow by default
                return True

            # Extract first bracketed token as component, e.g. [ChatManager][TRACE]
            comp = None
            try:
                # Find first occurrence like [Name]
                start = message.find('[')
                end = message.find(']', start + 1)
                if start != -1 and end != -1:
                    comp = message[start+1:end].strip().lower()
            except Exception:
                comp = None

            # Support dotted component names like connectors.twitch
            if comp:
                # direct component match
                if self.debug_map.get(comp):
                    return True
                # try parent group (e.g. connectors.twitch -> connectors)
                parts = comp.split('.')
                if len(parts) > 1:
                    parent = parts[0]
                    if self.debug_map.get(parent):
                        return True
                # also allow explicit mapping like 'twitch' to 'connectors.twitch'
                if self.debug_map.get(f"connectors.{comp}"):
                    return True

            # No explicit enable for this component; suppress verbose line
                return True

            # No explicit enable for this component; suppress verbose line
            return False
        except Exception:
            return True
    
    def start_logging(self):
        """Start logging to file"""
        if not self.log_folder:
            sys.stdout.write("[Logger] No log folder configured\n")
            return False
        
        try:
            # Create log folder if it doesn't exist
            os.makedirs(self.log_folder, exist_ok=True)
            
            # Create log file with timestamp header
            log_path = os.path.join(self.log_folder, 'audiblezenbot.log')
            
            # Open in append mode to preserve existing logs
            self.log_file = open(log_path, 'a', encoding='utf-8', buffering=1)
            
            # Write session start marker
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            separator = '=' * 80
            self.log_file.write(f"\n{separator}\n")
            self.log_file.write(f"AudibleZenBot - Logging Started: {timestamp}\n")
            self.log_file.write(f"{separator}\n\n")
            self.log_file.flush()
            
            # Update Tee objects
            self.tee_stdout.set_log_file(self.log_file)
            self.tee_stderr.set_log_file(self.log_file)
            self.tee_stdout.enable()
            self.tee_stderr.enable()
            
            self.enabled = True
            sys.stdout.write(f"[Logger] [OK] Logging enabled: {log_path}\n")
            return True
            
        except Exception as e:
            sys.stderr.write(f"[Logger] [ERROR] Error starting logging: {e}\n")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_logging(self):
        """Stop logging to file"""
        if not self.enabled:
            return
        
        try:
            # Write session end marker
            if self.log_file and not self.log_file.closed:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                separator = '=' * 80
                self.log_file.write(f"\n{separator}\n")
                self.log_file.write(f"AudibleZenBot - Logging Stopped: {timestamp}\n")
                self.log_file.write(f"{separator}\n\n")
                self.log_file.flush()
                self.log_file.close()
            
            # Disable Tee objects
            self.tee_stdout.disable()
            self.tee_stderr.disable()
            
            self.enabled = False
            sys.stdout.write("[Logger] [OK] Logging disabled\n")
            
        except Exception as e:
            sys.stderr.write(f"[Logger] [ERROR] Error stopping logging: {e}\n")
    
    def set_log_folder(self, folder_path):
        """Set the log folder and restart logging if enabled"""
        self.log_folder = folder_path
        
        # Save to config
        if self.config:
            self.config.set('logging.folder', folder_path)
        
        # Restart logging if currently enabled
        if self.enabled:
            self.stop_logging()
            self.start_logging()
    
    def toggle_logging(self, enabled):
        """Enable or disable logging"""
        if enabled:
            if not self.log_folder:
                sys.stderr.write("[Logger] Cannot enable logging: No folder configured\n")
                return False
            
            if not self.enabled:
                result = self.start_logging()
                if result and self.config:
                    self.config.set('logging.enabled', True)
                return result
        else:
            if self.enabled:
                self.stop_logging()
                if self.config:
                    self.config.set('logging.enabled', False)
            return True
    
    def is_enabled(self):
        """Check if logging is currently enabled"""
        return self.enabled
    
    def get_log_folder(self):
        """Get the current log folder path"""
        return self.log_folder
    
    def get_log_path(self):
        """Get the full path to the log file"""
        if self.log_folder:
            return os.path.join(self.log_folder, 'audiblezenbot.log')
        return None
    
    def cleanup(self):
        """Clean up logging system on app exit"""
        self.stop_logging()
        
        # Restore original stdout/stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    # --- Debug settings API -------------------------------------------------
    def get_debug_schema(self):
        """Return the available debug settings as (key, label) tuples."""
        return list(self._debug_schema)

    def get_debug_value(self, key: str) -> bool:
        """Return whether `key` is enabled in the current debug map."""
        try:
            return bool(self.debug_map.get(key, False))
        except Exception:
            return False

    def set_debug_value(self, key: str, enabled: bool):
        """Set a debug flag at runtime and persist to config if available."""
        try:
            self.debug_map[key] = bool(enabled)
            if self.config:
                # Persist the debug map under 'debug'
                try:
                    self.config.set('debug', self.debug_map)
                except Exception:
                    pass
            return True
        except Exception:
            return False

    # --- Per-level schema API ------------------------------------------------
    def get_level_schema(self):
        """Return available logging levels as (key,label) tuples."""
        return list(self._level_keys)

    def get_level_value(self, key: str) -> bool:
        try:
            return bool(self.level_map.get(key, False))
        except Exception:
            return False

    def set_level_value(self, key: str, enabled: bool):
        try:
            self.level_map[key] = bool(enabled)
            if self.config:
                try:
                    self.config.set('logging.levels', self.level_map)
                except Exception:
                    pass
            return True
        except Exception:
            return False


# Global log manager instance
_log_manager = None


def get_log_manager(config=None):
    """Get the global log manager instance"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager(config)
    return _log_manager


# Simple logger facade used by modules. This is intentionally lightweight and
# writes formatted lines to stdout/stderr so the TeeOutput/LogManager can
# filter or capture them. Examples in code call `get_logger('ModuleName')`.
_loggers = {}


class SimpleLogger:
    def __init__(self, name: str):
        self.name = name

    def _format(self, level: str, msg: str) -> str:
        # Format: [Component][LEVEL] message
        return f"[{self.name}][{level}] {msg}\n"

    def debug(self, msg: str):
        try:
            sys.stdout.write(self._format('DEBUG', str(msg)))
        except Exception:
            pass

    def info(self, msg: str):
        try:
            sys.stdout.write(self._format('INFO', str(msg)))
        except Exception:
            pass

    def warning(self, msg: str):
        try:
            sys.stderr.write(self._format('WARN', str(msg)))
        except Exception:
            pass

    def error(self, msg: str):
        try:
            sys.stderr.write(self._format('ERROR', str(msg)))
        except Exception:
            pass

    def critical(self, msg: str):
        try:
            sys.stderr.write(self._format('CRITICAL', str(msg)))
        except Exception:
            pass

    def exception(self, msg: str):
        """Log an exception message and attempt to include a traceback."""
        try:
            # Write exception header to stderr
            sys.stderr.write(self._format('ERROR', str(msg)))
            try:
                import traceback
                tb = traceback.format_exc()
                if tb and not tb.strip().endswith('None'):
                    sys.stderr.write(tb)
            except Exception:
                pass
        except Exception:
            pass

    def trace(self, msg: str):
        try:
            sys.stdout.write(self._format('TRACE', str(msg)))
        except Exception:
            pass

    def diag(self, msg: str):
        try:
            sys.stdout.write(self._format('DIAG', str(msg)))
        except Exception:
            pass


def get_logger(name: str):
    """Return a SimpleLogger instance for `name`.

    The returned logger writes messages to stdout/stderr with a predictable
    prefix so `LogManager.should_emit` can apply per-component filtering.
    """
    global _loggers
    key = str(name)
    if key not in _loggers:
        _loggers[key] = SimpleLogger(key)
    return _loggers[key]
