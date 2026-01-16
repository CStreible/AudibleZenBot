"""
Connections Page - Manage platform connections and authentication
"""

from logging import config
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox,
    QTextEdit, QFrame, QDialog, QProgressBar, QListWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from urllib.parse import urlparse, parse_qs
import secrets
import json
from core.config import ConfigManager
from core.oauth_handler import OAuthHandler, SimpleAuthDialog
import threading
from core.qt_utils import get_main_thread_executor


class OAuthBrowserDialog(QDialog):
    """Embedded browser dialog for OAuth authentication - Mixitup style"""
    
    auth_completed = pyqtSignal(str)  # authorization code
    auth_failed = pyqtSignal(str)  # error message
    
    def __init__(self, oauth_url, redirect_uri, platform_name, username=None, parent=None):
        super().__init__(parent)
        self.redirect_uri = redirect_uri
        self.platform_name = platform_name
        self.username = username
        self.authorization_code = None
        
        self.setWindowTitle(f"{platform_name} Authentication")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status label
        self.status_label = QLabel(f"Authorizing {platform_name}... Please log in and authorize the application.")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 10px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #1e1e1e;
                height: 3px;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
            }
        """)
        layout.addWidget(self.progress)
        
        # Embedded browser
        self.browser = QWebEngineView()
        self.browser.urlChanged.connect(self.onUrlChanged)
        self.browser.loadProgress.connect(self.onLoadProgress)
        self.browser.loadFinished.connect(self.onLoadFinished)
        layout.addWidget(self.browser)
        
        # Load OAuth URL
        self.browser.load(QUrl(oauth_url))
    
    def onUrlChanged(self, url):
        """Monitor URL changes to capture OAuth redirect"""
        url_str = url.toString()
        print(f"[DEBUG] onUrlChanged called, url={url_str}")
        # Check if this is the redirect URI with authorization code
        if url_str.startswith(self.redirect_uri):
            parsed = urlparse(url_str)
            params = parse_qs(parsed.query)
            if 'code' in params:
                # Success! Extract authorization code
                self.authorization_code = params['code'][0]
                print(f"[DEBUG] Authorization code detected: {self.authorization_code}")
                self.status_label.setText(f"✓ Authorization successful! Obtaining access token...")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #4caf50;
                        color: #ffffff;
                        padding: 10px;
                        font-size: 12px;
                    }
                """)
                self.progress.setRange(0, 1)
                self.progress.setValue(1)
                print(f"[DEBUG] Emitting auth_completed signal")
                self.auth_completed.emit(self.authorization_code)
                # Clear browser session to prevent auto-login for next account
                self.clearBrowserSession()
                # Close dialog after brief delay
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, self.accept)
            elif 'error' in params:
                # OAuth error
                error = params.get('error_description', [params['error'][0]])[0]
                print(f"[DEBUG] OAuth error detected: {error}")
                self.status_label.setText(f"✗ Authorization failed: {error}")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #ff6b6b;
                        color: #ffffff;
                        padding: 10px;
                        font-size: 12px;
                    }
                """)
                self.auth_failed.emit(error)
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, self.reject)
    
    def onLoadProgress(self, progress):
        """Update progress during page load"""
        if progress < 100:
            self.status_label.setText(f"Loading {self.platform_name} authorization page... {progress}%")
    
    def onLoadFinished(self, success):
        """Handle page load completion"""
        if success:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.status_label.setText(f"Please log in and authorize AudibleZenBot to access your {self.platform_name} account.")
            
            # Auto-fill username if provided - delay to ensure DOM is ready
            if self.username:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1000, self.autoFillUsername)
        else:
            self.status_label.setText(f"Failed to load {self.platform_name} authorization page. Check your internet connection.")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #ff6b6b;
                    color: #ffffff;
                    padding: 10px;
                    font-size: 12px;
                }
            """)
    
    def autoFillUsername(self):
        """Auto-fill username field on the login page"""
        import json
        
        # Escape username properly using JSON encoding
        username_escaped = json.dumps(self.username)
        
        # Platform-specific selectors for username fields
        js_code = f"""
        (function() {{
            var username = {username_escaped};
            var filled = false;
            
            // Try common username field selectors
            var selectors = [
                'input[name="username"]',
                'input[name="login"]',
                'input[name="email"]',
                'input[type="email"]',
                'input[type="text"]',
                'input[id*="username"]',
                'input[id*="login"]',
                'input[id*="email"]',
                'input[placeholder*="username"]',
                'input[placeholder*="Username"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]',
                'input[autocomplete="username"]',
                'input[autocomplete="email"]'
            ];
            
            for (var i = 0; i < selectors.length; i++) {{
                var field = document.querySelector(selectors[i]);
                if (field && field.offsetParent !== null) {{
                    field.value = username;
                    field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    field.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    field.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
                    filled = true;
                    console.log('Auto-filled username field: ' + selectors[i]);
                    break;
                }}
            }}
            
            if (!filled) {{
                console.log('No username field found to auto-fill');
            }}
            
            return filled;
        }})();
        """
        
        def callback(result):
            if result:
                print(f"[OAuth Browser] Username auto-filled successfully")
            else:
                print(f"[OAuth Browser] Could not auto-fill username - field not found on page")
        
        if hasattr(self, 'browser') and self.browser is not None:
            page = self.browser.page() if hasattr(self.browser, 'page') else None
            if page is not None:
                page.runJavaScript(js_code, callback)
    
    def clearBrowserSession(self):
        """Clear browser cookies and session to prevent auto-login"""
        # QWebEngineView uses QWebEngineProfile for cookies and cache
        page = self.browser.page() if hasattr(self.browser, 'page') else None
        if page is not None:
            profile = page.profile() if hasattr(page, 'profile') else None
            if profile is not None:
                # Clear cookies
                cookie_store = profile.cookieStore() if hasattr(profile, 'cookieStore') else None
                if cookie_store is not None and hasattr(cookie_store, 'deleteAllCookies'):
                    cookie_store.deleteAllCookies()
                # Clear cache
                if hasattr(profile, 'clearHttpCache'):
                    profile.clearHttpCache()
            # Clear local storage via JavaScript
            if hasattr(page, 'runJavaScript'):
                page.runJavaScript("""
                    try {
                        localStorage.clear();
                        sessionStorage.clear();
                    } catch(e) {}
                """)


class PlatformConnectionWidget(QWidget):
    """Widget for managing a single platform connection"""
    
    connect_requested = pyqtSignal(str, str, str)  # platform, username, token
    disable_changed = pyqtSignal(str, bool)
    # DLive OAuth JavaScript-based logic removed. Implement a new flow or manual entry as needed.
    config = ConfigManager()
    
    def __init__(self, platform_name, platform_id, chat_manager, parent=None):
        super().__init__(parent)
        self.platform_name = platform_name
        self.platform_id = platform_id
        self.chat_manager = chat_manager
        self.streamer_display_name = QLabel("")
        self.streamer_login_btn = QPushButton("Login")
        self.bot_display_name = QLabel("")
        self.bot_login_btn = QPushButton("Login")
        self.status_label = QLabel("")
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        from ui.ui_elements import ToggleSwitch
        self.disable_checkbox = ToggleSwitch(width=34, height=17)
        self.disable_checkbox.setToolTip("Disable platform (mute chat)")
        self.ngrok_manager = None
        self.trovo_ngrok_tunnel = None
        self.platform_widgets = {}

        # Layout setup
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Two-column layout for streamer/bot
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(16)

        # Streamer Column (left)
        streamer_col = QVBoxLayout()
        streamer_label = QLabel("Streamer")
        streamer_label.setStyleSheet("color: #4A90E2; font-size: 12pt; font-weight: bold;")
        streamer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        streamer_col.addWidget(streamer_label)

        self.streamer_display_name.setStyleSheet(
            "background: #1E1E1E; color: #4A90E2; border-radius: 6px; border: 2px solid #4A90E2; padding: 6px; font-size: 11pt; text-align: center;"
        )
        self.streamer_display_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        streamer_col.addWidget(self.streamer_display_name)

        self.streamer_login_btn.setStyleSheet(
            "background: #4A90E2; color: white; border-radius: 6px; font-size: 11pt; padding: 8px; width: 100%;"
        )
        self.streamer_login_btn.setMinimumHeight(32)
        streamer_col.addWidget(self.streamer_login_btn)
        streamer_col.addStretch(1)

        # Bot Column (right)
        bot_col = QVBoxLayout()
        bot_label = QLabel("Bot")
        bot_label.setStyleSheet("color: #7ED321; font-size: 12pt; font-weight: bold;")
        bot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bot_col.addWidget(bot_label)

        self.bot_display_name.setStyleSheet(
            "background: #1E1E1E; color: #7ED321; border-radius: 6px; border: 2px solid #7ED321; padding: 6px; font-size: 11pt; text-align: center;"
        )
        self.bot_display_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bot_col.addWidget(self.bot_display_name)

        self.bot_login_btn.setStyleSheet(
            "background: #7ED321; color: white; border-radius: 6px; font-size: 11pt; padding: 8px; width: 100%;"
        )
        self.bot_login_btn.setMinimumHeight(32)
        bot_col.addWidget(self.bot_login_btn)
        bot_col.addStretch(1)

        columns_layout.addLayout(streamer_col, 1)
        columns_layout.addLayout(bot_col, 1)
        main_layout.addLayout(columns_layout)

        # Log/Status Area
        self.info_text.setReadOnly(True)
        self.info_text.setFixedHeight(120)
        self.info_text.setStyleSheet(
            "background: #232323; color: #CCCCCC; border: 1px solid #333; border-radius: 4px; font-family: 'Segoe UI', sans-serif; font-size: 10pt;"
        )
        main_layout.addSpacing(8)
        main_layout.addWidget(self.info_text)
        settings_widget = self.create_platform_section(self.platform_id, True, True, True)
        main_layout.addWidget(settings_widget)
        # Load stream info at startup on the main thread after the event loop starts
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.refresh_platform_info(self.platform_id))
        except Exception:
            pass

        # Move Disable platform checkbox to the top
        # Add label next to toggle switch
        disable_row = QHBoxLayout()
        disable_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        disable_row.setSpacing(8)
        disable_row.addWidget(self.disable_checkbox)
        # Connect disable toggle to handler that saves state and notifies parent
        try:
            self.disable_checkbox.stateChanged.connect(self._on_disable_toggled)
        except Exception:
            pass
        disable_label = QLabel("Disable platform")
        disable_label.setStyleSheet("color: #BB6BD9; font-size: 11pt; font-weight: bold; margin-top: 10px; margin-bottom: 12px;")
        disable_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        disable_row.addWidget(disable_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.insertLayout(0, disable_row)

        # Large empty space below
        main_layout.addStretch(1)

        # Connect buttons to login/logout logic
        if self.platform_id == "trovo":
            self.streamer_login_btn.clicked.connect(lambda: self.onTrovoAccountAction("streamer"))
            self.bot_login_btn.clicked.connect(lambda: self.onTrovoAccountAction("bot"))
        else:
            self.streamer_login_btn.clicked.connect(lambda: self.onAccountAction("streamer"))
            self.bot_login_btn.clicked.connect(lambda: self.onAccountAction("bot"))

        # Main-thread executor for scheduling UI updates from worker threads
        try:
            self._mt_executor = get_main_thread_executor(self)
        except Exception:
            # Fallback: ensure attribute exists to avoid attribute errors
            self._mt_executor = None

    def create_platform_section(self, platform_name, has_notification, has_category, has_tags):
        """Create a platform-specific settings section"""
        group = QGroupBox(f"Stream Settings")
        group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        category_layout = None
        
        # Initialize storage for this platform's widgets
        if platform_name not in self.platform_widgets:
            self.platform_widgets[platform_name] = {}
        
        # Stream Title
        title_layout = QHBoxLayout()
        title_label = QLabel("Stream Title:")
        title_label.setStyleSheet("color: #ffffff; font-weight: normal;")
        title_label.setMinimumWidth(150)
        title_input = QLineEdit()
        title_input.setObjectName(f"{platform_name}_title")
        self.platform_widgets[platform_name]['title'] = title_input
        title_input.setPlaceholderText(f"Enter {platform_name} stream title...")
        title_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #4a90e2;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addWidget(title_input)
        layout.addLayout(title_layout)
        
        # Category and Go-Live Notification (if supported)
        # Render these in two columns: category on the left, notification on the right.
        if has_category or has_notification:
            category_layout = QVBoxLayout()
            top_row = QHBoxLayout()
            left_col = QVBoxLayout()
            right_col = QVBoxLayout()

            left_col.setSpacing(6)
            right_col.setSpacing(6)
            # Ensure columns are top-aligned so inputs don't get extra space above them
            left_col.setAlignment(Qt.AlignmentFlag.AlignTop)
            right_col.setAlignment(Qt.AlignmentFlag.AlignTop)
            top_row.setAlignment(Qt.AlignmentFlag.AlignTop)
            # Remove extra margins for a tighter layout
            category_layout.setContentsMargins(0, 0, 0, 0)
            top_row.setContentsMargins(0, 0, 0, 0)

            # Category column (left)
            if has_category:
                category_label = QLabel("Stream Category:")
                category_label.setStyleSheet("color: #ffffff; font-weight: normal;")
                category_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                category_input = QLineEdit()
                category_input.setObjectName(f"{platform_name}_category")
                category_input.setPlaceholderText("Enter stream category/game...")
                self.platform_widgets[platform_name]['category'] = category_input
                category_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #2b2b2b;
                        color: #ffffff;
                        border: 1px solid #3d3d3d;
                        border-radius: 3px;
                        padding: 8px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #4a90e2;
                    }
                """)
                # Label above input, left-justified
                left_col.addWidget(category_label, alignment=Qt.AlignmentFlag.AlignLeft)
                left_col.addWidget(category_input)

                # Only for Twitch: add suggestions list using the left column as anchor
                if platform_name == 'twitch':
                    self._setup_twitch_suggestions(platform_name, category_input, category_layout)

            # Notification column (right)
            if has_notification:
                notif_label = QLabel("Go-Live Notification:")
                notif_label.setStyleSheet("color: #ffffff; font-weight: normal; margin-bottom: 5px;")
                notif_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                notif_input = QTextEdit()
                notif_input.setObjectName(f"{platform_name}_notification")
                notif_input.setPlaceholderText(f"Enter {platform_name} go-live notification...")
                notif_input.setMaximumHeight(80)
                self.platform_widgets[platform_name]['notification'] = notif_input
                notif_input.setStyleSheet("""
                    QTextEdit {
                        background-color: #2b2b2b;
                        color: #ffffff;
                        border: 1px solid #3d3d3d;
                        border-radius: 3px;
                        padding: 8px;
                    }
                    QTextEdit:focus {
                        border: 1px solid #4a90e2;
                    }
                """)
                # Label above input, left-justified within its column
                right_col.addWidget(notif_label, alignment=Qt.AlignmentFlag.AlignLeft)
                right_col.addWidget(notif_input)

            # Add columns to top row and attach to the main category layout
            # Use a 3:7 stretch to give the left column roughly 30% width
            top_row.addLayout(left_col, 3)
            top_row.addLayout(right_col, 7)
            category_layout.addLayout(top_row)

        if category_layout:
            layout.addLayout(category_layout)
        
        # Tags (if supported)
        if has_tags:
            tags_layout = QVBoxLayout()
            tags_label = QLabel("Tags:")
            tags_label.setStyleSheet("color: #ffffff; font-weight: normal; margin-bottom: 5px;")
            tags_layout.addWidget(tags_label)
            
            # Tags container
            tags_container = QWidget()
            tags_container.setObjectName(f"{platform_name}_tags_container")
            tags_container_layout = QHBoxLayout(tags_container)
            tags_container_layout.setContentsMargins(0, 0, 0, 0)
            tags_container_layout.setSpacing(5)
            # Constrain the combined width of the tags area + Add Tag button
            # to approximately 900px so the widget doesn't grow indefinitely.
            try:
                tags_container.setMaximumWidth(900)
            except Exception:
                pass
            
            # Tag display area (will contain tag chips)
            tags_display = QFrame()
            tags_display.setObjectName(f"{platform_name}_tags_display")
            tags_display.setStyleSheet("""
                QFrame {
                    background-color: #2b2b2b;
                    border: 1px solid #3d3d3d;
                    border-radius: 3px;
                    padding: 8px;
                }
            """)
            # Use a wrapping flow layout so tag chips will wrap to new lines
            from ui.ui_elements import FlowLayout
            tags_display_layout = FlowLayout(tags_display, margin=5, spacing=5)
            # Ensure the FlowLayout is installed on the tags_display widget so
            # calls to `tags_display.layout()` return the FlowLayout instance.
            try:
                tags_display.setLayout(tags_display_layout)
            except Exception:
                pass
            # Make sure the tags display can expand horizontally and allow
            # vertical growth as chips wrap across lines.
            try:
                tags_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            except Exception:
                pass
            tags_container_layout.addWidget(tags_display, 1)
            self.platform_widgets[platform_name]['tags_display'] = tags_display
            
            # Add tag button
            add_tag_btn = QPushButton("+ Add Tag")
            add_tag_btn.setObjectName(f"{platform_name}_add_tag")
            add_tag_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #4a4a4a;
                    border-radius: 3px;
                    padding: 8px 15px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)
            add_tag_btn.clicked.connect(lambda: self.add_tag(platform_name))
            tags_container_layout.addWidget(add_tag_btn)
            
            tags_layout.addWidget(tags_container)
            layout.addLayout(tags_layout)
        
        # OAuth scope warning (for platforms that need it)
        if platform_name == 'twitch':
            oauth_warning = QLabel()
            oauth_warning.setObjectName(f"{platform_name}_oauth_warning")
            oauth_warning.setStyleSheet("""
                QLabel {
                    color: #ff9800;
                    background-color: #3d2800;
                    border: 1px solid #ff9800;
                    border-radius: 3px;
                    padding: 8px;
                    margin: 5px 0;
                }
            """)
            oauth_warning.setWordWrap(True)
            oauth_warning.setVisible(False)  # Hidden by default
            self.platform_widgets[platform_name]['oauth_warning'] = oauth_warning
            # Reconnect button (shown when OAuth scope issues are detected)
            reconnect_btn = QPushButton("Reconnect")
            reconnect_btn.setVisible(False)
            reconnect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f39c12;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #d68910;
                }
            """)
            # Clicking reconnect triggers the normal login flow
            reconnect_btn.clicked.connect(lambda: self.streamer_login_btn.click())
            self.platform_widgets[platform_name]['reconnect_btn'] = reconnect_btn
            layout.addWidget(reconnect_btn)
            layout.addWidget(oauth_warning)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName(f"{platform_name}_refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        refresh_btn.clicked.connect(lambda: self.refresh_platform_info(platform_name))
        buttons_layout.addWidget(refresh_btn)
        
        # Save button
        save_btn = QPushButton("💾 Save")
        save_btn.setObjectName(f"{platform_name}_save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        save_btn.clicked.connect(lambda: self.save_platform_info(platform_name))
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)

        return group

    def _setup_twitch_suggestions(self, platform_name, category_input, category_layout):
        """Create and wire a suggestions list for Twitch category input."""
        from PyQt6.QtCore import QTimer, QObject, QEvent, Qt, QPoint

        # Create a floating child widget (not a top-level Popup) anchored to the input.
        # Using a child widget avoids stealing focus — it stays visually floating but input retains focus.
        # Create a top-level popup so it can overlap other UI elements
        # Use Popup/Tool flags and avoid activating the window so input focus remains
        popup = QWidget(None)
        popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        try:
            popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        except Exception:
            pass
        popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        popup.setObjectName(f"{platform_name}_category_popup")
        popup.setStyleSheet("background-color: #232323; border: 1px solid #3d3d3d; border-radius: 4px;")
        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(6, 6, 6, 6)
        popup_layout.setSpacing(4)

        # No searching indicator (removed for snappier UI)

        suggestions_list = QListWidget()
        # Suggestions list shouldn't grab focus until explicitly requested
        suggestions_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        suggestions_list.setMaximumHeight(200)
        # Hide the vertical scrollbar so the list appears as a clean box
        suggestions_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Reserve space for at least 5 rows so popup isn't a single-line box
        try:
            fm = category_input.fontMetrics()
            row_h = fm.height() + 6
            min_rows = 5
            suggestions_list.setMinimumHeight(row_h * min_rows)
        except Exception:
            # Fallback to a reasonable minimum height
            suggestions_list.setMinimumHeight(120)
        suggestions_list.setUniformItemSizes(True)
        suggestions_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 10pt;
            }
            QListWidget::item:selected {
                background: #4a90e2;
                color: #fff;
            }
        """)
        popup_layout.addWidget(suggestions_list)

        popup.hide()

        # Local cache of last-fetched categories for immediate local filtering
        self.platform_widgets[platform_name]['category_suggestions_cache'] = []

        # Store references
        self.platform_widgets[platform_name]['category_suggestions'] = suggestions_list
        self.platform_widgets[platform_name]['category_suggestions_popup'] = popup

        # Debounce timer and state (reduced for snappier UX)
        # Reduced debounce and lower min_chars for snappier search
        debounce_ms = 100
        min_chars = 1
        timer = QTimer()
        timer.setSingleShot(True)
        timer.setInterval(debounce_ms)
        last_query = {'text': ''}

        def perform_search(query_text):
            # Called from timer timeout on main thread; start background fetch
            if not query_text or len(query_text.strip()) < min_chars:
                suggestions_list.clear()
                popup.hide()
                
                return

            # no-op: spinner removed

            def do_search():
                import requests
                import traceback
                connector = self.chat_manager.connectors.get('twitch')
                client_id = getattr(connector, 'client_id', None) if connector else None
                oauth_token = getattr(connector, 'oauth_token', None) if connector else None
                if not client_id or not oauth_token:
                    twitch_config = self.config.get_platform_config('twitch') if self.config else {}
                    client_id = client_id or twitch_config.get('client_id', '')
                    oauth_token = oauth_token or twitch_config.get('oauth_token', '')
                if not client_id or not oauth_token:
                    def _clear():
                        suggestions_list.clear()
                        suggestions_list.setVisible(False)
                    self.run_on_main_thread(_clear)
                    return

                url = "https://api.twitch.tv/helix/search/categories"
                headers = {"Client-ID": client_id, "Authorization": f"Bearer {oauth_token}"}
                params = {"query": query_text.strip()}
                try:
                    import requests
                    import traceback
                    import threading

                    resp = requests.get(url, headers=headers, params=params, timeout=6)
                    if resp.status_code == 200:
                        data = resp.json()
                        # Fetch a larger set from Twitch and show up to 10 suggestions
                        categories = data.get("data", [])[:12]

                        def _update():
                            # Update cache and UI
                            names = [cat.get("name", "") for cat in categories]
                            self.platform_widgets[platform_name]['category_suggestions_cache'] = names
                            suggestions_list.clear()
                            # Show up to 10 suggestions in the popup
                            for name in names[:10]:
                                suggestions_list.addItem(name)
                            visible = suggestions_list.count() > 0
                            if visible:
                                # Position popup under the input and set width to match input
                                try:
                                    inp_w = category_input.width()
                                    popup.setFixedWidth(inp_w)
                                    # Map the intended global position into this widget's local coordinates
                                    global_pos = category_input.mapToGlobal(QPoint(0, category_input.height()))
                                    # For a top-level popup we can move directly to global coordinates
                                    popup.move(global_pos)
                                except Exception:
                                    pass
                                popup.show()
                            else:
                                popup.hide()

                        self.run_on_main_thread(_update)
                    else:
                        self.run_on_main_thread(lambda: (suggestions_list.clear(), suggestions_list.setVisible(False)))
                except Exception as e:
                    print("Twitch suggestions fetch error:", e)
                    try:
                        import traceback
                        traceback.print_exc()
                    except Exception:
                        pass
                    self.run_on_main_thread(lambda: (suggestions_list.clear(), suggestions_list.setVisible(False)))

            threading.Thread(target=do_search, daemon=True).start()

        def on_timer_timeout():
            perform_search(last_query['text'])

        timer.timeout.connect(on_timer_timeout)

        def schedule_search(text):
            last_query['text'] = text
            if not text or len(text.strip()) < min_chars:
                # hide immediately
                suggestions_list.clear()
                popup.hide()
                
                timer.stop()
                return
            # no searching indicator (removed)
            # If we have a cached set of categories, locally filter and show immediately for snappy UX
            try:
                cache = self.platform_widgets[platform_name].get('category_suggestions_cache', [])
                q = text.strip().lower()
                if cache and q:
                    matches = [c for c in cache if q in c.lower()]
                    if matches:
                        suggestions_list.clear()
                        for m in matches[:10]:
                            suggestions_list.addItem(m)
                        try:
                            inp_w = category_input.width()
                            popup.setFixedWidth(inp_w)
                            global_pos = category_input.mapToGlobal(QPoint(0, category_input.height()))
                            popup.move(global_pos)
                        except Exception:
                            pass
                        popup.show()
            except Exception:
                pass
            timer.start()

        category_input.textChanged.connect(schedule_search)
        category_input.editingFinished.connect(lambda: popup.setVisible(False))

        def on_suggestion_clicked():
            selected = suggestions_list.currentItem()
            if selected:
                category_input.setText(selected.text())
                suggestions_list.clear()
                popup.setVisible(False)

        suggestions_list.itemClicked.connect(on_suggestion_clicked)

        # Keyboard navigation support: arrow keys, Enter, Esc
        class _KeyFilter(QObject):
            def eventFilter(self, a0, a1):
                if a1.type() == QEvent.Type.KeyPress:
                    key = a1.key()
                    # If typing in the category input and user presses Down, move focus to suggestions
                    if a0 is category_input:
                        if key == Qt.Key.Key_Down and popup.isVisible() and suggestions_list.count() > 0:
                            suggestions_list.setFocus()
                            suggestions_list.setCurrentRow(0)
                            return True
                        if key == Qt.Key.Key_Escape:
                            popup.setVisible(False)
                            return False
                    # If focus is on suggestions list, handle navigation and selection
                    if a0 is suggestions_list:
                        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                            current = suggestions_list.currentItem()
                            if current:
                                category_input.setText(current.text())
                            suggestions_list.clear()
                            popup.setVisible(False)
                            category_input.setFocus()
                            return True
                        if key == Qt.Key.Key_Escape:
                            popup.setVisible(False)
                            category_input.setFocus()
                            return True
                        if key == Qt.Key.Key_Up:
                            # If at top and press Up, return focus to input
                            if suggestions_list.currentRow() == 0:
                                category_input.setFocus()
                                return True
                return False

        key_filter = _KeyFilter(self)
        category_input.installEventFilter(key_filter)
        suggestions_list.installEventFilter(key_filter)

    def add_tag(self, platform_name):
        """Add a new tag for the platform"""
        from PyQt6.QtWidgets import QInputDialog
        
        tag_text, ok = QInputDialog.getText(
            self,
            "Add Tag",
            f"Enter a new tag for {platform_name}:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and tag_text:
            # Find the tag display area
            tags_display = self.findChild(QFrame, f"{platform_name}_tags_display")
            if tags_display:
                layout = tags_display.layout()
                # Ensure a layout exists on the tags display
                if layout is None:
                    layout = QHBoxLayout(tags_display)
                    layout.setContentsMargins(5, 5, 5, 5)
                    layout.setSpacing(5)
                
                # Create tag chip
                tag_chip = QFrame()
                tag_chip.setStyleSheet("""
                    QFrame {
                        background-color: #4a90e2;
                        border-radius: 3px;
                        padding: 2px 8px;
                    }
                """)
                chip_layout = QHBoxLayout(tag_chip)
                chip_layout.setContentsMargins(5, 3, 5, 3)
                chip_layout.setSpacing(5)
                
                tag_label = QLabel(tag_text)
                tag_label.setStyleSheet("color: #ffffff; font-size: 11px;")
                chip_layout.addWidget(tag_label)
                
                remove_btn = QPushButton("✕")
                remove_btn.setFixedSize(16, 16)
                remove_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #ffffff;
                        border: none;
                        font-size: 12px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        color: #ff4444;
                    }
                """)
                remove_btn.clicked.connect(lambda: self.remove_tag(platform_name, tag_text, tag_chip))
                chip_layout.addWidget(remove_btn)
                
                # Add the tag chip to the layout and refresh geometry so the
                # FlowLayout recalculates positions immediately.
                # Parent and show the chip so FlowLayout can manage it immediately
                try:
                    tag_chip.setParent(tags_display)
                    tag_chip.setVisible(True)
                except Exception:
                    pass
                layout.addWidget(tag_chip)
                try:
                    layout.invalidate()
                except Exception:
                    try:
                        layout.update()
                    except Exception:
                        pass
                try:
                    tags_display.updateGeometry()
                    tags_display.repaint()
                    tags_display.adjustSize()
                except Exception:
                    pass
                
                print(f"[ConnectionsPage] Added tag '{tag_text}' for {platform_name}")
    
    def remove_tag(self, platform_name, tag_text, tag_chip):
        """Remove a tag from the platform"""
        tag_chip.deleteLater()
        print(f"[ConnectionsPage] Removed tag '{tag_text}' from {platform_name}")
    
    def refresh_platform_info(self, platform_name):
        """Refresh stream info from the platform API"""
        print(f"[ConnectionsPage] Refreshing stream info for {platform_name}")
        
        # Get the platform connector
        platform_id = platform_name.lower()
        connector = self.chat_manager.connectors.get(platform_id)
        
        if not connector:
            print(f"[ConnectionsPage] No connector found for {platform_name}")
            return
        
        # Debug connector attributes
        print(f"[{platform_name}] Connector: {connector.__class__.__name__}")
        print(f"[{platform_name}] Is connected: {getattr(connector, 'is_connected', 'N/A')}")
        
        try:
            if platform_name == 'twitch':
                self.refresh_twitch_info(connector)
            elif platform_name == 'youtube':
                self.refresh_youtube_info(connector)
            elif platform_name == 'kick':
                self.refresh_kick_info(connector)
            elif platform_name == 'trovo':
                self.refresh_trovo_info(connector)
            elif platform_name == 'dlive':
                self.refresh_dlive_info(connector)
        except Exception as e:
            print(f"[ConnectionsPage] Error refreshing {platform_name} info: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_twitch_info(self, connector):
        """Refresh Twitch stream info"""
        import requests
        
        print(f"[Twitch] Attempting to refresh info...")
        
        # Try to get credentials from config if connector doesn't have them
        twitch_config = self.config.get_platform_config('twitch') if self.config else {}

        # Pre-populate UI from locally saved stream_info so local settings
        # (like Go-Live notification) persist across restarts even when
        # the platform API doesn't return live info immediately.
        try:
            stream_info = twitch_config.get('stream_info', {}) if isinstance(twitch_config, dict) else {}
            if 'twitch' in self.platform_widgets and stream_info:
                widgets = self.platform_widgets['twitch']
                # Title
                if stream_info.get('title') and widgets.get('title'):
                    try:
                        widgets['title'].blockSignals(True)
                        widgets['title'].setText(stream_info.get('title', ''))
                    finally:
                        widgets['title'].blockSignals(False)

                # Category
                if stream_info.get('category') and widgets.get('category'):
                    try:
                        widgets['category'].blockSignals(True)
                        widgets['category'].setText(stream_info.get('category', ''))
                    finally:
                        widgets['category'].blockSignals(False)

                # Notification (QTextEdit)
                if 'notification' in stream_info and widgets.get('notification'):
                    try:
                        widgets['notification'].setPlainText(stream_info.get('notification', ''))
                    except Exception:
                        try:
                            widgets['notification'].setText(stream_info.get('notification', ''))
                        except Exception:
                            pass

                # Tags
                if stream_info.get('tags') and widgets.get('tags_display'):
                    try:
                        tags_display = widgets['tags_display']
                        layout = tags_display.layout()
                        if layout is not None:
                            while layout.count() > 0:
                                item = layout.takeAt(0)
                                if item and item.widget():
                                    item.widget().deleteLater()
                        for tag_name in stream_info.get('tags', []):
                            self.add_tag_chip('twitch', tag_name, tags_display)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[ConnectionsPage] Failed to pre-populate Twitch stream_info from config: {e}")
        
        client_id = getattr(connector, 'client_id', None) if connector else None
        if not client_id:
            client_id = 'h84tx3mvvpk9jyt8rv8p8utfzupz82'  # Default client ID
        
        oauth_token = getattr(connector, 'oauth_token', None) if connector else None
        if not oauth_token:
            oauth_token = twitch_config.get('oauth_token', '')
        
        username = getattr(connector, 'username', None) if connector else None
        if not username:
            username = twitch_config.get('username', '')
        
        print(f"[Twitch] Has oauth_token: {bool(oauth_token)}")
        print(f"[Twitch] Has client_id: {bool(client_id)}")
        print(f"[Twitch] Has username: {bool(username)}")
        
        if not oauth_token or not client_id or not username:
            print(f"[Twitch] Missing required credentials (check config)")
            return
        
        try:
            # Get broadcaster user info
            headers = {
                'Client-ID': client_id,
                'Authorization': f'Bearer {oauth_token}'
            }
            
            # Get user ID
            user_response = requests.get(
                'https://api.twitch.tv/helix/users',
                headers=headers,
                params={'login': username},
                timeout=10
            )
            
            if user_response.status_code != 200:
                print(f"[Twitch] Failed to get user info: {user_response.status_code}")
                return
            
            user_data = user_response.json()
            if not user_data.get('data'):
                return
            
            broadcaster_id = user_data['data'][0]['id']
            
            # Get channel information
            channel_response = requests.get(
                'https://api.twitch.tv/helix/channels',
                headers=headers,
                params={'broadcaster_id': broadcaster_id}
            )
            
            if channel_response.status_code == 200:
                channel_data = channel_response.json()
                if channel_data.get('data'):
                    info = channel_data['data'][0]
                    
                    # Update title
                    if 'title' in info and 'twitch' in self.platform_widgets:
                        self.platform_widgets['twitch']['title'].setText(info['title'])
                        print(f"[Twitch] Loaded title: {info['title']}")
                    
                    # Update category
                    if 'game_name' in info and 'twitch' in self.platform_widgets:
                        category_widget = self.platform_widgets['twitch'].get('category')
                        if category_widget:
                            try:
                                category_widget.blockSignals(True)
                                category_widget.setText(info['game_name'])
                            finally:
                                category_widget.blockSignals(False)
                            print(f"[Twitch] Loaded category: {info['game_name']}")
                    
                    # Update tags (tags are now in the channel info as a list of strings)
                    if 'tags' in info and info['tags'] and 'twitch' in self.platform_widgets:
                        tags_display = self.platform_widgets['twitch'].get('tags_display')
                        if tags_display:
                            # Clear existing tags
                            layout = tags_display.layout()
                            if layout is not None:
                                while layout.count() > 0:
                                    item = layout.takeAt(0)
                                    if item and item.widget():
                                        item.widget().deleteLater()
                            
                            # Add new tags
                            for tag_name in info['tags']:
                                self.add_tag_chip('twitch', tag_name, tags_display)
                            try:
                                tags_display.setVisible(True)
                                tags_display.show()
                            except Exception:
                                pass
                            print(f"[Twitch] Loaded {len(info['tags'])} tags")
                            # Diagnostic: report layout count and child widget visibilities
                            try:
                                l = tags_display.layout()
                                count = l.count() if l is not None else -1
                                td_size = tags_display.size()
                                td_hint = tags_display.sizeHint()
                                print(f"[ConnectionsPage][DIAG] tags_populated: layout_count={count} tags_display_size={td_size.width()}x{td_size.height()} hint={td_hint.width()}x{td_hint.height()} visible={tags_display.isVisible()}")
                                # enumerate children
                                if l is not None:
                                    for i in range(l.count()):
                                        item = l.itemAt(i)
                                        w = item.widget() if item is not None else None
                                        if w is not None:
                                            text = ''
                                            try:
                                                sub = w.layout().itemAt(0).widget()
                                                text = sub.text() if hasattr(sub, 'text') else ''
                                            except Exception:
                                                pass
                                            print(f"[ConnectionsPage][DIAG] child[{i}]: class={w.__class__.__name__} visible={w.isVisible()} text={text}")
                                # Parent chain visibility
                                try:
                                    chain = []
                                    p = tags_display
                                    while p is not None:
                                        try:
                                            chain.append((p.__class__.__name__, p.isVisible()))
                                        except Exception:
                                            chain.append((p.__class__.__name__, 'N/A'))
                                        p = getattr(p, 'parent', lambda: None)() if not hasattr(p, 'parentWidget') else p.parentWidget()
                                    print(f"[ConnectionsPage][DIAG] parent_chain: {chain}")
                                except Exception as e:
                                    print(f"[ConnectionsPage][DIAG] parent_chain diagnostic failed: {e}")
                            except Exception as e:
                                print(f"[ConnectionsPage][DIAG] tags_populated diagnostic failed: {e}")
                        else:
                            print(f"[Twitch] tags_display widget not found")
                    else:
                        print(f"[Twitch] No tags in channel info or widget missing")
            else:
                print(f"[Twitch] Channel info request failed: {channel_response.status_code}")
                    
        except Exception as e:
            print(f"[Twitch] Error refreshing info: {e}")
    
    def refresh_youtube_info(self, connector):
        """Refresh YouTube stream info"""
        import requests
        
        print(f"[YouTube] Attempting to refresh info...")
        print(f"[YouTube] Has oauth_token: {hasattr(connector, 'oauth_token')}")
        
        if not hasattr(connector, 'oauth_token') or not connector.oauth_token:
            print(f"[YouTube] No oauth token, skipping refresh")
            return
        
        try:
            headers = {'Authorization': f'Bearer {connector.oauth_token}'}
            
            # Get live broadcast
            response = requests.get(
                'https://www.googleapis.com/youtube/v3/liveBroadcasts',
                headers=headers,
                params={
                    'part': 'snippet,contentDetails',
                    'mine': 'true',
                    'broadcastStatus': 'active'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    info = data['items'][0]['snippet']
                    
                    # Update title
                    if 'title' in info and 'youtube' in self.platform_widgets:
                        self.platform_widgets['youtube']['title'].setText(info['title'])
                        print(f"[YouTube] Loaded title: {info['title']}")
                else:
                    print(f"[YouTube] No active broadcasts found")
            else:
                print(f"[YouTube] API request failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"[YouTube] Error details: {error_data}")
                except:
                    pass
        except Exception as e:
            print(f"[YouTube] Error refreshing info: {e}")
    
    def refresh_kick_info(self, connector):
        """Refresh Kick stream info"""
        import requests
        import cloudscraper
        
        print(f"[Kick] Attempting to refresh info...")
        
        # Try to get credentials from config
        kick_config = self.config.get_platform_config('kick') if self.config else {}
        
        # Use channel_slug if available, otherwise try username
        channel_identifier = None
        if connector:
            if hasattr(connector, 'channel_slug') and connector.channel_slug:
                channel_identifier = connector.channel_slug
            elif hasattr(connector, 'username') and connector.username:
                channel_identifier = connector.username
        
        if not channel_identifier:
            channel_identifier = kick_config.get('username', '')
        
        if not channel_identifier:
            print(f"[Kick] No channel identifier available (set username in config)")
            return
        
        print(f"[Kick] Using channel identifier: {channel_identifier}")
        
        try:
            scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
            )
            response = scraper.get(f"https://kick.com/api/v2/channels/{channel_identifier}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"[Kick] API response keys: {list(data.keys())}")
                
                # Check if channel data exists (even if not live)
                if 'user' in data and data.get('user'):
                    user_info = data['user']
                    print(f"[Kick] Channel found: {user_info.get('username', 'Unknown')}")
                
                # Update title if stream is live
                if data.get('livestream'):
                    stream_info = data['livestream']
                    if 'session_title' in stream_info and 'kick' in self.platform_widgets:
                        self.platform_widgets['kick']['title'].setText(stream_info['session_title'])
                        print(f"[Kick] Loaded title: {stream_info['session_title']}")
                    
                    # Update category
                    if stream_info.get('categories') and 'kick' in self.platform_widgets:
                        category_widget = self.platform_widgets['kick'].get('category')
                        if category_widget and stream_info['categories']:
                            category_name = stream_info['categories'][0].get('name', '')
                            try:
                                category_widget.blockSignals(True)
                                category_widget.setText(category_name)
                            finally:
                                category_widget.blockSignals(False)
                            print(f"[Kick] Loaded category: {category_name}")
                    
                    # Update tags
                    if 'kick' in self.platform_widgets:
                        print(f"[Kick] Checking for tags in stream_info...")
                        print(f"[Kick] stream_info keys: {list(stream_info.keys())}")
                        if 'tags' in stream_info:
                            print(f"[Kick] Tags found: {stream_info['tags']}")
                        
                        if stream_info.get('tags'):
                            tags_display = self.platform_widgets['kick'].get('tags_display')
                            if tags_display:
                                # Clear existing tags
                                layout = tags_display.layout()
                                if layout is not None:
                                    while layout.count() > 0:
                                        item = layout.takeAt(0)
                                        if item and item.widget():
                                            item.widget().deleteLater()
                                
                                # Add new tags (Kick returns tags as a list of strings)
                                for tag_name in stream_info['tags']:
                                    self.add_tag_chip('kick', tag_name, tags_display)
                                print(f"[Kick] Loaded {len(stream_info['tags'])} tags")
                            else:
                                print(f"[Kick] tags_display widget not found")
                        else:
                            print(f"[Kick] No tags in stream_info")
                else:
                    print(f"[Kick] Channel is not currently live (no livestream data)")
                    print(f"[Kick] Keeping saved config data displayed")
            else:
                print(f"[Kick] API request failed: {response.status_code}")
                print(f"[Kick] Response text: {response.text[:200]}")
                print(f"[Kick] Keeping saved config data displayed")
        except Exception as e:
            print(f"[Kick] Error refreshing info: {e}")
            print(f"[Kick] Keeping saved config data displayed")
            import traceback
            traceback.print_exc()
    
    def refresh_trovo_info(self, connector):
        """Refresh Trovo stream info"""
        import requests
        
        print(f"[Trovo] Attempting to refresh info...")
        
        # Try loading username and access token from config
        trovo_config = self.config.get_platform_config('trovo') if self.config else {}
        username = trovo_config.get('username', '')
        access_token = trovo_config.get('access_token', '')
        
        # Fallback to connector if available
        if connector and hasattr(connector, 'access_token'):
            if not access_token:
                access_token = connector.access_token
        
        print(f"[Trovo] Username from config: '{username}'")
        print(f"[Trovo] Has access token: {bool(access_token)}")
        
        if not username:
            print(f"[Trovo] No username found in config")
            return
        
        try:
            headers = {
                'Accept': 'application/json',
                'Client-ID': 'b239c1cc698e04e93a164df321d142b3',
                'Content-Type': 'application/json'
            }
            
            print(f"[Trovo] Making API request with username: {username}")
            
            # First get user info (and channel_id) using getusers endpoint
            # This endpoint uses "user" (array) not "username" (string)
            user_response = requests.post(
                'https://open-api.trovo.live/openplatform/getusers',
                headers=headers,
                json={'user': [username]}
            )
            
            print(f"[Trovo] User API response status: {user_response.status_code}")
            
            if user_response.status_code != 200:
                print(f"[Trovo] Failed to get user info: {user_response.text}")
                return
            
            user_data = user_response.json()
            if not user_data.get('users') or len(user_data['users']) == 0:
                print(f"[Trovo] No user found for username: {username}")
                return
            
            channel_id = user_data['users'][0]['channel_id']
            print(f"[Trovo] Got channel_id: {channel_id}")
            
            # Now get channel info using channel_id
            channel_response = requests.post(
                'https://open-api.trovo.live/openplatform/channels/id',
                headers=headers,
                json={'channel_id': int(channel_id)}
            )
            
            print(f"[Trovo] Channel API response status: {channel_response.status_code}")
            
            if channel_response.status_code == 200:
                data = channel_response.json()
                print(f"[Trovo] Channel response keys: {list(data.keys())}")
                
                # Update title
                if 'live_title' in data and 'trovo' in self.platform_widgets:
                    self.platform_widgets['trovo']['title'].setText(data['live_title'])
                    print(f"[Trovo] Loaded title: {data['live_title']}")
                
                # Update category
                if 'category_name' in data and 'trovo' in self.platform_widgets:
                    category_widget = self.platform_widgets['trovo'].get('category')
                    if category_widget:
                        try:
                            category_widget.blockSignals(True)
                            category_widget.setText(data['category_name'])
                        finally:
                            category_widget.blockSignals(False)
                        print(f"[Trovo] Loaded category: {data['category_name']}")
            else:
                print(f"[Trovo] Channel API request failed: {channel_response.status_code}")
                print(f"[Trovo] Response: {channel_response.text[:300]}")
                try:
                    error_data = channel_response.json()
                    print(f"[Trovo] Error details: {error_data}")
                except:
                    pass
        except Exception as e:
            print(f"[Trovo] Error refreshing info: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_dlive_info(self, connector):
        """Refresh DLive stream info"""
        import requests
        
        # DLive uses GraphQL API
        # This is a placeholder - actual implementation would need auth token
        print(f"[DLive] Info refresh not yet implemented")
    
    def add_tag_chip(self, platform_name, tag_text, tags_display):
        """Add a tag chip to the tags display"""
        layout = tags_display.layout()
        
        # Create tag chip
        tag_chip = QFrame()
        tag_chip.setStyleSheet("""
            QFrame {
                background-color: #4a90e2;
                border-radius: 3px;
                padding: 2px 8px;
            }
        """)
        chip_layout = QHBoxLayout(tag_chip)
        chip_layout.setContentsMargins(5, 3, 5, 3)
        chip_layout.setSpacing(5)
        
        tag_label = QLabel(tag_text)
        tag_label.setStyleSheet("color: #ffffff; font-size: 11px;")
        chip_layout.addWidget(tag_label)
        
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 12px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ff4444;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_tag(platform_name, tag_text, tag_chip))
        chip_layout.addWidget(remove_btn)
        
        # Parent the chip to the tags_display widget so it is properly
        # managed by the FlowLayout, then add to layout and refresh.
        try:
            tag_chip.setParent(tags_display)
            # Ensure the chip widget is shown and owned by the tags container
            tag_chip.setVisible(True)
            tag_chip.show()
        except Exception:
            pass

        layout.addWidget(tag_chip)
        # Invalidate and activate the layout so FlowLayout recomputes immediately
        try:
            layout.invalidate()
            try:
                layout.activate()
            except Exception:
                pass

            # Ensure the tags_display container is visible and refreshed
            try:
                tags_display.setVisible(True)
            except Exception:
                pass

            try:
                tags_display.updateGeometry()
            except Exception:
                pass
            try:
                tags_display.adjustSize()
            except Exception:
                pass
            try:
                tags_display.repaint()
            except Exception:
                pass
        except Exception:
            pass

        # Diagnostic logs: confirm widget added and layout sizes
        try:
            lc = layout.count() if layout is not None else -1
            td_size = tags_display.size()
            td_hint = tags_display.sizeHint()
            visible = tag_chip.isVisible()
            parent = tag_chip.parent().__class__.__name__ if tag_chip.parent() is not None else 'None'
            print(f"[ConnectionsPage][DIAG] add_tag_chip: platform={platform_name!r} tag={tag_text!r} layout_count={lc} parent={parent} visible={visible} tags_display_size={td_size.width()}x{td_size.height()} hint={td_hint.width()}x{td_hint.height()}")
        except Exception as e:
            print(f"[ConnectionsPage][DIAG] add_tag_chip: diagnostic failed: {e}")

    def save_platform_info(self, platform_name):
        """Save stream info locally and update platform API"""
        print(f"[ConnectionsPage] Saving stream info for {platform_name}")
        
        if platform_name not in self.platform_widgets:
            print(f"[ConnectionsPage] No widgets found for {platform_name}")
            return
        
        widgets = self.platform_widgets[platform_name]
        
        # Save to local config
        platform_key = platform_name.lower()
        # Build stream_info locally and persist atomically via ConfigManager
        stream_info = {}
        
        # Save title
        if 'title' in widgets:
            stream_info['title'] = widgets['title'].text()
        
        # Save notification (stored locally, not sent to platform)
        if 'notification' in widgets:
            stream_info['notification'] = widgets['notification'].toPlainText()
        
        # Save category
        if 'category' in widgets:
            stream_info['category'] = widgets['category'].text()
        
        # Save tags
        if 'tags_display' in widgets:
            tags = []
            tags_layout = widgets['tags_display'].layout()
            for i in range(tags_layout.count()):
                item = tags_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, 'layout'):
                        chip_layout = widget.layout()
                        if chip_layout and chip_layout.count() > 0:
                            label = chip_layout.itemAt(0).widget()
                            if label and hasattr(label, 'text'):
                                tags.append(label.text())
            stream_info['tags'] = tags
        
        # Persist stream_info atomically using ConfigManager helper to avoid races
        try:
            merged = self.config.merge_platform_stream_info(platform_key, stream_info)
            print(f"[ConnectionsPage] Saved {platform_name} stream info to local config")
            print(f"[ConnectionsPage] Saved data: {merged}")
        except Exception as e:
            print(f"[ConnectionsPage] Failed to save stream_info atomically: {e}")
        
        # Try to update platform API (title, category, tags only - notification is local)
        update_success = self.update_platform_api(platform_name, stream_info)
        
        # Show success message
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Saved")
        if update_success:
            msg.setText(f"{platform_name} stream info saved and updated!")
            msg.setInformativeText("Local config saved and platform updated via API.")
        else:
            msg.setText(f"{platform_name} stream info saved locally!")
            msg.setInformativeText("Note: Go-live notification is stored locally.\\nTitle, category, and tags are saved in your config.\\n\\nAPI update was not attempted (may require authentication or platform may not support API updates).")
        msg.exec()

    def update_platform_api(self, platform_name, stream_info):
        """Update platform API with stream info (title, category, tags)"""
        try:
            if platform_name == 'twitch':
                return self.update_twitch_api(stream_info)
            elif platform_name == 'trovo':
                return self.update_trovo_api(stream_info)
            elif platform_name == 'kick':
                return self.update_kick_api(stream_info)
            # Other platforms can be added here
            return False
        except Exception as e:
            print(f"[{platform_name}] Error updating API: {e}")
            return False
    
    def update_twitch_api(self, stream_info):
        """Update Twitch channel info via API"""
        import requests
        
        connector = self.chat_manager.connectors.get('twitch')
        if not connector or not hasattr(connector, 'oauth_token') or not hasattr(connector, 'client_id'):
            print(f"[Twitch] Cannot update API: missing credentials")
            return False
        
        if not hasattr(connector, 'username') or not connector.username:
            print(f"[Twitch] Cannot update API: no username set")
            return False
        
        try:
            headers = {
                'Client-ID': connector.client_id,
                'Authorization': f'Bearer {connector.oauth_token}',
                'Content-Type': 'application/json'
            }
            
            # First get broadcaster ID
            user_response = requests.get(
                'https://api.twitch.tv/helix/users',
                headers=headers,
                params={'login': connector.username}
            )
            
            if user_response.status_code != 200:
                print(f"[Twitch] Failed to get user ID: {user_response.status_code}")
                return False
            
            user_data = user_response.json()
            if not user_data.get('data'):
                print(f"[Twitch] No user data returned")
                return False
            
            broadcaster_id = user_data['data'][0]['id']
            
            # Update channel information
            update_data = {}
            if stream_info.get('title'):
                update_data['title'] = stream_info['title']
            
            # For game/category, need to get game_id first
            if stream_info.get('category'):
                game_response = requests.get(
                    'https://api.twitch.tv/helix/games',
                    headers=headers,
                    params={'name': stream_info['category']}
                )
                if game_response.status_code == 200:
                    game_data = game_response.json()
                    if game_data.get('data'):
                        update_data['game_id'] = game_data['data'][0]['id']
            
            # Tags can be updated (max 10 tags, each up to 25 chars)
            if stream_info.get('tags'):
                # Twitch API accepts up to 10 tags
                tags = stream_info['tags'][:10]
                update_data['tags'] = tags
            
            if not update_data:
                print(f"[Twitch] No data to update")
                return False
            
            # Send PATCH request to update channel
            response = requests.patch(
                f'https://api.twitch.tv/helix/channels?broadcaster_id={broadcaster_id}',
                headers=headers,
                json=update_data
            )
            
            if response.status_code == 204:
                print(f"[Twitch] Successfully updated channel info")
                return True
            elif response.status_code == 401:
                print(f"[Twitch] Authentication failed - token missing required scope")
                print(f"[Twitch] Required scope: user:edit:broadcast or channel:manage:broadcast")
                print(f"[Twitch] Your changes are saved locally but not pushed to Twitch")
                
                # Show OAuth warning in UI
                if 'twitch' in self.platform_widgets:
                    warning_label = self.platform_widgets['twitch'].get('oauth_warning')
                    reconnect_btn = self.platform_widgets['twitch'].get('reconnect_btn')
                    if warning_label:
                        warning_label.setText(
                            "⚠️ Cannot update Twitch channel: Missing OAuth permissions.\n"
                            "Your changes are saved locally but not pushed to Twitch.\n"
                            "Click the button below to reconnect with updated permissions."
                        )
                        warning_label.setVisible(True)
                    if reconnect_btn:
                        reconnect_btn.setVisible(True)
                
                return False
            else:
                print(f"[Twitch] Failed to update channel: {response.status_code}")
                print(f"[Twitch] Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"[Twitch] Error updating API: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_trovo_api(self, stream_info):
        """Update Trovo channel info via API"""
        import requests
        
        connector = self.chat_manager.connectors.get('trovo')
        if not connector or not hasattr(connector, 'access_token'):
            print(f"[Trovo] Cannot update API: missing credentials")
            return False
        
        trovo_config = self.config.get_platform_config('trovo') if self.config else {}
        username = trovo_config.get('username', '')
        
        if not username:
            print(f"[Trovo] Cannot update API: no username set")
            return False
        
        try:
            headers = {
                'Accept': 'application/json',
                'Client-ID': 'b239c1cc698e04e93a164df321d142b3',
                'Content-Type': 'application/json'
            }
            
            # First get channel_id from username
            channel_response = requests.post(
                'https://open-api.trovo.live/openplatform/channels/id',
                headers=headers,
                json={'username': username}
            )
            
            if channel_response.status_code != 200:
                print(f"[Trovo] Failed to get channel info: {channel_response.status_code}")
                return False
            
            channel_data = channel_response.json()
            channel_id = channel_data.get('channel_id')
            if not channel_id:
                print(f"[Trovo] No channel_id in response")
                return False
            
            # Prepare update payload
            update_data = {'channel_id': int(channel_id)}
            
            if stream_info.get('title'):
                update_data['live_title'] = stream_info['title']
            
            # For category, need to search for category_id
            if stream_info.get('category'):
                search_response = requests.post(
                    'https://open-api.trovo.live/openplatform/searchcategory',
                    headers=headers,
                    json={'query': stream_info['category'], 'limit': 1}
                )
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    if search_data.get('category_info'):
                        update_data['category_id'] = search_data['category_info'][0]['id']
            
            if len(update_data) == 1:  # Only channel_id
                print(f"[Trovo] No data to update")
                return False
            
            # Add OAuth token for update request
            headers['Authorization'] = f'OAuth {connector.access_token}'
            
            # Send update request
            response = requests.post(
                'https://open-api.trovo.live/openplatform/channels/update',
                headers=headers,
                json=update_data
            )
            
            if response.status_code == 200:
                print(f"[Trovo] Successfully updated channel info")
                return True
            else:
                print(f"[Trovo] Failed to update channel: {response.status_code}")
                print(f"[Trovo] Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"[Trovo] Error updating API: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_kick_api(self, stream_info):
        """Update Kick channel info via API"""
        import requests
        import cloudscraper
        
        connector = self.chat_manager.connectors.get('kick')
        if not connector:
            print(f"[Kick] Cannot update API: no connector")
            return False
        
        # Get channel identifier
        channel_identifier = None
        if hasattr(connector, 'channel_slug') and connector.channel_slug:
            channel_identifier = connector.channel_slug
        elif hasattr(connector, 'username') and connector.username:
            channel_identifier = connector.username
        else:
            kick_config = self.config.get_platform_config('kick') if self.config else {}
            channel_identifier = kick_config.get('username', '')
        
        if not channel_identifier:
            print(f"[Kick] Cannot update API: no channel identifier")
            return False
        
        # Note: Kick API does not currently provide a public authenticated endpoint
        # for updating channel information (title, category, tags)
        # The official Kick API is limited and requires special access/credentials
        # This is a placeholder for when/if Kick provides such an API
        print(f"[Kick] API updates not yet supported - Kick does not provide public update endpoints")
        print(f"[Kick] Your changes are saved locally only")
        return False

    def onTrovoAccountAction(self, account_type):
        """Handle Trovo login/logout button click"""
        print(f"[Trovo] onTrovoAccountAction called for account_type: {account_type}")
        from PyQt6.QtWidgets import QMessageBox, QInputDialog
        import secrets, threading, webbrowser, time
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from urllib.parse import urlparse, parse_qs, urlencode
        callback_received = threading.Event()
        auth_code_container = {}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                if 'code' in query_params:
                    auth_code_container['code'] = query_params['code'][0]
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<html><body><h1>Authorization successful!</h1><p>You can close this window and return to AudibleZenBot.</p></body></html>')
                    callback_received.set()
                elif 'error' in query_params:
                    auth_code_container['error'] = query_params['error'][0]
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<html><body><h1>Authorization failed</h1><p>You can close this window.</p></body></html>')
                    callback_received.set()
            def log_message(self, format, *args):
                pass

        server = HTTPServer(('localhost', 8887), CallbackHandler)
        server_thread = threading.Thread(target=lambda: server.handle_request())
        server_thread.daemon = True
        server_thread.start()

        print("[Trovo] Started local OAuth callback server on port 8887")

        TROVO_CLIENT_ID = "b239c1cc698e04e93a164df321d142b3"
        TROVO_REDIRECT_URI = "http://localhost:8887/callback"
        scopes = [
            "user_details_self",
            "channel_details_self",
            "send_message",
            "manage_channel",
            "manage_messages"
        ]
        scope_string = " ".join(scopes)
        state = secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id": TROVO_CLIENT_ID,
            "redirect_uri": TROVO_REDIRECT_URI,
            "scope": scope_string,
            "state": state
        }
        oauth_url = f"https://open-api.trovo.live/openplatform/oauth2/authorize?{urlencode(params)}"
        print(f"[Trovo] Starting OAuth with scopes: {scope_string}")
        print(f"[Trovo] Redirect URI: {TROVO_REDIRECT_URI}")
        webbrowser.open(oauth_url)
        print("[Trovo] Waiting for OAuth callback...")

        # Wait for callback (with timeout)
        if callback_received.wait(timeout=120):
            server.server_close()
            if 'code' in auth_code_container:
                auth_code = auth_code_container['code']
                print(f"[Trovo] Authorization code received: {auth_code[:20]}...")
                self.exchangeCodeForToken(account_type, auth_code)
        else:
            print("[Trovo] OAuth callback not received in time.")

    def append_status_message(self, message):
        """Append a date and time stamped message to the info_text log box."""
        from datetime import datetime
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.info_text.append(f"{timestamp} {message}")

    def onAccountAction(self, account_type):
        """Handle login/logout button click"""
        from PyQt6.QtWidgets import QMessageBox, QInputDialog
        print(f"[DEBUG] onAccountAction called for account_type: {account_type}")
        if account_type == "streamer":
            print(f"[DEBUG] streamer_login_btn text: {self.streamer_login_btn.text()}")
            display_label = self.streamer_display_name
            button = self.streamer_login_btn
            config_prefix = "streamer_"
            status_role = "Streamer"
        else:
            print(f"[DEBUG] bot_login_btn text: {self.bot_login_btn.text()}")
            display_label = self.bot_display_name
            button = self.bot_login_btn
            config_prefix = "bot_"
            status_role = "Bot"
        print(f"[DEBUG] Button text at start: {button.text()}")
        print(f"[DEBUG] Platform: {self.platform_id}, Account: {account_type}, Button: {button}")
        # Check current state
        if button.text() == "Login":
            print(f"[DEBUG] {account_type} login flow starting for platform {self.platform_id}")
            import threading
            from http.server import HTTPServer, BaseHTTPRequestHandler
            from urllib.parse import urlparse, parse_qs, urlencode
            callback_received = threading.Event()
            auth_code_container = {}

            class CallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed_url = urlparse(self.path)
                    query_params = parse_qs(parsed_url.query)
                    if 'code' in query_params:
                        auth_code_container['code'] = query_params['code'][0]
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Authorization successful!</h1><p>You can close this window and return to AudibleZenBot.</p></body></html>')
                        callback_received.set()
                    elif 'error' in query_params:
                        auth_code_container['error'] = query_params['error'][0]
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Authorization failed</h1><p>You can close this window.</p></body></html>')
                        callback_received.set()
                def log_message(self, format, *args):
                    pass

            server = HTTPServer(('localhost', 8888), CallbackHandler)
            server_thread = threading.Thread(target=lambda: server.handle_request())
            server_thread.daemon = True
            server_thread.start()

            print("[OAuth] Started local OAuth callback server on port 8888")

            if self.platform_id == 'twitch':
                # Twitch OAuth credentials and flow
                client_id = "h84tx3mvvpk9jyt8rv8p8utfzupz82"  # Replace with your Twitch client ID
                redirect_uri = "http://localhost:8888/callback"
                scopes = [
                    "user:read:email",
                    "chat:read",
                    "chat:edit",
                    "channel:read:subscriptions",
                    "channel:manage:broadcast",
                    # Additional scopes required for EventSub subscriptions
                    "channel:read:redemptions",
                    "bits:read",
                    "moderator:read:followers"
                ]
                scope_string = " ".join(scopes)
                state = secrets.token_urlsafe(16)
                params = {
                    "response_type": "code",
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "scope": scope_string,
                    "state": state,
                    "force_verify": "true"
                }
                oauth_url = f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"
                print(f"[Twitch] Starting OAuth with scopes: {scope_string}")
                print(f"[Twitch] Redirect URI: {redirect_uri}")
                import webbrowser
                webbrowser.open(oauth_url)
                print("[Twitch] Waiting for OAuth callback...")
            elif self.platform_id == 'kick':
                # ...existing Kick OAuth logic...
                client_id = "01KDPP3YN4SB6ZMSV6R6HM12C7"
                client_secret = "cf46287e05ebf1c68bc7a5fda41cb42da6015cd08c06ca788e6cbd3657a36e81"
                redirect_uri = "http://localhost:8890/callback"
                scopes = [
                    "user:read",
                    "channel:read",
                    "channel:write",
                    "chat:write",
                    "events:subscribe"
                ]
                scope_string = " ".join(scopes)
                state = secrets.token_urlsafe(16)
                if not hasattr(self, 'code_challenge'):
                    self.code_challenge = ''  # TODO: Implement PKCE if needed
                code_challenge = self.code_challenge
                params = {
                    "response_type": "code",
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "scope": scope_string,
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                    "state": state,
                    "prompt": "consent"
                }
                oauth_url = f"https://id.kick.com/oauth/authorize?{urlencode(params)}"
                print(f"[Kick] Starting OAuth with scopes: {scope_string}")
                print(f"[Kick] Redirect URI: {redirect_uri}")
                import webbrowser
                webbrowser.open(oauth_url)
                print("[Kick] Waiting for OAuth callback...")
            # Add other platforms as needed

            # Wait for callback (with timeout)
            if callback_received.wait(timeout=120):
                server.server_close()
                if 'code' in auth_code_container:
                    auth_code = auth_code_container['code']
                    print(f"[OAuth] Authorization code received: {auth_code[:20]}...")
                    # Trigger token exchange and UI update for Twitch
                    if self.platform_id == 'twitch':
                        print(f"[DEBUG] Calling exchangeCodeForToken for Twitch {account_type} login")
                        self.exchangeCodeForToken(account_type, auth_code)
        else:
                # Disconnect the account from the platform
            #if hasattr(self, 'parent') and hasattr(self.parent(), 'chat_manager'):
            #    self.parent().chat_manager.disconnectPlatform(self.platform_id)
            if self.chat_manager:
                self.chat_manager.disconnectPlatform(self.platform_id)
            # Optionally clear credentials from config
            from core.config import ConfigManager
            config = ConfigManager()
            # Use atomic set operations to avoid races when clearing credentials
            if account_type == "streamer":
                config.set_platform_config(self.platform_id, "streamer_logged_in", False)
                config.set_platform_config(self.platform_id, "streamer_token", "")
                config.set_platform_config(self.platform_id, "streamer_refresh_token", "")
                config.set_platform_config(self.platform_id, "streamer_user_id", "")
                self.streamer_display_name.setText("")
                self.streamer_login_btn.setText("Login")
                self.status_label.setText("Streamer account logged out.")
            else:
                config.set_platform_config(self.platform_id, "bot_logged_in", False)
                config.set_platform_config(self.platform_id, "bot_token", "")
                config.set_platform_config(self.platform_id, "bot_refresh_token", "")
                config.set_platform_config(self.platform_id, "bot_user_id", "")
                self.bot_display_name.setText("")
                self.bot_login_btn.setText("Login")
                self.status_label.setText("Bot account logged out.")

    def extractUsernameFromProfilePage(self, browser_dialog, account_type):
        """Extract username from the profile settings page"""
        print("[Kick] Extracting username from profile settings page...")
        
        js_code = """
        (function() {
            var username = '';
            var method = '';
            
            // Try to find username input field on profile settings page
            var usernameInput = document.querySelector('input[name="username"]') ||
                               document.querySelector('input[id="username"]') ||
                               document.querySelector('input[placeholder*="username" i]') ||
                               document.querySelector('input[type="text"][value]');
            
            if (usernameInput && usernameInput.value) {
                username = usernameInput.value;
                method = 'Found in username input field';
            }
            
            // Try to find it in any input field with username-like value
            if (!username) {
                var allInputs = document.querySelectorAll('input[type="text"]');
                for (var i = 0; i < allInputs.length; i++) {
                    var value = allInputs[i].value;
                    if (value && value.length > 2 && value.length < 30 && 
                        !value.includes('@') && !value.includes(' ')) {
                        username = value;
                        method = 'Found in text input: ' + (allInputs[i].name || allInputs[i].id || 'unnamed');
                        break;
                    }
                }
            }
            
            // Try to find in page state
            if (!username && window.__NUXT__ && window.__NUXT__.state) {
                var state = window.__NUXT__.state;
                if (state.auth && state.auth.user && state.auth.user.username) {
                    username = state.auth.user.username;
                    method = 'Found in __NUXT__.state.auth.user';
                }
            }
            
            return JSON.stringify({
                username: username,
                method: method,
                url: window.location.href,
                title: document.title
            });
        })();
        """
        
        browser_dialog.browser.page().runJavaScript(
            js_code,
            lambda result: self.onUsernameExtractedFromProfile(result, browser_dialog, account_type)
        )
    
    def onUsernameExtractedFromProfile(self, result_json, browser_dialog, account_type):
        """Handle username extracted from profile page"""
        import json
        
        try:
            result = json.loads(result_json)
            username = result.get('username', '')
            method = result.get('method', '')
            url = result.get('url', '')
            title = result.get('title', '')
            
            print(f"[Kick] Profile page URL: {url}")
            print(f"[Kick] Profile page title: {title}")
            
            if username:
                print(f"[Kick] ✓ Found username: {username}")
                print(f"[Kick] Extraction method: {method}")
                self._kick_extracted_username = username
            else:
                print(f"[Kick] ✗ Could not find username on profile page")
            
        except Exception as e:
            print(f"[Kick] Error extracting username from profile: {e}")

        # Now extract the token and complete authentication
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self.extractKickTokenAndUsername(browser_dialog, account_type))
    
    def onPageStateExtracted(self, state_json, browser_dialog, account_type):
        """Check extracted page state for username; log and abort if not found"""
        import json
        username = None
        if state_json:
            try:
                state = json.loads(state_json)
                print(f"[Kick] Examining page state structure...")
                if isinstance(state, dict):
                    print(f"[Kick] Root keys: {list(state.keys())}")
                    def find_username_in_obj(obj, path=""):
                        if isinstance(obj, dict):
                            if 'username' in obj or 'slug' in obj:
                                found = obj.get('username') or obj.get('slug')
                                if found and isinstance(found, str) and len(found) > 2:
                                    print(f"[Kick] Found username candidate at {path}: {found}")
                                    return found
                            for key in ['user', 'auth', 'currentUser', 'account', 'profile', 'channel']:
                                if key in obj and isinstance(obj[key], dict):
                                    result = find_username_in_obj(obj[key], f"{path}.{key}")
                                    if result:
                                        return result
                        return None
                    username = find_username_in_obj(state, "state")
            except Exception as e:
                print(f"[Kick] Error parsing page state: {e}")
        else:
            print("[Kick] No page state data returned from JavaScript")
        if username:
            print(f"[Kick] ✓ Found username in page state: {username}")
            from PyQt6.QtCore import QTimer
            self._kick_extracted_username = username
            QTimer.singleShot(500, lambda: self.extractKickTokenAndUsername(browser_dialog, account_type))
        else:
            print("[Kick] ERROR: Username could not be extracted from page state. Aborting Kick OAuth flow.")
            # Optionally, show a message box or emit a signal for UI feedback
            # from PyQt6.QtWidgets import QMessageBox
            # QMessageBox.warning(self, "Kick Login Failed", "Could not extract username from Kick profile page. Please try again.")
    
    def extractKickTokenAndUsername(self, browser_dialog, account_type):
        """Extract Kick bearer token and username from browser session using JavaScript"""
        # JavaScript to extract authentication token and username from page
        js_code = """
        (function() {
            // Try to get token from cookies
            var cookies = document.cookie.split(';');
            var token = null;
            
            // Look for authorization cookie - checking Kick-specific cookie names
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                // Kick-specific auth cookie names
                if (cookie.startsWith('kick_session=') || 
                    cookie.startsWith('session_token=') ||
                    cookie.startsWith('kick_token=') || 
                    cookie.startsWith('authorization=') ||
                    cookie.startsWith('auth_token=') ||
                    cookie.startsWith('session=')) {
                    token = cookie.split('=')[1];
                    break;
                }
            }
            
            // If not in cookies, try localStorage
            if (!token && window.localStorage) {
                token = localStorage.getItem('kick_session') ||
                       localStorage.getItem('session_token') ||
                       localStorage.getItem('authorization') || 
                       localStorage.getItem('token') ||
                       localStorage.getItem('auth_token') ||
                       localStorage.getItem('kick_token');
            }
            
            // If not in localStorage, try sessionStorage
            if (!token && window.sessionStorage) {
                token = sessionStorage.getItem('kick_session') ||
                       sessionStorage.getItem('session_token') ||
                       sessionStorage.getItem('authorization') ||
                       sessionStorage.getItem('token') ||
                       sessionStorage.getItem('auth_token') ||
                       sessionStorage.getItem('kick_token');
            }
            
            // Try to extract username from the page DOM
            var username = '';
            var debugInfo = [];
            
            // Blacklist of common paths that are NOT usernames
            var blacklist = [
                'dashboard', 'stream', 'login', 'achievements', 'settings', 'analytics',
                'chatbot', 'clips', 'videos', 'subscribers', 'followers', 'moderators',
                'chat', 'community', 'about', 'schedule', 'emotes', 'badges', 'rewards',
                'creator-dashboard', 'livestream', 'vods', 'categories', 'browse',
                'notifications', 'messages', 'inbox', 'profile', 'account', 'help',
                'support', 'legal', 'terms', 'privacy', 'guidelines', 'api', 'docs'
            ];
            
            // First, try to find username in stored user data (often in window object)
            try {
                if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.user) {
                    username = window.__INITIAL_STATE__.user.username || window.__INITIAL_STATE__.user.slug;
                    if (username) debugInfo.push('Found in __INITIAL_STATE__');
                }
            } catch(e) {}
            
            // Try other common window properties (Nuxt/Vue apps)
            if (!username) {
                try {
                    if (window.__NUXT__ && window.__NUXT__.state && window.__NUXT__.state.auth && window.__NUXT__.state.auth.user) {
                        username = window.__NUXT__.state.auth.user.username || window.__NUXT__.state.auth.user.slug;
                        if (username) debugInfo.push('Found in __NUXT__.state.auth.user');
                    }
                } catch(e) {}
            }
            
            // Try localStorage for user data (most reliable for logged-in user)
            if (!username && window.localStorage) {
                try {
                    var userDataKeys = ['user', 'userData', 'currentUser', 'auth', 'authUser', 'kick-user'];
                    for (var i = 0; i < userDataKeys.length; i++) {
                        var data = localStorage.getItem(userDataKeys[i]);
                        if (data) {
                            try {
                                var parsed = JSON.parse(data);
                                if (parsed.username || parsed.slug) {
                                    username = parsed.username || parsed.slug;
                                    debugInfo.push('Found in localStorage.' + userDataKeys[i]);
                                    break;
                                }
                            } catch(e) {}
                        }
                    }
                } catch(e) {}
            }
            
            // Try to get from page title (often shows "Username - Kick Dashboard")
            if (!username) {
                var titleMatch = document.title.match(/^([^-|]+)/);
                if (titleMatch && titleMatch[1]) {
                    var titleName = titleMatch[1].trim();
                    if (titleName && titleName.length > 0 && titleName.length < 30 && 
                        blacklist.indexOf(titleName.toLowerCase()) === -1 &&
                        titleName.toLowerCase() !== 'kick') {
                        username = titleName;
                        debugInfo.push('Found in page title: "' + document.title + '"');
                    }
                }
            }
            
            // Try to find in specific profile/user links (avoid navigation links)
            if (!username) {
                // Look for profile image or avatar links first (more likely to be username)
                var profileSelectors = [
                    'a[href^="/"] img[alt]',  // Profile images with alt text
                    'button[aria-label*="profile"] + a',
                    '[data-testid="user-profile"] a',
                    '[class*="profile"] a[href^="/"]',
                    '[class*="avatar"] a[href^="/"]'
                ];
                
                for (var i = 0; i < profileSelectors.length; i++) {
                    var elem = document.querySelector(profileSelectors[i]);
                    if (elem) {
                        var href = elem.getAttribute('href') || '';
                        if (href && href.match(/^\\/[a-zA-Z0-9_-]+$/)) {
                          var possibleUsername = href.substring(1);
                          if (possibleUsername && blacklist.indexOf(possibleUsername.toLowerCase()) === -1 &&
                              possibleUsername.length > 0 && possibleUsername.length < 30) {
                            username = possibleUsername;
                            debugInfo.push('Found in profile link: ' + href);
                            break;
                          }
                        }
                    }
                }
            }
            
            // Last resort: scan links but be very selective
            if (!username) {
                var allLinks = document.querySelectorAll('a[href^="/"]');
                var candidates = {};
                
                for (var i = 0; i < allLinks.length; i++) {
                    var href = allLinks[i].getAttribute('href') || '';
                    
                    // Only consider simple paths like /username (not /path/subpath)
                    if (href.match(/^\\/[a-zA-Z0-9_-]+$/)) {
                        var possibleUsername = href.substring(1);
                        if (possibleUsername && blacklist.indexOf(possibleUsername.toLowerCase()) === -1 &&
                            possibleUsername.length > 2 && possibleUsername.length < 30) {
                            // Count occurrences to find most common (likely the logged-in user)
                            candidates[possibleUsername] = (candidates[possibleUsername] || 0) + 1;
                        }
                    }
                }
                
                // Use the most frequent username candidate (appears multiple times = profile links)
                var maxCount = 0;
                for (var candidate in candidates) {
                    if (candidates[candidate] > maxCount && candidates[candidate] >= 2) {
                        username = candidate;
                        maxCount = candidates[candidate];
                        debugInfo.push('Found frequent link: /' + candidate + ' (appeared ' + maxCount + ' times)');
                    }
                }
            }
            
            return JSON.stringify({token: token || '', username: username || '', debug: debugInfo.join('; ')});
        })();
        """
        
        # Execute JavaScript to extract token and username
        browser_dialog.browser.page().runJavaScript(
            js_code,
            None  # Callback removed; token/username extraction logic no longer needed
        )
    
    # REMOVED: tryExtractUsernameFromAPI fallback method. Username extraction now only uses primary methods. If extraction fails, logs are written and flow aborts.
    
    # REMOVED: onComprehensiveExtractionComplete fallback handler. Username extraction now only uses primary methods. If extraction fails, logs are written and flow aborts.
    
    # REMOVED: onKickTokenAndUsernameExtracted method and logic. No longer needed.
    
    # REMOVED: dlive OAuth flow. DLive does not use standard OAuth; users must provide tokens manually. 
    
    
    
    def showManualTokenEntry(self, account_type, username, platform_name):
        """Show dialog for manual token entry (for platforms without OAuth)"""
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        
        token, ok = QInputDialog.getText(
            self,
            f"{platform_name} Token",
            f"Paste your {platform_name} token/API key:",
            QLineEdit.EchoMode.Password
        )
        
        if ok and token.strip():
            # For manual token entry, create minimal user info and save directly
            user_info = {
                'username': f'{platform_name} User',
                'display_name': f'{platform_name} User',
                'user_id': ''
            }
            self.onOAuthSuccess(account_type, user_info, token.strip(), '')
        else:
            self.onOAuthFailed(account_type, "No token provided")
    
    def exchangeCodeForToken(self, account_type, code):
        """Exchange authorization code for access token"""
        import requests
        from core.config import ConfigManager
        try:
            if self.platform_id == 'trovo':
                TROVO_CLIENT_ID = "b239c1cc698e04e93a164df321d142b3"
                TROVO_CLIENT_SECRET = "a6a9471aed462e984c85feb04e39882e"
                TROVO_TOKEN_URL = "https://open-api.trovo.live/openplatform/exchangetoken"
                TROVO_REDIRECT_URI = getattr(self, '_trovo_redirect_uri', "https://mistilled-declan-unendable.ngrok-free.dev/callback")
                headers = {
                    "Accept": "application/json",
                    "client-id": TROVO_CLIENT_ID,
                    "Content-Type": "application/json"
                }
                data = {
                    "client_secret": TROVO_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": TROVO_REDIRECT_URI
                }
                response = requests.post(TROVO_TOKEN_URL, headers=headers, json=data)
                response.raise_for_status()
                token_data = response.json()
                access_token = token_data.get('access_token')
                refresh_token = token_data.get('refresh_token', '')
                if access_token:
                    user_info = self.fetchUserInfo(access_token)
                    self.onOAuthSuccess(account_type, user_info, access_token, refresh_token)
                    # if hasattr(self, '_cleanup_trovo_ngrok'):
                    #     self._cleanup_trovo_ngrok()
                else:
                    self.onOAuthFailed(account_type, "No access token in response")
                    # if hasattr(self, '_cleanup_trovo_ngrok'):
                    #     self._cleanup_trovo_ngrok()
            elif self.platform_id == 'youtube':
                YOUTUBE_CLIENT_ID = "44621719812-l23h29dbhqjfm6ln6buoojenmiocv1cp.apps.googleusercontent.com"
                YOUTUBE_CLIENT_SECRET = "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"
                YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
                YOUTUBE_REDIRECT_URI = "http://localhost:8880/callback"
                data = {
                    "code": code,
                    "client_id": YOUTUBE_CLIENT_ID,
                    "client_secret": YOUTUBE_CLIENT_SECRET,
                    "redirect_uri": YOUTUBE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
                response = requests.post(YOUTUBE_TOKEN_URL, data=data)
                response.raise_for_status()
                token_data = response.json()
                access_token = token_data.get('access_token')
                refresh_token = token_data.get('refresh_token', '')
                if access_token:
                    user_info = self.fetchUserInfo(access_token)
                    self.onOAuthSuccess(account_type, user_info, access_token, refresh_token)
                else:
                    self.onOAuthFailed(account_type, "No access token in response")
            elif self.platform_id == 'twitch':
                config = ConfigManager()
                twitch_config = config.get_platform_config('twitch')
                client_id = twitch_config.get('client_id', 'h84tx3mvvpk9jyt8rv8p8utfzupz82') if twitch_config else 'h84tx3mvvpk9jyt8rv8p8utfzupz82'
                client_secret = twitch_config.get('client_secret', '') if twitch_config else ''
                if not client_secret:
                    self.onOAuthFailed(account_type, "Twitch client_secret not configured in config.json. Add it under twitch > client_secret")
                    return
                TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
                TWITCH_REDIRECT_URI = "http://localhost:8888/callback"
                data = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": TWITCH_REDIRECT_URI
                }
                response = requests.post(TWITCH_TOKEN_URL, data=data, timeout=10)
                response.raise_for_status()
                token_data = response.json()
                access_token = token_data.get('access_token')
                refresh_token = token_data.get('refresh_token', '')
                if access_token:
                    user_info = self.fetchUserInfo(access_token)
                    self.onOAuthSuccess(account_type, user_info, access_token, refresh_token)
                else:
                    self.onOAuthFailed(account_type, "No access token in response")
            else:
                self.onOAuthFailed(account_type, f"Token exchange not implemented for {self.platform_id}")
        except Exception as e:
            self.onOAuthFailed(account_type, f"Token exchange error: {str(e)}")
        
    def onOAuthSuccess(self, account_type, user_info, token, refresh_token=''):
        """Handle successful OAuth authentication"""
        from core.config import ConfigManager
        import json
        import time
        config_prefix = "streamer_" if account_type == "streamer" else "bot_"
        # Extract username and display name from user_info
        username = user_info.get('username', 'Unknown')
        display_name = user_info.get('display_name', username)
        user_id = user_info.get('user_id', '')
        cookies = user_info.get('cookies', {})  # Get cookies if provided (Kick)
        # Save to config - IMPORTANT: Use a single config instance and reload to avoid race conditions
        config = ConfigManager()
        # Persist fields atomically via ConfigManager helpers to avoid races.
        config.set_platform_config(self.platform_id, f"{config_prefix}username", username)
        config.set_platform_config(self.platform_id, f"{config_prefix}display_name", display_name)
        config.set_platform_config(self.platform_id, f"{config_prefix}token", token)
        config.set_platform_config(self.platform_id, f"{config_prefix}refresh_token", refresh_token)
        config.set_platform_config(self.platform_id, f"{config_prefix}token_timestamp", int(time.time()))
        config.set_platform_config(self.platform_id, f"{config_prefix}logged_in", True)
        # Save user_id for platforms that need it (like Trovo for sending messages)
        if user_id:
            config.set_platform_config(self.platform_id, f"{config_prefix}user_id", user_id)
            print(f"[ConnectionsPage] DEBUG: Set {config_prefix}user_id = {user_id} in platform_config dict")
            pc = config.get_platform_config(self.platform_id)
            print(f"[ConnectionsPage] DEBUG: platform_config keys before save: {list(pc.keys())}")
        # Save cookies for platforms that need them (like Kick for v2 API)
        if cookies:
            config.set_platform_config(self.platform_id, f"{config_prefix}cookies", json.dumps(cookies))
            print(f"[ConnectionsPage] DEBUG: Stored {len(cookies) if hasattr(cookies, '__len__') else 'unknown'} cookies for {config_prefix}")

        print(f"[ConnectionsPage] Saved {account_type} login to config: {config_prefix}logged_in = True")
        print(f"[ConnectionsPage] Config saved: {config_prefix}username = {username}")
        print(f"[ConnectionsPage] Config saved: {config_prefix}display_name = {display_name}")
        print(f"[ConnectionsPage] Config saved: {config_prefix}user_id = {user_id}")
        print(f"[ConnectionsPage] Config saved: {config_prefix}token exists = {bool(token)}")
        print(f"[ConnectionsPage] Config file path: {self.config.config_file}")

        # Wait a moment for file system to flush
        import time as time_module
        time_module.sleep(0.1)

        # Verify it was saved by creating a NEW config manager instance and reloading
        verify_config = ConfigManager()
        verify_data = verify_config.load()
        verify_platform = verify_data.get('platforms', {}).get(self.platform_id, {})
        saved_value = verify_platform.get(f"{config_prefix}logged_in", False)
        print(f"[ConnectionsPage] Verified {config_prefix}logged_in in config: {saved_value}")
        saved_username = verify_platform.get(f"{config_prefix}username", '')
        print(f"[ConnectionsPage] Verified {config_prefix}username in config: {saved_username}")
        saved_user_id = verify_platform.get(f"{config_prefix}user_id", '')
        print(f"[ConnectionsPage] Verified {config_prefix}user_id in config: {saved_user_id}")

        if not saved_value or not saved_username:
            print(f"[ConnectionsPage] WARNING: Config verification failed! logged_in={saved_value}, username={saved_username}")
            print(f"[ConnectionsPage] Attempting to save again...")
            # Try saving again using atomic set calls
            config.set_platform_config(self.platform_id, f"{config_prefix}logged_in", True)
            config.set_platform_config(self.platform_id, f"{config_prefix}username", username)
            time_module.sleep(0.1)
            print(f"[ConnectionsPage] Second save attempt completed")
        # Update UI
        if account_type == "streamer":
            print(f"[DEBUG] Setting streamer_display_name to {display_name}")
            self.streamer_display_name.setText(display_name)
            print(f"[DEBUG] Setting streamer_login_btn text to Logout")
            self.streamer_login_btn.setText("Logout")
            self.streamer_login_btn.setEnabled(True)
            print(f"[DEBUG] streamer_login_btn text after set: {self.streamer_login_btn.text()}")
            if hasattr(self, 'info_text'):
                self.append_status_message(f"[{account_type.title()}] ✓ Successfully logged in as {display_name} (@{username})")
                self.append_status_message(f"[{account_type.title()}] Connecting to {getattr(self, 'platform_name', self.platform_id)} chat...")
            if hasattr(self, 'connect_requested'):
                self.connect_requested.emit(self.platform_id, username, token)
        elif account_type == "bot":
            print(f"[DEBUG] Setting bot_display_name to {display_name}")
            self.bot_display_name.setText(display_name)
            print(f"[DEBUG] Setting bot_login_btn text to Logout")
            self.bot_login_btn.setText("Logout")
            self.bot_login_btn.setEnabled(True)
            print(f"[DEBUG] bot_login_btn text after set: {self.bot_login_btn.text()}")
            if hasattr(self, 'info_text'):
                self.append_status_message(f"[{account_type.title()}] ✓ Successfully logged in as {display_name} (@{username})")
                self.append_status_message(f"[{account_type.title()}] Connecting bot to {getattr(self, 'platform_name', self.platform_id)}...")
            # Get chat_manager from parent window and connect bot
            # main_window = self.parent()
            # for _ in range(3):
            #     if hasattr(main_window, 'parent'):
            #         main_window = main_window.parent()
            # if hasattr(main_window, 'chat_manager'):
            #     success = main_window.chat_manager.connectBotAccount(self.platform_id, username, token, refresh_token)
            #     if hasattr(self, 'info_text'):
            #         if success:
            #             self.info_text.append(f"[{account_type.title()}] ✓ Bot connected to {getattr(self, 'platform_name', self.platform_id)}")
            #         else:
            #             self.info_text.append(f"[{account_type.title()}] ⚠ Failed to connect bot")
    
    def onOAuthFailed(self, account_type, error):
        """Handle failed OAuth authentication"""
        # Re-enable button
        if account_type == "streamer":
            self.streamer_login_btn.setText("Login")
            self.streamer_login_btn.setEnabled(True)
        else:
            self.bot_login_btn.setText("Login")
            self.bot_login_btn.setEnabled(True)
        if hasattr(self, 'info_text'):
            self.append_status_message(f"[{account_type.title()}] ✗ Authentication failed: {error}")
    
    def fetchUserInfo(self, token):
        """Fetch user information from platform API"""
        import requests
        try:
            if self.platform_id == 'trovo':
                TROVO_CLIENT_ID = "b239c1cc698e04e93a164df321d142b3"
                url = "https://open-api.trovo.live/openplatform/getuserinfo"
                headers = {
                    "Accept": "application/json",
                    "client-id": TROVO_CLIENT_ID,
                    "Authorization": f"OAuth {token}"
                }
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return {
                    'username': data.get('userName', data.get('username', 'Unknown')),
                    'display_name': data.get('nickName', data.get('nickname', data.get('userName', data.get('username', 'Unknown')))),
                    'user_id': str(data.get('userId', data.get('user_id', data.get('channelId', ''))))
                }
            elif self.platform_id == 'youtube':
                url = "https://www.googleapis.com/oauth2/v2/userinfo"
                headers = {
                    "Authorization": f"Bearer {token}"
                }
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                user = response.json()
                name = user.get('name', 'YouTube User')
                email = user.get('email', '')
                # Try to get channel info for a better display name
                try:
                    channel_url = "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true"
                    channel_response = requests.get(channel_url, headers=headers)
                    if channel_response.ok:
                        channel_data = channel_response.json()
                        if channel_data.get('items'):
                            channel = channel_data['items'][0]
                            snippet = channel.get('snippet', {})
                            name = snippet.get('title', name)
                except Exception:
                    pass  # Use the basic name if channel fetch fails
                return {
                    'username': email.split('@')[0] if email else name,
                    'display_name': name,
                    'user_id': user.get('id', '')
                }
            elif self.platform_id == 'twitch':
                from core.config import ConfigManager
                config = ConfigManager()
                twitch_config = config.get_platform_config('twitch')
                client_id = twitch_config.get('client_id', 'h84tx3mvvpk9jyt8rv8p8utfzupz82') if twitch_config else 'h84tx3mvvpk9jyt8rv8p8utfzupz82'
                url = "https://api.twitch.tv/helix/users"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Client-Id": client_id
                }
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                if data.get('data'):
                    user = data['data'][0]
                    user_info = {
                        'username': user.get('login', 'Unknown'),
                        'display_name': user.get('display_name', user.get('login', 'Unknown')),
                        'user_id': user.get('id', '')
                    }
                    return user_info
                else:
                    return {'username': 'Unknown', 'display_name': 'Unknown', 'user_id': ''}
            elif self.platform_id == 'kick':
                url = "https://api.kick.com/v1/user"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                user = response.json()
                return {
                    'username': user.get('username', 'Unknown'),
                    'display_name': user.get('display_name', user.get('username', 'Unknown')),
                    'user_id': str(user.get('id', ''))
                }
            elif self.platform_id == 'dlive':
                # DLive uses GraphQL - for now return minimal info
                return {
                    'username': 'DLive User',
                    'display_name': 'DLive User',
                    'user_id': ''
                }
            else:
                # Platform not implemented yet
                return {'username': 'Unknown', 'display_name': 'Unknown', 'user_id': ''}
        except Exception as e:
            # Return minimal info on error
            print(f"[OAuth] Error fetching user info: {str(e)}")
            return {'username': 'Unknown', 'display_name': 'Unknown', 'user_id': ''}
    
    def refreshToken(self, account_type):
        """Refresh OAuth token if it has expired or is about to expire"""
        import requests
        import time
        from core.config import ConfigManager

        config = ConfigManager()
        platform_config = config.get_platform_config(self.platform_id)

        if not platform_config:
            print(f"[OAuth] No config found for {self.platform_id}")
            return None

        config_prefix = "streamer_" if account_type == "streamer" else "bot_"
        refresh_token = platform_config.get(f"{config_prefix}refresh_token", '')

        if not refresh_token:
            print(f"[OAuth] No refresh token available for {self.platform_id} {account_type}")
            return None

        try:
            if self.platform_id == 'trovo':
                TROVO_CLIENT_ID = "b239c1cc698e04e93a164df321d142b3"
                TROVO_CLIENT_SECRET = "a6a9471aed462e984c85feb04e39882e"
                TROVO_TOKEN_URL = "https://open-api.trovo.live/openplatform/refreshtoken"
                headers = {
                    "Accept": "application/json",
                    "client-id": TROVO_CLIENT_ID,
                    "Content-Type": "application/json"
                }
                data = {
                    "client_secret": TROVO_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
                response = requests.post(TROVO_TOKEN_URL, headers=headers, json=data)
                response.raise_for_status()
                token_data = response.json()
                new_access_token = token_data.get('access_token')
                new_refresh_token = token_data.get('refresh_token', refresh_token)  # Use old if not provided
                if new_access_token:
                    # Save updated tokens using atomic helper (each call saves under lock)
                    config.set_platform_config(self.platform_id, f"{config_prefix}token", new_access_token)
                    config.set_platform_config(self.platform_id, f"{config_prefix}refresh_token", new_refresh_token)
                    config.set_platform_config(self.platform_id, f"{config_prefix}token_timestamp", int(time.time()))
                    print(f"[OAuth] Token refreshed successfully for {self.platform_id} {account_type}")
                    return new_access_token
                else:
                    print(f"[OAuth] No access token in refresh response")
                    return None
            elif self.platform_id == 'youtube':
                YOUTUBE_CLIENT_ID = "44621719812-l23h29dbhqjfm6ln6buoojenmiocv1cp.apps.googleusercontent.com"
                YOUTUBE_CLIENT_SECRET = "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"
                YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
                data = {
                    "client_id": YOUTUBE_CLIENT_ID,
                    "client_secret": YOUTUBE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
                response = requests.post(YOUTUBE_TOKEN_URL, data=data)
                response.raise_for_status()
                token_data = response.json()
                new_access_token = token_data.get('access_token')
                new_refresh_token = token_data.get('refresh_token', refresh_token)  # Use old if not provided
                if new_access_token:
                    # Save updated tokens using atomic helper
                    config.set_platform_config(self.platform_id, f"{config_prefix}token", new_access_token)
                    config.set_platform_config(self.platform_id, f"{config_prefix}refresh_token", new_refresh_token)
                    config.set_platform_config(self.platform_id, f"{config_prefix}token_timestamp", int(time.time()))
                    print(f"[OAuth] Token refreshed successfully for {self.platform_id} {account_type}")
                    return new_access_token
                else:
                    print(f"[OAuth] No access token in refresh response")
                    return None
            elif self.platform_id == 'twitch':
                twitch_config = config.get_platform_config('twitch')
                client_id = twitch_config.get('client_id', 'h84tx3mvvpk9jyt8rv8p8utfzupz82') if twitch_config else 'h84tx3mvvpk9jyt8rv8p8utfzupz82'
                client_secret = twitch_config.get('client_secret', '') if twitch_config else ''
                if not client_secret:
                    print(f"[OAuth] Twitch client_secret not configured, cannot refresh token")
                    return None
                TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
                data = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
                print(f"[DEBUG] Attempting Twitch token refresh with data: {data}")
                try:
                    response = requests.post(TWITCH_TOKEN_URL, data=data, timeout=10)
                    print(f"[DEBUG] Twitch token refresh response status: {response.status_code}")
                    print(f"[DEBUG] Twitch token refresh response body: {response.text}")
                    response.raise_for_status()
                    token_data = response.json()
                except Exception as e:
                    print(f"[ERROR] Twitch token refresh failed: {str(e)}")
                    print(f"[ERROR] Twitch token refresh response: {getattr(e, 'response', None)}")
                    print(f"[ERROR] Twitch token refresh guidance: This may be due to an expired or revoked refresh token. Prompting user to re-authenticate.")
                    return None
                new_access_token = token_data.get('access_token')
                new_refresh_token = token_data.get('refresh_token', refresh_token)  # Use old if not provided
                if new_access_token:
                    # Save updated tokens using atomic helper
                    config.set_platform_config(self.platform_id, f"{config_prefix}token", new_access_token)
                    config.set_platform_config(self.platform_id, f"{config_prefix}refresh_token", new_refresh_token)
                    config.set_platform_config(self.platform_id, f"{config_prefix}token_timestamp", int(time.time()))
                    print(f"[OAuth] Token refreshed successfully for {self.platform_id} {account_type}")
                    return new_access_token
                else:
                    print(f"[ERROR] No access token in Twitch refresh response. Full response: {token_data}")
                    print(f"[ERROR] Twitch token refresh guidance: This may be due to an invalid refresh token. Prompting user to re-authenticate.")
                    return None
            else:
                print(f"[OAuth] Token refresh not implemented for {self.platform_id}")
                return None
        except Exception as e:
            print(f"[OAuth] Error refreshing token: {str(e)}")
            return None
    
    def getValidToken(self, account_type):
        """Get a valid token, refreshing if necessary (tokens typically expire after 1 hour)"""
        import time
        from core.config import ConfigManager

        config = ConfigManager()
        platform_config = config.get_platform_config(self.platform_id)

        if not platform_config:
            return None

        config_prefix = "streamer_" if account_type == "streamer" else "bot_"
        current_token = platform_config.get(f"{config_prefix}token", '')
        token_timestamp = platform_config.get(f"{config_prefix}token_timestamp", 0)

        # Check if token is older than 50 minutes (3000 seconds) - refresh before it expires
        if current_token and (time.time() - token_timestamp > 3000):
            print(f"[OAuth] Token may be expired, attempting refresh...")
            refreshed_token = self.refreshToken(account_type)
            if refreshed_token:
                return refreshed_token

        return current_token if current_token else None
    
    def loadAccountStates(self):
        """Load saved account states from config"""
        from core.config import ConfigManager
        config = ConfigManager()
        platform_config = config.get_platform_config(self.platform_id)

        if not platform_config:
            print(f"[{self.platform_id}] No config found in loadAccountStates")
            return

        # Debug: Show what's in the config
        print(f"[{self.platform_id}] loadAccountStates: streamer_logged_in={platform_config.get('streamer_logged_in', False)}, has_username={bool(platform_config.get('streamer_username', ''))}, has_token={bool(platform_config.get('streamer_token', ''))}")

        # Load streamer account
        if platform_config.get('streamer_logged_in', False):
            display_name = platform_config.get('streamer_display_name', '')
            username = platform_config.get('streamer_username', '')
            token = platform_config.get('streamer_token', '')
            # Use display name if available, otherwise fallback to username
            if display_name:
                self.streamer_display_name.setText(display_name)
            elif username:
                self.streamer_display_name.setText(username)
            if display_name or username:
                self.status_label.setText(f"Streamer logged in: {display_name or username}")
                self.streamer_login_btn.setText("Logout")
                self.streamer_login_btn.setEnabled(True)
                # Auto-connect to platform with streamer account
                if username and token:
                    if hasattr(self, 'append_status_message'):
                        self.append_status_message(f"[Streamer] Auto-connecting to {self.platform_name} chat...")
                    self.connect_requested.emit(self.platform_id, username, token)
                else:
                    print(f"[{self.platform_id}] Streamer logged in but missing username={bool(username)} or token={bool(token)}")
        else:
            self.streamer_display_name.setText("")

        # Load bot account
        if platform_config.get('bot_logged_in', False):
            display_name = platform_config.get('bot_display_name', '')
            username = platform_config.get('bot_username', '')
            # Set the bot account username field in the UI
            if display_name:
                self.bot_display_name.setText(display_name)
                self.status_label.setText(f"Bot logged in: {display_name}")
            elif username:
                self.bot_display_name.setText(username)
                self.status_label.setText(f"Bot logged in: {username}")
        # Load disable state for this platform (persist across runs)
        try:
            disabled = platform_config.get('disabled', False)
            # Reflect in UI without triggering handler
            try:
                self.disable_checkbox.blockSignals(True)
                self.disable_checkbox.setChecked(bool(disabled))
                # Ensure the knob offset matches the checked state so visuals are correct on startup
                try:
                    offset_val = self.disable_checkbox._get_offset_for_state(bool(disabled))
                    # Use the property setter for the offset
                    try:
                        self.disable_checkbox.set_offset(float(offset_val))
                    except Exception:
                        try:
                            self.disable_checkbox.offset = float(offset_val)
                        except Exception:
                            pass
                    self.disable_checkbox.update()
                except Exception:
                    pass
            finally:
                self.disable_checkbox.blockSignals(False)
            # Do not emit `disable_changed` during initialization to avoid
            # triggering duplicate connect/disconnect cycles. The toggle
            # handler `_on_disable_toggled` will emit when user changes it.
        except Exception:
            pass
    
    def setConfig(self, config):
        """Set the config manager for saving state"""
        self.config = config
    
    def _on_disable_toggled(self, state):
        """Handle toggle and persist disabled state to config, then notify listeners"""
        is_disabled = False
        try:
            is_disabled = bool(self.disable_checkbox.isChecked())
        except Exception:
            is_disabled = False
        try:
            if hasattr(self, 'config') and self.config:
                # Save under platform config key 'disabled'
                try:
                    # set_platform_config is already atomic and saves; no extra save() needed
                    self.config.set_platform_config(self.platform_id, 'disabled', is_disabled)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if hasattr(self, 'append_status_message'):
                self.append_status_message(f"[Platform] {'Disabled' if is_disabled else 'Enabled'} platform: {self.platform_name}")
        except Exception:
            pass
        try:
            self.disable_changed.emit(self.platform_id, is_disabled)
        except Exception:
            pass
    
    def setConnectionState(self, connected):
        """Stub for legacy compatibility - now handled by account-specific methods"""
        pass

    def run_on_main_thread(self, func, *args, **kwargs):
        try:
            if hasattr(self, '_mt_executor') and self._mt_executor:
                self._mt_executor.run.emit(func, args, kwargs)
                return
        except Exception as e:
            import traceback
            print(f"[run_on_main_thread] emit failed: {e}")
            traceback.print_exc()
        # Fallback to QTimer if executor not available
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: func(*args, **kwargs))

class ConnectionsPage(QWidget):
    """Connections page for managing all platform connections"""

    def apply_global_settings(self):
        """Apply global settings to all platforms (migrated from AutomationPage)."""
        # global_title = self.global_title_input.text()
        # global_notif = self.global_notification_input.toPlainText()
        platforms = ['Twitch', 'YouTube', 'Kick', 'Trovo', 'DLive']
        for platform in platforms:
            widget = self.platform_widgets.get(platform.lower())
            if widget:
                pass
        print("[ConnectionsPage] Applied global settings to all platforms")
    """Connections page for managing all platform connections"""
    
    def __init__(self, chat_manager, config, parent=None):
        super().__init__(parent)
        self.chat_manager = chat_manager
        self.config = config
        self.platform_widgets = {}
        self.oauth_handler = OAuthHandler()
        self._ngrok_manager = None  # Use private variable with property
        self.trovo_ngrok_tunnel = None  # Track Trovo tunnel for cleanup
        # Connect OAuth signals
        self.oauth_handler.auth_completed.connect(self.onAuthCompleted)
        self.oauth_handler.auth_failed.connect(self.onAuthFailed)
        # Connect chat manager signals
        if self.chat_manager:
            self.chat_manager.bot_connection_changed.connect(self.onBotConnectionChanged)
            self.chat_manager.streamer_connection_changed.connect(self.onStreamerConnectionChanged)
        self.initUI()
    
    @property
    def ngrok_manager(self):
        """Get ngrok manager"""
        return self._ngrok_manager
    
    @ngrok_manager.setter
    def ngrok_manager(self, value):
        """Set ngrok manager and propagate to all platform widgets"""
        self._ngrok_manager = value
        # Update all existing platform widgets
        for widget in self.platform_widgets.values():
            widget.ngrok_manager = value;
        
    
    def onBotConnectionChanged(self, platform_id, connected, username):
        """Handle bot connection state change"""
        print(f"[ConnectionsPage] Bot connection changed: {platform_id}, connected={connected}, username={username}")
        widget = self.platform_widgets.get(platform_id)
        if widget:
            if connected:
                # Update UI to show bot as logged in
                from core.config import ConfigManager
                config = ConfigManager()
                bot_display_name = config.get_platform_config(platform_id).get('bot_display_name', '')
                # If display name isn't in config yet, use the username from the signal
                if not bot_display_name and username:
                    bot_display_name = username
                widget.bot_display_name.setText(bot_display_name)
                widget.bot_login_btn.setText("Logout")
                print(f"[ConnectionsPage] Updated bot UI for {platform_id}: {bot_display_name}")
            else:
                # Update UI to show bot as logged out
                widget.bot_display_name.setText("")
                widget.bot_login_btn.setText("Login")
                print(f"[ConnectionsPage] Cleared bot UI for {platform_id}")
    
    def onStreamerConnectionChanged(self, platform_id, connected, username):
        """Handle streamer connection state change"""
        print(f"[ConnectionsPage] Streamer connection changed: {platform_id}, connected={connected}, username={username}")
        widget = self.platform_widgets.get(platform_id)
        if widget:
            if connected:
                # Update UI to show streamer as logged in
                from core.config import ConfigManager
                config = ConfigManager()
                streamer_display_name = config.get_platform_config(platform_id).get('streamer_display_name', '')
                # If display name isn't in config yet, use the username from the signal
                if not streamer_display_name and username:
                    streamer_display_name = username
                widget.streamer_display_name.setText(streamer_display_name)
                widget.streamer_login_btn.setText("Logout")
                print(f"[ConnectionsPage] Updated streamer UI for {platform_id}: {streamer_display_name}")
            else:
                # Update UI to show streamer as logged out
                widget.streamer_display_name.setText("")
                widget.streamer_login_btn.setText("Login")
                print(f"[ConnectionsPage] Cleared streamer UI for {platform_id}")

    def initUI(self):
        """Initialize the connections page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("Platform Connections")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff; padding: 10px;")
        layout.addWidget(title)

        # Description
        desc = QLabel("Connect to streaming platforms to start receiving chat messages.")
        desc.setStyleSheet("color: #cccccc; font-size: 12px; padding: 0 10px 10px 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Tabbed widget for platforms
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 10px 20px;
                margin-right: 2px;
                border: 1px solid #3d3d3d;
            }
            QTabBar::tab:selected {
                background-color: #4a90e2;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
        """)

        # No global stream info tab, just platform tabs

        # Create platform tabs (as before)
        platforms = [
            ("Twitch", "twitch"),
            ("YouTube", "youtube"),
            ("Trovo", "trovo"),
            ("Kick", "kick"),
            ("DLive", "dlive"),
        ]
        for platform_name, platform_id in platforms:
            widget = PlatformConnectionWidget(platform_name, platform_id, self.chat_manager)
            # Provide config to the widget so it can read/save settings
            try:
                widget.setConfig(self.config)
            except Exception:
                pass
            widget.connect_requested.connect(self.onPlatformConnect)
            # Notify page when disable state changes so chat_manager can be updated
            try:
                widget.disable_changed.connect(self.onDisableChanged)
            except Exception:
                pass
            # widget.disconnect_requested.connect(self.onPlatformDisconnect)
            # widget.auth_requested.connect(self.onAuthRequested)
            # widget.disable_changed.connect(self.onDisableChanged)
            widget.ngrok_manager = self.ngrok_manager
            widget.loadAccountStates()
            self.tabs.addTab(widget, platform_name)
            self.platform_widgets[platform_id] = widget
        layout.addWidget(self.tabs)
    
    def onAuthRequested(self, platform_id: str):
        """Handle OAuth authentication request - legacy stub"""
        pass
    
    def onAuthCompleted(self, platform: str, token: str):
        """Handle successful OAuth authentication - legacy stub"""
        pass
    
    def onAuthFailed(self, platform: str, error: str):
        """Handle failed OAuth authentication - legacy stub"""
        pass
    
    def onPlatformConnect(self, platform_id, username, token=""):
        """Handle platform connection request - connects using streamer account"""
        from core.config import ConfigManager
        
        # Get streamer account credentials
        config = ConfigManager();
        platform_config = config.get_platform_config(platform_id);
        
        if not platform_config:
            print(f"[ConnectionsPage] No config found for {platform_id}")
            return
        # Use streamer account credentials for reading chat
        streamer_username = platform_config.get('streamer_username', username)
        streamer_token = platform_config.get('streamer_token', token)
        if not streamer_username:
            print(f"[ConnectionsPage] No streamer username configured for {platform_id}")
            return
        print(f"[ConnectionsPage] Connecting to {platform_id} as streamer: {streamer_username}")
        # Connect to the platform using chat_manager
        if self.chat_manager:
            self.chat_manager.connectPlatform(platform_id, streamer_username, streamer_token)
    
    def onPlatformDisconnect(self, platform_id):
        """Handle platform disconnection request"""
        print(f"[ConnectionsPage] Disconnecting from {platform_id}")
        if self.chat_manager:
            self.chat_manager.disconnectPlatform(platform_id)
    
    def autoConnect(self, platform_id, username, token):
        """Auto-connect to a platform from saved state - legacy stub"""
        pass
    
    def saveAllConnectionStates(self):
        """Save connection states for all platforms - handled by individual widgets now"""
        # Cleanup Trovo ngrok in all widgets if still running
        for widget in self.platform_widgets.values():
            if hasattr(widget, '_cleanup_trovo_ngrok'):
                widget._cleanup_trovo_ngrok()
    
    def onDisableChanged(self, platform_id, is_disabled):
        """Han
dle disable state change from platform widget"""
        if self.chat_manager:
            self.chat_manager.disablePlatform(platform_id, is_disabled)
