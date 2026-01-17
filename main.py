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
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont

# Windows taskbar icon support
try:
    import ctypes
    myappid = 'audiblezen.chatbot.multiplatform.1.0'  # Arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass  # Not on Windows or ctypes not available

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
        self.setGeometry(100, 100, 1200, 800)
        
        # Set window icon for taskbar
        icon_path = self.get_resource_path("resources/icons/app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Initialize config manager
        self.config = ConfigManager()
        
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
    
    def initUI(self):
        """Initialize the user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        self.sidebar.setStyleSheet("QFrame { background-color: #252525; }")
        self.sidebar.setMinimumWidth(60)
        self.sidebar.setMaximumWidth(60)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Sidebar toggle button
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setMinimumHeight(50)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: #ffffff;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggleSidebar)
        sidebar_layout.addWidget(self.toggle_btn)
        
        # Navigation buttons
        self.chat_btn = SidebarButton("Chat", "💬")
        self.chat_btn.setObjectName("Chat")
        self.chat_btn.clicked.connect(lambda: self.changePage(0))
        sidebar_layout.addWidget(self.chat_btn)
        
        self.connections_btn = SidebarButton("Connections", "🌐")
        self.connections_btn.setObjectName("Connections")
        self.connections_btn.clicked.connect(lambda: self.changePage(1))
        sidebar_layout.addWidget(self.connections_btn)
        
        self.settings_btn = SidebarButton("Settings", "⚙️")
        self.settings_btn.setObjectName("Settings")
        self.settings_btn.clicked.connect(lambda: self.changePage(2))
        sidebar_layout.addWidget(self.settings_btn)
        
        self.overlay_btn = SidebarButton("Overlay", "💻")
        self.overlay_btn.setObjectName("Overlay")
        self.overlay_btn.clicked.connect(lambda: self.changePage(3))
        sidebar_layout.addWidget(self.overlay_btn)
        
        self.automation_btn = SidebarButton("Automation", "🤖")
        self.automation_btn.setObjectName("Automation")
        self.automation_btn.clicked.connect(lambda: self.changePage(4))
        sidebar_layout.addWidget(self.automation_btn)
        
        sidebar_layout.addStretch()
        
        # Content area with stacked widget for pages
        self.content_stack = QStackedWidget()
        
        # Create pages
        self.chat_page = ChatPage(self.chat_manager, self.config)
        self.chat_page.overlay_server = self.overlay_server  # Pass overlay server to chat page
        self.connections_page = ConnectionsPage(self.chat_manager, self.config)
        self.connections_page.ngrok_manager = self.ngrok_manager  # Pass ngrok manager to connections page
        self.settings_page = SettingsPage(self.ngrok_manager, self.config, self.log_manager)
        self.overlay_page = OverlayPage(self.overlay_server, self.config)
        self.automation_page = AutomationPage(self.chat_manager, self.config)
        
        # Connect settings signals to chat page
        self.settings_page.colors_updated.connect(self.on_username_colors_updated)
        
        # Add pages to stack
        self.content_stack.addWidget(self.chat_page)
        self.content_stack.addWidget(self.connections_page)
        self.content_stack.addWidget(self.settings_page)
        self.content_stack.addWidget(self.overlay_page)
        self.content_stack.addWidget(self.automation_page)
        
        # Add widgets to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_stack)
        
        # Set initial page
        self.chat_btn.setChecked(True)
        self.content_stack.setCurrentIndex(0)
        
        # Track sidebar state
        self.sidebar_expanded = False
    
    def toggleSidebar(self):
        """Toggle sidebar expansion"""
        if self.sidebar_expanded:
            # Collapse
            self.sidebar.setMaximumWidth(60)
            self.sidebar.setMinimumWidth(60)
            self.sidebar_expanded = False
        else:
            # Expand
            self.sidebar.setMaximumWidth(200)
            self.sidebar.setMinimumWidth(200)
            self.sidebar_expanded = True
        
        # Update button text
        self.chat_btn.updateStyleSheet(self.sidebar_expanded)
        self.connections_btn.updateStyleSheet(self.sidebar_expanded)
        self.settings_btn.updateStyleSheet(self.sidebar_expanded)
        self.overlay_btn.updateStyleSheet(self.sidebar_expanded)
        self.automation_btn.updateStyleSheet(self.sidebar_expanded)
    
    def changePage(self, index):
        """Change the current page"""
        self.content_stack.setCurrentIndex(index)
        
        # Update button states
        self.chat_btn.setChecked(index == 0)
        self.connections_btn.setChecked(index == 1)
        self.settings_btn.setChecked(index == 2)
        self.overlay_btn.setChecked(index == 3)
        self.automation_btn.setChecked(index == 4)
    
    def on_username_colors_updated(self, colors):
        """Handle username colors being updated from settings page"""
        from ui.chat_page import set_username_colors
        set_username_colors(colors)
        print(f"[MainWindow] Username colors updated: {len(colors)} colors")
    
    def restoreSavedConnections(self):
        """Restore connections from last session, skipping disabled platforms"""
        platforms_config = self.config.get('platforms', {})

        for platform_id, platform_data in platforms_config.items():
            # Skip disabled platforms
            if platform_data.get('disabled', False):
                print(f"[Main] Skipping auto-connect for disabled platform: {platform_id}")
                continue

            # Restore streamer connection for platforms that support it
            # Twitch and YouTube only work with bot accounts, so skip them here
            if platform_id not in ['twitch', 'youtube']:
                is_streamer_logged_in = platform_data.get('streamer_logged_in', False)
                is_streamer_connected = platform_data.get('streamer_connected', False)

                if is_streamer_logged_in or is_streamer_connected:
                    username = platform_data.get('streamer_username', '')
                    token = platform_data.get('streamer_token', '')

                    if username and token:
                        print(f"Auto-connecting streamer to {platform_id}: {username}")
                        try:
                            success = self.chat_manager.connectPlatform(platform_id, username, token)
                            if success:
                                print(f"[OK] Streamer connected to {platform_id}")
                            else:
                                print(f"[WARN] Failed to connect streamer to {platform_id}")
                        except Exception as e:
                            print(f"✗ Error connecting streamer to {platform_id}: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"[Main] Streamer credentials missing for {platform_id}")
                        if is_streamer_logged_in or is_streamer_connected:
                            print(f"[Main] Clearing stale streamer connection state for {platform_id}")
                            # Use ConfigManager to update platform flags atomically
                            self.config.set_platform_config(platform_id, 'streamer_connected', False)
                            self.config.set_platform_config(platform_id, 'streamer_logged_in', False)

            # Restore bot connection if saved (for all platforms)
            bot_logged_in = platform_data.get('bot_logged_in', False)
            bot_connected = platform_data.get('bot_connected', False)
            if bot_logged_in or bot_connected:
                bot_username = platform_data.get('bot_username', '')
                bot_token = platform_data.get('bot_token', '') or platform_data.get('bot_access_token', '')
                bot_refresh_token = platform_data.get('bot_refresh_token', '')

                if bot_username and bot_token:
                    print(f"Auto-connecting bot to {platform_id}: {bot_username}")
                    success = self.chat_manager.connectBotAccount(platform_id, bot_username, bot_token, bot_refresh_token)
                    if success:
                        print(f"[OK] Bot connected to {platform_id}")
                    else:
                        print(f"[WARN] Failed to connect bot to {platform_id}")

                else:
                    if bot_connected or bot_logged_in:
                        print(f"[Main] Clearing stale bot connection state for {platform_id}")
                        self.config.set_platform_config(platform_id, 'bot_connected', False)
                        self.config.set_platform_config(platform_id, 'bot_logged_in', False)
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Save connection states before closing
        self.connections_page.saveAllConnectionStates()
        
        # Cleanup ngrok tunnels
        if hasattr(self, 'ngrok_manager') and self.ngrok_manager:
            print("\n🛑 Shutting down ngrok tunnels...")
            self.ngrok_manager.cleanup()

        # Trovo callback server thread is daemon; no explicit stop required.
        
        # Cleanup logging system
        if hasattr(self, 'log_manager') and self.log_manager:
            print("\n📝 Closing log file...")
            self.log_manager.cleanup()
        
        event.accept()

    def _start_trovo_support_servers(self):
        """Start local Trovo callback Flask server and ngrok tunnel when configured.

        If the configured Trovo redirect URI is non-local (e.g., an ngrok domain), ensure
        a local callback server is running on port 8889 and start an ngrok tunnel to it
        so Trovo can redirect the authorization response.
        """
        try:
            trovo_cfg = self.config.get_platform_config('trovo') if self.config else {}
            # Allow override via attribute if present (connections page may set this)
            configured_redirect = trovo_cfg.get('redirect_uri') or getattr(self, '_trovo_redirect_uri', None)
            print(f"[Main][TrovoStartup] Resolved trovo redirect_uri: {configured_redirect!r}")
            if not configured_redirect:
                print("[Main][TrovoStartup] No Trovo redirect configured; skipping callback/ngrok startup")
                # Nothing configured; skip automatic server start
                return

            parsed = urlparse(configured_redirect)
            hostname = parsed.hostname or ''
            if hostname and 'localhost' in hostname:
                print("[Main][TrovoStartup] Redirect uses localhost; will start local callback only (no ngrok)")
            else:
                print("[Main][TrovoStartup] Redirect uses non-local host; will start local callback and attempt ngrok tunnel")

            # If redirect is not localhost, start local Flask callback and ngrok tunnel
            if hostname and 'localhost' not in hostname:
                try:
                    import threading
                    from platform_connectors import trovo_callback_server

                    def run_callback():
                        try:
                            # Bind to all interfaces so ngrok can forward
                            trovo_callback_server.app.run(host='0.0.0.0', port=8889, debug=False, use_reloader=False)
                        except Exception as e:
                            print(f"[Trovo Callback] Server error: {e}")

                    t = threading.Thread(target=run_callback, daemon=True)
                    t.start()
                    self.trovo_callback_thread = t
                    print("[Main] Trovo callback server started on port 8889 (daemon thread)")
                except Exception as e:
                    print(f"[Main] Failed to start Trovo callback server: {e}")

                # Start ngrok tunnel if available
                try:
                    if hasattr(self, 'ngrok_manager') and self.ngrok_manager and self.ngrok_manager.is_available():
                        public = self.ngrok_manager.start_tunnel(8889, protocol='http', name='trovo_callback')
                        if public:
                            print(f"[Main] Ngrok tunnel for Trovo callback: {public}")
                            # Surface public URL to Connections UI if available
                            try:
                                if hasattr(self, 'connections_page') and self.connections_page:
                                    if hasattr(self.connections_page, 'set_trovo_callback_url'):
                                        self.connections_page.set_trovo_callback_url(public)
                                    elif 'trovo' in getattr(self.connections_page, 'platform_widgets', {}):
                                        self.connections_page.platform_widgets['trovo'].set_trovo_callback_url(public)
                            except Exception as e:
                                print(f"[Main] Failed to update ConnectionsPage with trovo ngrok URL: {e}")
                        else:
                            print("[Main] Ngrok manager returned no public URL for port 8889")
                except Exception as e:
                    print(f"[Main] Failed to start ngrok tunnel for Trovo callback: {e}")

        except Exception as e:
            print(f"[Main] Error while setting up Trovo support servers: {e}")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support
    
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


if __name__ == "__main__":
    main()
