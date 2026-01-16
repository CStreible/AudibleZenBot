"""
Checkpoint copy of ui/connections_page.py
Created: 2026-01-14 00:01
This is a full snapshot of the current file for checkpointing purposes.
"""

# --- BEGIN FILE SNAPSHOT -------------------------------------------------

"""
Connections Page - Manage platform connections and authentication
"""

from logging import config
from PyQt6.QtWidgets import (
	QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
	QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox,
	QTextEdit, QFrame, QDialog, QProgressBar, QListWidget
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
		from ui.automation_page import ToggleSwitch
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

		# Move Disable platform checkbox to the top
		# Add label next to toggle switch
		disable_row = QHBoxLayout()
		disable_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
		disable_row.setSpacing(8)
		disable_row.addWidget(self.disable_checkbox)
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

		# Go-Live Notification (if supported)
		if has_notification:
			notif_layout = QVBoxLayout()
			notif_label = QLabel("Go-Live Notification:")
			notif_label.setStyleSheet("color: #ffffff; font-weight: normal; margin-bottom: 5px;")
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
			notif_layout.addWidget(notif_label)
			notif_layout.addWidget(notif_input)
			layout.addLayout(notif_layout)

		# Category/Game (if supported)
		if has_category:
			category_layout = QVBoxLayout()
			row_layout = QHBoxLayout()
			category_label = QLabel("Stream Category:")
			category_label.setStyleSheet("color: #ffffff; font-weight: normal;")
			category_label.setMinimumWidth(150)
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
			row_layout.addWidget(category_label)
			row_layout.addWidget(category_input)
			category_layout.addLayout(row_layout)

			# Only for Twitch: add suggestions list
			if platform_name == 'twitch':
				self._setup_twitch_suggestions(platform_name, category_input, category_layout)

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
			tags_display_layout = QHBoxLayout(tags_display)
			tags_display_layout.setContentsMargins(5, 5, 5, 5)
			tags_display_layout.setSpacing(5)
			tags_display_layout.addStretch()
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

# ... (rest of the file omitted in checkpoint to keep snapshot readable) ...

# --- END FILE SNAPSHOT ---------------------------------------------------

