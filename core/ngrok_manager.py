"""
NgrokManager - Automatic Ngrok Tunnel Management
Handles starting, stopping, and monitoring ngrok tunnels for webhook-based platforms.
"""

import os
import sys
import time
import requests
import subprocess
from threading import Thread, Lock
from typing import Dict, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal
from core.logger import get_logger

logger = get_logger(__name__)

# Monkey-patch subprocess.Popen early to hide console windows on Windows
if sys.platform == 'win32' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
    _original_popen = subprocess.Popen
    
    class _HiddenPopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            if 'creationflags' not in kwargs:
                kwargs['creationflags'] = 0
            kwargs['creationflags'] |= subprocess.CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    
    subprocess.Popen = _HiddenPopen


class NgrokManager(QObject):
    """
    Manages ngrok tunnels for platforms that require public URLs (webhooks/callbacks).
    Automatically starts/stops tunnels and monitors their health.
    """
    
    # Signals for UI updates
    tunnel_started = pyqtSignal(int, str)  # port, public_url
    tunnel_stopped = pyqtSignal(int)  # port
    tunnel_error = pyqtSignal(int, str)  # port, error_message
    status_changed = pyqtSignal(str)  # status_message
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        # Optionally kill lingering ngrok processes from previous crashes
        try:
            if self.config and isinstance(self.config.get('ngrok', {}), dict):
                if self.config.get('ngrok', {}).get('kill_existing_on_startup', False):
                    try:
                        self.kill_existing_processes()
                    except Exception:
                        logger.exception("Error attempting to kill existing ngrok processes")
        except Exception:
            pass
        self.tunnels: Dict[int, Dict[str, Any]] = {}  # port -> tunnel_info
        self.ngrok_process = None
        self.lock = Lock()
        self.monitoring = False
        self.monitor_thread = None
        self.pyngrok_available = False
        self.auth_token = None
        
        # Try to import pyngrok
        try:
            global ngrok, conf
            from pyngrok import ngrok, conf
            self.pyngrok_available = True
            
            # Configure pyngrok to hide console window on Windows
            if sys.platform == 'win32':
                import subprocess
                pyngrok_config = conf.get_default()
                # Set startup flags to log to stdout instead of file
                pyngrok_config.log_event_callback = None
                # Configure subprocess creation to hide window
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    pyngrok_config.startup_flags = ['--log=stdout']
                    # Store the config for use when starting tunnels
                    conf.set_default(pyngrok_config)
            
            logger.info("pyngrok library available")
        except ImportError:
            logger.warning("pyngrok not installed. Install with: pip install pyngrok")
            self.pyngrok_available = False
        
        # Load auth token from config
        if self.config:
            ngrok_config = self.config.get('ngrok', {})
            self.auth_token = ngrok_config.get('auth_token', '')
            if self.auth_token and self.pyngrok_available:
                self.set_auth_token(self.auth_token)
    
    def set_auth_token(self, token: str):
        """Set ngrok auth token"""
        if not self.pyngrok_available:
            logger.error("Cannot set auth token: pyngrok not available")
            return False
        
        try:
            self.auth_token = token
            ngrok.set_auth_token(token)
            
            # Save to config using the correct method
            if self.config:
                self.config.set('ngrok.auth_token', token)
            
            logger.info("Ngrok auth token configured")
            self.status_changed.emit("Ngrok auth token configured")
            return True
        except Exception as e:
            logger.exception(f"Failed to set auth token: {e}")
            self.status_changed.emit(f"Failed to set auth token: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if ngrok is available and ready to use"""
        if not self.pyngrok_available:
            return False
        if not self.auth_token:
            return False
        return True
    
    def start_tunnel(self, port: int, protocol: str = 'http', name: str = None) -> Optional[str]:
        """
        Start an ngrok tunnel for the specified port.
        
        Args:
            port: Local port to expose
            protocol: Protocol (http, tcp, etc.)
            name: Optional name for the tunnel
            
        Returns:
            Public URL if successful, None otherwise
        """
        # Check if tunnel already exists (without blocking)
        if port in self.tunnels:
            logger.info(f"Tunnel for port {port} already active")
            return self.tunnels[port]['public_url']
        
        # Check availability
        if not self.is_available():
            error_msg = "Ngrok not available. Please configure auth token in Settings."
            logger.error(error_msg)
            self.tunnel_error.emit(port, error_msg)
            return None
        
        # Start tunnel in background thread to avoid blocking UI
        result_holder = {'url': None, 'done': False, 'error': None}
        
        def start_tunnel_thread():
            try:
                logger.info(f"Starting ngrok tunnel for port {port}...")
                self.status_changed.emit(f"Starting tunnel for port {port}...")
                
                # Configure pyngrok to hide console window on Windows
                if sys.platform == 'win32':
                    import subprocess
                    pyngrok_config = conf.get_default()
                    
                    # Set pyngrok config to prevent console window
                    pyngrok_config.startup_timeout = 30
                    
                    # Monkey-patch subprocess.Popen BEFORE pyngrok uses it
                    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                        original_popen = subprocess.Popen
                        def hidden_popen(*args, **kwargs):
                            if 'creationflags' not in kwargs:
                                kwargs['creationflags'] = 0
                            kwargs['creationflags'] |= subprocess.CREATE_NO_WINDOW
                            return original_popen(*args, **kwargs)
                        subprocess.Popen = hidden_popen
                
                # Start tunnel using pyngrok
                tunnel = ngrok.connect(port, protocol)
                public_url = tunnel.public_url
                
                # Restore original Popen if we patched it
                if sys.platform == 'win32' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    subprocess.Popen = original_popen
                
                with self.lock:
                    # Store tunnel info
                    self.tunnels[port] = {
                        'port': port,
                        'protocol': protocol,
                        'public_url': public_url,
                        'tunnel_obj': tunnel,
                        'name': name or f"port_{port}",
                        'started_at': time.time()
                    }
                
                logger.info(f"Ngrok tunnel started: {public_url} -> localhost:{port}")
                self.status_changed.emit(f"Tunnel active: {public_url}")
                self.tunnel_started.emit(port, public_url)
                
                # Start monitoring if not already running
                if not self.monitoring:
                    self.start_monitoring()
                
                result_holder['url'] = public_url
                result_holder['done'] = True
                
            except Exception as e:
                error_msg = f"Failed to start tunnel: {str(e)}"
                
                # Check if this is the "endpoint already online" error
                if "endpoint" in error_msg.lower() and "already online" in error_msg.lower():
                    # Try to extract the URL from the error message
                    import re
                    url_match = re.search(r'https://[a-z0-9\-]+\.ngrok[a-z\-\.]+', error_msg)
                    if url_match:
                        existing_url = url_match.group(0)
                        logger.info(f"Endpoint already exists: {existing_url}")
                        logger.info(f"Using existing ngrok tunnel: {existing_url} -> localhost:{port}")
                        
                        # Store tunnel info with existing URL
                        with self.lock:
                            self.tunnels[port] = {
                                'port': port,
                                'protocol': protocol,
                                'public_url': existing_url,
                                'tunnel_obj': None,
                                'name': name or f"port_{port}",
                                'started_at': time.time(),
                                'reused': True
                            }
                        
                        self.status_changed.emit(f"Using existing tunnel: {existing_url}")
                        self.tunnel_started.emit(port, existing_url)
                        
                        result_holder['url'] = existing_url
                        result_holder['done'] = True
                        return
                
                logger.error(error_msg)
                self.tunnel_error.emit(port, error_msg)
                self.status_changed.emit(error_msg)
                result_holder['error'] = error_msg
                result_holder['done'] = True
        
        # Start thread
        thread = Thread(target=start_tunnel_thread, daemon=True)
        thread.start()
        
        # Wait for completion (with timeout)
        timeout = 15  # 15 second timeout
        start_time = time.time()
        while not result_holder['done'] and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if not result_holder['done']:
            error_msg = "Tunnel start timeout"
            logger.error(error_msg)
            self.tunnel_error.emit(port, error_msg)
            return None
        
        return result_holder['url']
    
    def stop_tunnel(self, port: int):
        """Stop a specific tunnel"""
        with self.lock:
            if port not in self.tunnels:
                logger.info(f"No tunnel found for port {port}")
                return

            try:
                tunnel_info = self.tunnels[port]
                logger.info(f"Stopping ngrok tunnel for port {port}...")

                # Disconnect tunnel
                if self.pyngrok_available:
                    ngrok.disconnect(tunnel_info['public_url'])

                # Remove from tracking
                del self.tunnels[port]

                logger.info(f"Tunnel stopped for port {port}")
                self.status_changed.emit(f"Tunnel stopped for port {port}")
                self.tunnel_stopped.emit(port)

                # Stop monitoring if no tunnels left
                if not self.tunnels and self.monitoring:
                    self.stop_monitoring()

            except Exception as e:
                logger.exception(f"Error stopping tunnel: {e}")
    
    def stop_all_tunnels(self):
        """Stop all active tunnels"""
        logger.info("Stopping all ngrok tunnels...")
        
        # Get list of ports to avoid dict change during iteration
        ports = list(self.tunnels.keys())
        
        for port in ports:
            self.stop_tunnel(port)
        
        # Kill ngrok process completely
        if self.pyngrok_available:
            try:
                ngrok.kill()
                logger.info("Ngrok process terminated")
            except Exception as e:
                logger.warning(f"Error killing ngrok: {e}")
        
        self.tunnels.clear()
        self.status_changed.emit("All tunnels stopped")

    def kill_existing_processes(self):
        """Terminate lingering ngrok processes on the host.

        This prefers `psutil` if available; otherwise falls back to platform
        specific commands (`taskkill` on Windows, `pkill` on POSIX).
        """
        logger.info("Attempting to terminate lingering ngrok processes...")
        try:
            try:
                import psutil
                killed = 0
                targets = []
                for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        name = (p.info.get('name') or '').lower()
                        cmd = ' '.join(p.info.get('cmdline') or []).lower()
                        if 'ngrok' in name or 'ngrok' in cmd:
                            targets.append(p)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                if not targets:
                    logger.info("No lingering ngrok processes found via psutil")
                    return

                logger.info(f"Found {len(targets)} ngrok processes, attempting graceful terminate")
                # Try polite termination first
                for p in targets:
                    try:
                        logger.info(f"Terminating ngrok process PID={p.pid} CMD={' '.join(p.info.get('cmdline') or [])}")
                        p.terminate()
                        killed += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.debug(f"Could not terminate process PID={getattr(p, 'pid', 'unknown')}: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to terminate ngrok PID={getattr(p, 'pid', 'unknown')}: {e}")

                # Wait for processes to exit using psutil.wait_procs
                try:
                    gone, alive = psutil.wait_procs(targets, timeout=8)
                    if alive:
                        logger.info(f"Some ngrok processes still alive after terminate, forcing kill ({len(alive)})")
                        for p in alive:
                            try:
                                p.kill()
                            except Exception as e:
                                logger.warning(f"Failed to kill ngrok PID={getattr(p, 'pid', 'unknown')}: {e}")
                        # wait a short time for killed processes
                        psutil.wait_procs(alive, timeout=5)
                except Exception as e:
                    logger.debug(f"psutil.wait_procs failed: {e}")

                logger.info(f"Ngrok cleanup complete (psutil), attempted terminations: {killed}")
                return
            except ImportError:
                logger.debug("psutil not available; falling back to platform commands for ngrok cleanup. Install psutil for more reliable cleanup: pip install psutil")

            import subprocess, sys
            try:
                if sys.platform == 'win32':
                    # Force kill ngrok.exe instances
                    subprocess.call(['taskkill', '/f', '/im', 'ngrok.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    # pkill will target processes with 'ngrok' in their name/command
                    subprocess.call(['pkill', '-f', 'ngrok'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # Wait for processes to disappear (poll)
                timeout = 10.0
                start = time.time()
                while time.time() - start < timeout:
                    # Check via platform process listing
                    try:
                        if sys.platform == 'win32':
                            out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ngrok.exe'], capture_output=True, text=True)
                            if 'ngrok.exe' not in out.stdout:
                                break
                        else:
                            out = subprocess.run(['pgrep', '-f', 'ngrok'], capture_output=True, text=True)
                            if not out.stdout.strip():
                                break
                    except Exception:
                        # If listing commands fail, just break to avoid infinite loop
                        break
                    time.sleep(0.5)

                logger.info("Ngrok cleanup (fallback) executed")
            except Exception:
                logger.debug("Fallback ngrok kill attempted")
        except Exception as e:
            logger.exception(f"Error during ngrok cleanup: {e}")
    
    def get_tunnel_url(self, port: int) -> Optional[str]:
        """Get the public URL for a specific port (non-blocking)"""
        if not self.lock.acquire(timeout=0.1):
            return None
        
        try:
            if port in self.tunnels:
                return self.tunnels[port]['public_url']
            return None
        finally:
            self.lock.release()
    
    def get_all_tunnels(self) -> Dict[int, Dict[str, Any]]:
        """Get information about all active tunnels (non-blocking)"""
        if not self.lock.acquire(timeout=0.1):
            return {}
        
        try:
            return dict(self.tunnels)
        finally:
            self.lock.release()
    
    def is_tunnel_active(self, port: int) -> bool:
        """Check if a tunnel is active for the specified port (non-blocking)"""
        if not self.lock.acquire(timeout=0.1):
            return False
        
        try:
            return port in self.tunnels
        finally:
            self.lock.release()
    
    def start_monitoring(self):
        """Start monitoring tunnel health"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = Thread(target=self._monitor_tunnels, daemon=True)
        self.monitor_thread.start()
        logger.info("Tunnel monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring tunnel health"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
            self.monitor_thread = None
        logger.info("Tunnel monitoring stopped")
    
    def _monitor_tunnels(self):
        """Monitor tunnel health (runs in background thread)"""
        while self.monitoring:
            try:
                time.sleep(30)  # Check every 30 seconds
                
                # Check ngrok API for tunnel status
                with self.lock:
                    if not self.tunnels:
                        continue
                    
                    try:
                        # Query ngrok API
                        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
                        if response.status_code == 200:
                            api_tunnels = response.json().get('tunnels', [])
                            active_urls = {t['public_url'] for t in api_tunnels}
                            
                            # Check if our tunnels are still active
                            for port, info in list(self.tunnels.items()):
                                if info['public_url'] not in active_urls:
                                    logger.warning(f"Tunnel for port {port} is no longer active")
                                    self.tunnel_error.emit(port, "Tunnel disconnected")
                                    
                    except requests.exceptions.RequestException:
                        # Ngrok API not available - tunnels might be down
                        pass
                        
            except Exception as e:
                logger.exception(f"Monitor error: {e}")
    
    def get_status_summary(self) -> str:
        """Get a summary of tunnel status (non-blocking)"""
        # Try to acquire lock with timeout to avoid UI freezing
        if not self.lock.acquire(timeout=0.1):
            return "Updating..."
        
        try:
            if not self.is_available():
                return "Ngrok not configured"
            
            if not self.tunnels:
                return "Ngrok ready (no active tunnels)"
            
            count = len(self.tunnels)
            return f"{count} tunnel{'s' if count > 1 else ''} active"
        finally:
            self.lock.release()
    
    def cleanup(self):
        """Cleanup resources on shutdown"""
        logger.info("Cleaning up NgrokManager...")
        self.stop_monitoring()
        self.stop_all_tunnels()
        logger.info("NgrokManager cleanup complete")


# Platform requirements - which platforms need ngrok tunnels
PLATFORM_TUNNEL_REQUIREMENTS = {
    'kick': {
        'port': 8889,
        'needs_tunnel': True,
        'protocol': 'http',
        'purpose': 'webhook',
        'description': 'Kick requires webhooks for real-time chat'
    },
    'trovo': {
        'port': 5000,
        'needs_tunnel': False,  # Trovo uses WebSocket, no ngrok needed
        'protocol': 'http',
        'purpose': 'callback',
        'description': 'Trovo OAuth callback (optional)'
    },
    'youtube_oauth': {
        'port': 8080,
        'needs_tunnel': False,  # Local OAuth callback only
        'protocol': 'http',
        'purpose': 'oauth',
        'description': 'YouTube OAuth callback (local only)'
    }
}


def get_platform_tunnel_requirement(platform: str) -> Optional[Dict[str, Any]]:
    """Get tunnel requirements for a platform"""
    return PLATFORM_TUNNEL_REQUIREMENTS.get(platform.lower())
