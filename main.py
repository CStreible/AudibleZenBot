"""
AudibleZenBot - Multi-Platform Streaming Chat Bot
Main application entry point
"""

import sys
import traceback

# Global exception hook to log all unhandled exceptions
def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("\n[UNHANDLED EXCEPTION]", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    try:
        with open("unhandled_exception.log", "a", encoding="utf-8") as f:
            f.write("\n[UNHANDLED EXCEPTION]\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception as log_exc:
        print(f"[Exception Logging Failed] {log_exc}", file=sys.stderr)

sys.excepthook = log_unhandled_exception
import os
import sysconfig
# Ensure system site-packages is preferred so a local `PyQt6/` stub in the
# workspace doesn't shadow the installed PyQt6 package when running the GUI.
try:
    purelib = sysconfig.get_paths().get('purelib')
    if purelib and purelib not in sys.path:
        sys.path.insert(0, purelib)
except Exception:
    pass
# Prefer the installed PyQt6 package by temporarily removing the workspace
# root from `sys.path` so local test stubs (PyQt6/) do not shadow the real
# package when running the full application.
_orig_sys_path = list(sys.path)
_cwd = os.path.abspath(os.getcwd())
HAS_PYQT = True
try:
    try:
        for p in list(sys.path):
            try:
                if p and os.path.abspath(p) == _cwd:
                    sys.path.remove(p)
            except Exception:
                pass
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
            QPushButton, QStackedWidget, QLabel, QFrame, QScrollArea
        )
        from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
        from PyQt6.QtGui import QIcon, QFont
    finally:
        try:
            sys.path[:] = _orig_sys_path
        except Exception:
            pass
except Exception:
    HAS_PYQT = False
    # PyQt6 not available or import shadowed by workspace stubs; will run headless.

# Core imports needed for headless startup
from core.chat_manager import ChatManager
from core.config import ConfigManager
from core.ngrok_manager import NgrokManager
try:
    from core.overlay_server import OverlayServer
except Exception:
    # OverlayServer depends on optional packages (Flask). Provide a minimal
    # fallback so headless startup can proceed when Flask isn't installed.
    class OverlayServer:
        def __init__(self, port=5000):
            self.port = port
        def start(self):
            return None
from core.logger import get_log_manager
from urllib.parse import urlparse

"""GUI imports and MainWindow/SidebarButton are only defined when PyQt6 is present.
This prevents import-time failures in headless/test environments where a workspace
stub or missing PyQt6 could previously cause early ImportError before headless
initialization could run.
"""
try:
    import ctypes
    myappid = 'audiblezen.chatbot.multiplatform.1.0'  # Arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    # Not on Windows or ctypes not available
    pass

if HAS_PYQT:
    from ui.chat_page import ChatPage
    from ui.connections_page import ConnectionsPage
    from ui.settings_page import SettingsPage
    from ui.overlay_page import OverlayPage
    from ui.automation_page import AutomationPage
    from core.chat_manager import ChatManager
    from core.config import ConfigManager
    from core.ngrok_manager import NgrokManager
    from core.overlay_server import OverlayServer
    from core.logger import get_log_manager
    from urllib.parse import urlparse

    class SidebarButton(QPushButton):
        """Custom styled button for sidebar navigation"""
        def __init__(self, text, icon_text="", parent=None):
            super().__init__(text, parent)
            self.setCheckable(True)
            self.setMinimumHeight(50)
            self.icon_text = icon_text
            self.updateStyleSheet(False)

        def updateStyleSheet(self, is_expanded):
            if is_expanded:
                self.setText(f"{self.icon_text}  {self.text() if self.text() != self.icon_text else self.objectName()}")
            else:
                self.setText(self.icon_text)

            self.setStyleSheet("""
                QPushButton {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: none;
                    text-align: left;
                    padding: 10px;
                    font-size: 20px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
                QPushButton:checked {
                    background-color: #4a90e2;
                }
            """)

    class MainWindow(QMainWindow):
        """Main application window"""

        def get_resource_path(self, relative_path):
            """Get absolute path to resource, works for dev and for PyInstaller"""
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        def __init__(self):
            super().__init__()
            self.setWindowTitle("AudibleZenBot - Multi-Platform Chat Bot")
            # Initialize config manager early so we can restore window geometry before showing
            self.config = ConfigManager()

            # Try to restore saved window geometry from config; otherwise use ~50% screen size
            try:
                screen = QApplication.primaryScreen()
                geom = screen.availableGeometry() if screen else None
            except Exception:
                geom = None

            saved = self.config.get('ui.window', {}) or {}
            try:
                sx = saved.get('x')
                sy = saved.get('y')
                sw = saved.get('width')
                sh = saved.get('height')
            except Exception:
                sx = sy = sw = sh = None

            if sw and sh:
                w = int(sw)
                h = int(sh)
            elif geom:
                w = int(geom.width() * 0.5)
                h = int(geom.height() * 0.5)
            else:
                w = 1200
                h = 800

            if sx is not None and sy is not None:
                try:
                    self.setGeometry(int(sx), int(sy), w, h)
                except Exception:
                    # Fallback to center on primary screen
                    if geom:
                        x = geom.x() + (geom.width() - w) // 2
                        y = geom.y() + (geom.height() - h) // 2
                        self.setGeometry(x, y, w, h)
                    else:
                        self.setGeometry(100, 100, w, h)
            else:
                # Center default size on primary screen if possible
                if geom:
                    x = geom.x() + (geom.width() - w) // 2
                    y = geom.y() + (geom.height() - h) // 2
                    self.setGeometry(x, y, w, h)
                else:
                    self.setGeometry(100, 100, w, h)

            # Set window icon for taskbar
            icon_path = self.get_resource_path("resources/icons/app_icon.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))

            # config already initialized above

            # Initialize ngrok manager
            self.ngrok_manager = NgrokManager(self.config)

            # Initialize chat manager (pass ngrok_manager)
            self.chat_manager = ChatManager(self.config)
            self.chat_manager.ngrok_manager = self.ngrok_manager

            # Initialize overlay server
            self.overlay_server = OverlayServer(port=5000)

            # Initialize logging system
            self.log_manager = get_log_manager(self.config)
            print("[Main] Log manager initialized")
            # Prefetch Twitch global emotes in background to warm caches
            try:
                from core.twitch_emotes import get_manager as get_twitch_manager
                try:
                    get_twitch_manager().prefetch_global(background=True)
                except Exception:
                    pass
            except Exception:
                pass
            # Ensure Trovo callback server and ngrok tunnel are started if needed
            try:
                self._start_trovo_support_servers()
            except Exception as e:
                print(f"[Main] Failed to start trovo support servers: {e}")

            # Setup UI
            self.initUI()

            # Restore previous connections
            self.restoreSavedConnections()

            # Apply dark theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                }
                QLabel {
                    color: #ffffff;
                }
            """)


def main():
    """Main application entry point"""
    if not HAS_PYQT:
        print('[Main] PyQt6 not available; running in headless mode')
        headless_main()
        return

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support
    # Ensure Twitch emote manager shutdown is invoked on application quit
    try:
        from core.twitch_emotes import get_manager as get_twitch_manager
        try:
            app.aboutToQuit.connect(lambda: get_twitch_manager().shutdown())
        except Exception:
            pass
    except Exception:
        pass
    
    # Set application icon
    icon_path = "resources/icons/app_icon.ico"
    if hasattr(sys, '_MEIPASS'):
        icon_path = os.path.join(sys._MEIPASS, icon_path)
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    print("[DEBUG] About to call window.show()")
    window.show()
    print("[DEBUG] window.show() called, entering app.exec()")
    sys.exit(app.exec())


# Defer running main() until after `headless_main` is defined at module bottom.


def headless_main():
    """Run startup logic without GUI for environments without PyQt6.

    Initializes core components, prefetches emotes, and attempts to restore
    saved platform connections so we can catch startup/connect issues in CI
    or headless environments.
    """
    try:
        print('[Headless] Initializing config, ngrok, chat_manager, overlay_server')
        config = ConfigManager()
        ngrok_manager = NgrokManager(config)
        chat_manager = ChatManager(config)
        chat_manager.ngrok_manager = ngrok_manager
        overlay_server = OverlayServer(port=5000)
        log_manager = get_log_manager(config)

        # Prefetch Twitch global emotes if available
        try:
            from core.twitch_emotes import get_manager as get_twitch_manager
            try:
                get_twitch_manager().prefetch_global(background=False)
            except Exception:
                pass
        except Exception:
            pass

        # Restore saved connections (adapted from MainWindow.restoreSavedConnections)
        print('[Headless] Restoring saved connections')
        platforms_config = config.get('platforms', {})
        for platform_id, platform_data in (platforms_config.items() if platforms_config else []):
            if platform_data.get('disabled', False):
                print(f"[Headless] Skipping disabled platform: {platform_id}")
                continue

            # Streamer connections (skip twitch/youtube streamer auto-connect as UI does)
            if platform_id not in ['twitch', 'youtube']:
                is_streamer_logged_in = platform_data.get('streamer_logged_in', False)
                is_streamer_connected = platform_data.get('streamer_connected', False)
                if is_streamer_logged_in or is_streamer_connected:
                    username = platform_data.get('streamer_username', '')
                    token = platform_data.get('streamer_token', '')
                    if username and token:
                        print(f"[Headless] Auto-connecting streamer to {platform_id}: {username}")
                        try:
                            ok = chat_manager.connectPlatform(platform_id, username, token)
                            print(f"[Headless] connectPlatform returned: {ok}")
                        except Exception as e:
                            print(f"[Headless] Error connecting streamer to {platform_id}: {e}")

            # Bot connections
            bot_logged_in = platform_data.get('bot_logged_in', False)
            bot_connected = platform_data.get('bot_connected', False)
            if bot_logged_in or bot_connected:
                bot_username = platform_data.get('bot_username', '')
                bot_token = platform_data.get('bot_token', '') or platform_data.get('bot_access_token', '')
                bot_refresh_token = platform_data.get('bot_refresh_token', '')
                if bot_username and bot_token:
                    print(f"[Headless] Auto-connecting bot to {platform_id}: {bot_username}")
                    try:
                        ok = chat_manager.connectBotAccount(platform_id, bot_username, bot_token, bot_refresh_token)
                        print(f"[Headless] connectBotAccount returned: {ok}")
                    except Exception as e:
                        print(f"[Headless] Error connecting bot to {platform_id}: {e}")

        print('[Headless] Initialization complete')
    except Exception as e:
        print(f"[Headless] Startup failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
