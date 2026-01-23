
"""
Chat Page - Display messages from all connected platforms
"""

# Standard library imports
import os
import base64
import json
import hashlib
import html

# PyQt6 imports (guarded for headless/test environments)
HAS_PYQT = True
try:
    from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox, QHBoxLayout,
                                  QCheckBox, QPushButton, QMenu, QInputDialog, QMessageBox, QSizePolicy)
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineScript
    from PyQt6.QtCore import pyqtSlot, pyqtSignal, Qt, QUrl, QTimer
    from PyQt6.QtGui import QAction
except Exception:
    HAS_PYQT = False
    class QWidget:
        def __init__(self, parent=None):
            self._parent = parent

    class QVBoxLayout:
        def __init__(self, *a, **k):
            pass

    class QLabel:
        def __init__(self, *a, **k):
            pass

    class QGroupBox:
        def __init__(self, *a, **k):
            pass

    class QHBoxLayout:
        def __init__(self, *a, **k):
            pass

    class QCheckBox:
        def __init__(self, *a, **k):
            pass

    class QPushButton:
        def __init__(self, *a, **k):
            pass

    class QMenu:
        def __init__(self, *a, **k):
            pass

    class QInputDialog:
        @staticmethod
        def getText(parent, title, label):
            return ('', False)

    class QMessageBox:
        @staticmethod
        def information(parent, title, message):
            return None

    class QSizePolicy:
        def __init__(self, *a, **k):
            pass

    class QWebEngineView:
        def __init__(self, *a, **k):
            pass

    class QWebEngineScript:
        DocumentReady = 0
        def __init__(self, *a, **k):
            pass

    def pyqtSlot(*a, **k):
        def _decorator(f):
            return f
        return _decorator

    class _DummySignal:
        def __init__(self):
            self._callbacks = []
        def connect(self, cb):
            try:
                self._callbacks.append(cb)
            except Exception:
                pass
        def emit(self, *a, **k):
            for cb in list(self._callbacks):
                try:
                    cb(*a, **k)
                except Exception:
                    pass

    def pyqtSignal(*a, **k):
        return _DummySignal()

    class Qt:
        AlignLeft = 0
        AlignRight = 1
        AlignCenter = 2

    class QUrl:
        def __init__(self, url=''):
            self._url = url
        def toString(self):
            return str(self._url)

    class QTimer:
        def __init__(self, *a, **k):
            pass

    class QAction:
        def __init__(self, *a, **k):
            pass

# If the PyQt6 package stubs are actually available in the environment (e.g., the
# local `PyQt6_local` stubs were registered in `PyQt6`), prefer those concrete
# implementations over the simple fallbacks above. This helps keep behavior
# consistent when the project's PyQt6 shim is present.
try:
    import PyQt6
    if hasattr(PyQt6, 'QtWidgets'):
        try:
            QW = PyQt6.QtWidgets
            QWidget = getattr(QW, 'QWidget', QWidget)
            QVBoxLayout = getattr(QW, 'QVBoxLayout', QVBoxLayout)
            QLabel = getattr(QW, 'QLabel', QLabel)
            QGroupBox = getattr(QW, 'QGroupBox', QGroupBox)
            QHBoxLayout = getattr(QW, 'QHBoxLayout', QHBoxLayout)
            QCheckBox = getattr(QW, 'QCheckBox', QCheckBox)
            QPushButton = getattr(QW, 'QPushButton', QPushButton)
            QMenu = getattr(QW, 'QMenu', QMenu)
            QInputDialog = getattr(QW, 'QInputDialog', QInputDialog)
            QMessageBox = getattr(QW, 'QMessageBox', QMessageBox)
            QSizePolicy = getattr(QW, 'QSizePolicy', QSizePolicy)
        except Exception:
            pass
    if hasattr(PyQt6, 'QtWebEngineWidgets'):
        try:
            QWebEngineView = getattr(PyQt6.QtWebEngineWidgets, 'QWebEngineView', QWebEngineView)
        except Exception:
            pass
    if hasattr(PyQt6, 'QtWebEngineCore'):
        try:
            QWebEngineScript = getattr(PyQt6.QtWebEngineCore, 'QWebEngineScript', QWebEngineScript)
        except Exception:
            pass
    if hasattr(PyQt6, 'QtCore'):
        try:
            QC = PyQt6.QtCore
            pyqtSlot = getattr(QC, 'pyqtSlot', pyqtSlot)
            pyqtSignal = getattr(QC, 'pyqtSignal', pyqtSignal)
            Qt = getattr(QC, 'Qt', Qt)
            QUrl = getattr(QC, 'QUrl', QUrl)
            QTimer = getattr(QC, 'QTimer', QTimer)
        except Exception:
            pass
    if hasattr(PyQt6, 'QtGui'):
        try:
            QAction = getattr(PyQt6.QtGui, 'QAction', QAction)
        except Exception:
            pass
    HAS_PYQT = True
except Exception:
    pass

# Project-specific imports
from core.badge_manager import get_badge_manager
from core.blocked_terms_manager import get_blocked_terms_manager
from ui.platform_icons import get_platform_icon_html, PLATFORM_COLORS

from core.logger import get_logger

# Structured logger for this module
logger = get_logger('ChatPage')


# --- Kick badge icon mapping ---
KICK_BADGE_ICONS = {
    # type: (local_svg_path, tooltip)
    'moderator': ("resources/badges/kick/moderator.svg", "Moderator"),
    'broadcaster': ("resources/badges/kick/broadcaster.svg", "Broadcaster"),
    'founder': ("resources/badges/kick/founder.svg", "Founder"),
    'subscriber': ("resources/badges/kick/subscriber.svg", "Subscriber"),
    'vip': ("resources/badges/kick/vip.svg", "VIP"),
    'staff': ("resources/badges/kick/staff.svg", "Staff"),
    'bot': ("resources/badges/kick/bot.svg", "Bot"),
}

# --- Trovo badge icon mapping ---
TROVO_BADGE_ICONS = {
    # type: (local_svg_path, tooltip)
    'creator': ("resources/icons/trovo.png", "Creator"),
    'streamer': ("resources/icons/trovo.png", "Streamer"),
    'moderator': ("resources/icons/trovo.png", "Moderator"),
    'subscriber': ("resources/icons/trovo.png", "Subscriber"),
    'vip': ("resources/icons/trovo.png", "VIP"),
    'founder': ("resources/icons/trovo.png", "Founder"),
}

# --- YouTube badge icon mapping ---
YOUTUBE_BADGE_ICONS = {
    # type: (local_svg_path, tooltip)
    'owner': ("resources/badges/youtube/owner.svg", "Owner"),
    'moderator': ("resources/badges/youtube/moderator.svg", "Moderator"),
    'member': ("resources/badges/youtube/member.svg", "Member"),
    'verified': ("resources/badges/youtube/verified.svg", "Verified"),
}

# --- DLive badge icon mapping ---
DLIVE_BADGE_ICONS = {
    # type: (local_svg_path, tooltip)
    'partner': ("resources/badges/dlive/partner.svg", "Partner"),
    'subscriber': ("resources/badges/dlive/subscriber.svg", "Subscriber"),
    'moderator': ("resources/badges/dlive/moderator.svg", "Moderator"),
    'gift': ("resources/badges/dlive/gift.svg", "Gift"),
    'follow': ("resources/badges/dlive/follow.svg", "Follow"),
}


# --- Username Color Assignment ---
# Predefined colors that are visible against dark backgrounds
# These are the default colors, can be customized in settings
USERNAME_COLORS = [
    '#FF6B6B',  # Red
    '#4ECDC4',  # Teal
    '#45B7D1',  # Light Blue
    '#FFA07A',  # Light Salmon
    '#98D8C8',  # Mint
    '#F7DC6F',  # Yellow
    '#BB8FCE',  # Purple
    '#85C1E2',  # Sky Blue
    '#F8B88B',  # Peach
    '#FAD7A0',  # Tan
    '#A9DFBF',  # Light Green
    '#F5B7B1',  # Pink
    '#D7BDE2',  # Lavender
    '#AED6F1',  # Baby Blue
    '#F9E79F',  # Light Yellow
    '#FADBD8',  # Blush
    '#D5F4E6',  # Mint Cream
    '#EBDEF0',  # Lilac
    '#E8DAEF',  # Mauve
    '#A3E4D7',  # Aqua
]


def set_username_colors(colors):
    """Update the username colors palette."""
    global USERNAME_COLORS
    USERNAME_COLORS.clear()
    USERNAME_COLORS.extend(colors)
    logger.info(f"Updated USERNAME_COLORS with {len(colors)} colors")


def get_username_color(username: str) -> str:
    """
    Generate a consistent color for a username based on its hash.
    The same username will always get the same color.
    
    Args:
        username: The username to generate a color for
    
    Returns:
        A hex color string (e.g., '#FF6B6B')
    """
    # Use MD5 hash to get a consistent number from the username
    hash_obj = hashlib.md5(username.lower().encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    
    # Use modulo to map to our color palette
    color_index = hash_int % len(USERNAME_COLORS)
    
    return USERNAME_COLORS[color_index]
    

def get_badge_html(badge_str: str, platform: str = 'twitch') -> str:
    """
    Convert badge string to HTML image tag.
    Args:
        badge_str: Badge identifier (e.g., 'moderator/1' or 'subscriber/12')
        platform: Platform name ('twitch', 'kick', 'trovo', 'youtube', 'dlive')
    Returns:
        HTML <img> tag or empty string if badge not found
    """
    try:
        # If badge_str is just a platform badge type (no version), use platform-specific icons
        if '/' not in badge_str:
            # Select the appropriate badge icon set
            if platform == 'kick':
                badge_icons = KICK_BADGE_ICONS
                logger.debug(f"Looking up Kick badge: '{badge_str}'")
            elif platform == 'trovo':
                badge_icons = TROVO_BADGE_ICONS
                logger.debug(f"Looking up Trovo badge: '{badge_str}'")
            elif platform == 'youtube':
                badge_icons = YOUTUBE_BADGE_ICONS
                logger.debug(f"Looking up YouTube badge: '{badge_str}'")
            elif platform == 'dlive':
                badge_icons = DLIVE_BADGE_ICONS
                logger.debug(f"Looking up DLive badge: '{badge_str}'")
            else:
                # Unknown platform without version - return empty
                return ''
            
            icon = badge_icons.get(badge_str)
            if icon:
                local_path, tooltip = icon
                try:
                    with open(local_path, 'rb') as f:
                        svg_data = f.read()
                    img_data = base64.b64encode(svg_data).decode()
                    data_uri = f'data:image/svg+xml;base64,{img_data}'
                    return f'<img src="{data_uri}" width="18" height="18" style="vertical-align: middle; margin-right: 2px;" title="{tooltip}" />'
                except Exception as e:
                    logger.debug(f"Error reading {platform} badge SVG from {local_path}: {e}")
                    # Return text fallback if SVG not found
                    return f'<span style="background: #555; color: #fff; padding: 2px 4px; border-radius: 3px; font-size: 10px; margin-right: 4px;" title="{tooltip}">{badge_str.upper()}</span>'
            else:
                logger.debug(f"{platform} badge '{badge_str}' not found. Showing as text badge.")
                # Return text fallback for unknown badges
                return f'<span style="background: #555; color: #fff; padding: 2px 4px; border-radius: 3px; font-size: 10px; margin-right: 4px;">{badge_str.upper()}</span>'

        # Otherwise, treat as Twitch-style badge (with version)
        badge_manager = get_badge_manager()
        parts = badge_str.split('/')
        if len(parts) != 2:
            logger.debug(f"Badge {badge_str} doesn't have version number")
            return ''
        badge_name, version = parts
        badge_key = f"{badge_name}/{version}"
        badge_title = badge_manager.get_badge_title(badge_key)
        if not badge_title:
            badge_title = badge_name.replace('-', ' ').replace('_', ' ').title()
        badge_path = badge_manager.get_badge_path(badge_key, size='1x')
        if not badge_path or not os.path.exists(badge_path):
            logger.debug(f"Downloading badge: {badge_key}")
            badge_path = badge_manager.download_badge(badge_key, size='1x')
        if not badge_path or not os.path.exists(badge_path):
            logger.debug(f"Badge not found after download attempt: {badge_key}")
            return ''
        with open(badge_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{img_data}" width="18" height="18" style="vertical-align: middle; margin-right: 2px;" title="{badge_title}" />'
    except Exception as e:
        logger.error(f"Error getting badge HTML for {badge_str}: {e}")
        import traceback
        traceback.print_exc()
        return ''

class ChatPage(QWidget):
    # Emitted when a message has been rendered into the WebEngine DOM.
    # Passes the `message_id` string when available.
    message_rendered = pyqtSignal(str)
    # Emitted when the WebEngine page is ready to receive JS (document.readyState)
    page_ready = pyqtSignal()
    # Emitted when a background render is ready to be inserted into the DOM
    render_ready = pyqtSignal(str, str, bool)
    """Chat page displaying messages from all platforms"""
    
    def __init__(self, chat_manager, config=None, parent=None):
        super().__init__(parent)
        self.chat_manager = chat_manager
        self.config = config
        
        # Load settings from config
        if self.config:
            self.show_platform_icons = self.config.get('ui.show_platform_icons', True)
            self.show_user_colors = self.config.get('ui.show_user_colors', True)
            self.show_timestamps = self.config.get('ui.show_timestamps', True)
            self.show_badges = self.config.get('ui.show_badges', True)
            self.background_style = self.config.get('ui.background_style', 'No background')
            
            # Load custom username colors if configured
            custom_colors = self.config.get('ui.username_colors')
            if custom_colors and len(custom_colors) == 20:
                set_username_colors(custom_colors)
                logger.info(f"Loaded {len(custom_colors)} custom username colors from config")
        else:
            self.show_platform_icons = True
            self.show_user_colors = True
            self.show_timestamps = True
            self.show_badges = True
            self.background_style = 'No background'
        
        # Track message count for alternating backgrounds
        self.message_count = 0
        
        # Track message data for moderation
        self.message_data = {}
        self.platform_message_id_map = {}  # Map platform message_id -> internal msg_id for deletion events
        self.blocked_terms_manager = get_blocked_terms_manager()
        
        # Pause/unpause message display
        self.is_paused = False
        # Immediate JS execution rate-limits
        # Number of immediate calls allowed per second for generic priority snippets
        self._immediate_rate_limit = 20
        # Number of immediate calls allowed per second specifically for tiny metadata/data-uri patches
        # Temporarily raised for testing to allow aggressive immediate patching
        self._meta_immediate_rate_limit = (self.config.get('ui.meta_immediate_rate_limit') if self.config else None) or 200
        # timestamps of recent immediate calls
        self._immediate_call_timestamps = []
        self.message_queue = []
        # Count of Python-side display calls (increments for every _displayMessage call)
        self._python_display_count = 0
        
        # JavaScript execution queue for reliable message rendering
        self.js_execution_queue = []
        self.is_processing_js = False
        self.pending_js_count = 0
        self.max_pending_js = 20  # Increased limit for high-volume chat (was 10)
        self._js_retry_count = {}  # Track retries for failed executions
        # Immediate execution rate-limiting for META_PRIORITY items
        self._immediate_call_timestamps = []
        self._immediate_rate_limit = 20  # max immediate runs per second
        # Track message_ids already queued to avoid duplicate DOM insertions
        self._queued_message_ids = set()
        
        # Overlay server will be set by main.py
        self.overlay_server = None
        # Page readiness flag
        self._page_ready_emitted = False
        
        self.initUI()
        
        # Connect to chat manager signals
        # Diagnostic: log IDs when connecting
        try:
            logger.debug(f"[TRACE] Connecting to ChatManager.message_received chat_manager_id={id(self.chat_manager)} chat_page_id={id(self)}")
        except Exception:
            pass
        self.chat_manager.message_received.connect(self.addMessage)
        
        # Connect to deletion signal if available
        if hasattr(self.chat_manager, 'message_deleted'):
            self.chat_manager.message_deleted.connect(self.onPlatformMessageDeleted)

        # Connect background render completion to DOM insertion handler
        try:
            # Ensure the signal is delivered to the main thread via queued connection
            self.render_ready.connect(self._on_render_ready, Qt.QueuedConnection)
        except Exception:
            try:
                self.render_ready.connect(self._on_render_ready)
            except Exception:
                pass

        # Subscribe to emote cached events so we can patch placeholders when
        # emote images are written to disk by the emote manager. Use explicit
        # connect calls and emit a short diagnostic to confirm the subscription
        # succeeded (helps correlate META_CACHE_EMIT -> META_HANDLER_CALLED).
        try:
            from core.signals import signals as emote_signals
            try:
                emote_signals.emote_image_cached_ext.connect(self._on_emote_image_cached)
            except Exception as e:
                try:
                    logger.debug(f"[TRACE] failed connect emote_image_cached_ext: {e}")
                except Exception:
                    pass
            try:
                emote_signals.emote_set_metadata_ready_ext.connect(self._on_emote_set_metadata_ready)
                # Subscription diagnostic: write a log entry so we can correlate
                try:
                    import time, os
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} META_SUBSCRIBE_CONNECTED emote_signals_present=True\n")
                except Exception:
                    pass
            except Exception as e:
                try:
                    logger.debug(f"[TRACE] failed connect emote_set_metadata_ready_ext: {e}")
                except Exception:
                    pass
        except Exception as e:
            try:
                logger.debug(f"[TRACE] import core.signals failed: {e}")
            except Exception:
                pass

        # Threading: allow background rendering of messages so UI remains responsive
        self._render_threads = []
        # Queue for worker -> main-thread DOM insertions (thread-safe)
        try:
            import threading as _threading
            self._worker_queue = []
            self._worker_queue_lock = _threading.Lock()
            self._worker_queue_timer = QTimer(self)
            self._worker_queue_timer.setInterval(50)
            self._worker_queue_timer.timeout.connect(self._drain_worker_queue)
            self._worker_queue_timer.start()
        except Exception:
            # Best-effort; if threading or timers unavailable, fall back to signals only
            self._worker_queue = None
            self._worker_queue_lock = None
            self._worker_queue_timer = None
    
    def replace_emotes_with_images(self, message: str, emotes_tag: str) -> str:
        """
        Replace emote text with image tags (Twitch emotes).
        Args:
            message: Original message text
            emotes_tag: Twitch emotes tag (e.g., "25:0-4,12-16/1902:6-10") or a dict mapping emote_id -> ["start-end", ...]
        Returns:
            Message with emotes replaced by <img> tags
        """
        if not message:
                # If we have a page, attempt immediate execution subject to simple rate limiting.
                if page:
                    # Allow a test-time override to bypass rate limiting via env var AZB_FORCE_IMMEDIATE=1
                    try:
                        force_immediate = bool(os.environ.get('AZB_FORCE_IMMEDIATE') in ('1', 'true', 'True'))
                    except Exception:
                        force_immediate = False
                    if force_immediate:
                        try:
                            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                df.write(f"{time.time():.3f} IMMEDIATE_FORCED_BY_ENV message_id={message_id}\n")
                                try:
                                    df.flush(); os.fsync(df.fileno())
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    # Extra diagnostics: log immediate timestamp list and queue length
                    try:
                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} IMMEDIATE_DIAG message_id={message_id} page_present=1 pending_js={self.pending_js_count} queue_len={len(self.js_execution_queue)} timestamps={self._immediate_call_timestamps}\n")
                            try:
                                df.flush(); os.fsync(df.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass
        if not emotes_tag:
            # No emote info; escape message for safe HTML
            return html.escape(message)

        try:
            positions = []  # list of (start, end, emote_id)

            if isinstance(emotes_tag, dict):
                for eid, ranges in emotes_tag.items():
                    try:
                        eid_int = int(eid)
                    except Exception:
                        continue
                    for r in (ranges or []):
                        if not r:
                            continue
                        s, e = r.split('-')
                        positions.append((int(s), int(e), eid_int))

            elif isinstance(emotes_tag, str):
                # Format: "25:0-4,12-16/1902:6-10"
                for part in emotes_tag.split('/'):
                    if not part:
                        continue
                    if ':' not in part:
                        continue
                    eid, rngs = part.split(':', 1)
                    try:
                        eid_int = int(eid)
                    except Exception:
                        continue
                    for r in rngs.split(','):
                        if not r:
                            continue
                        if '-' not in r:
                            continue
                        s, e = r.split('-', 1)
                        positions.append((int(s), int(e), eid_int))

            else:
                # Unknown format - return escaped message
                return html.escape(message)

            if not positions:
                return html.escape(message)

            # Sort positions by start index
            positions.sort(key=lambda x: x[0])

            out_parts = []
            last = 0
            for s, e, eid in positions:
                # Skip overlapping or invalid ranges
                if s < last or s >= len(message):
                    continue
                if e < s:
                    continue
                # Append text before emote
                if s > last:
                    out_parts.append(html.escape(message[last:s]))

                # Build emote image tag using Twitch CDN v2
                emote_url = f'https://static-cdn.jtvnw.net/emoticons/v2/{eid}/default/dark/1.0'
                out_parts.append(f'<img src="{emote_url}" alt="emote" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />')
                last = e + 1

            # Append remaining text
            if last < len(message):
                out_parts.append(html.escape(message[last:]))

            return ''.join(out_parts)
        except Exception as e:
            logger.debug(f"Failed to parse emotes tag: {e}")
            return html.escape(message)
    
    def initUI(self):
        """Initialize the chat page UI"""
        main_layout = QVBoxLayout(self)
        try:
            # Debug: show layout details when running in headless tests
            import inspect, sys
            # print type/dir to stdout for pytest capture if this branch errors
            print('DEBUG: main_layout type=', type(main_layout), 'module=', getattr(type(main_layout),'__module__', None))
            print('DEBUG: has setContentsMargins=', hasattr(main_layout, 'setContentsMargins'))
        except Exception:
            pass
        main_layout.setContentsMargins(10, 2, 10, 2)
        main_layout.setSpacing(2)
        
        # Title
        title = QLabel("Chat Messages")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff; margin: 0; padding: 2px 0 8px 0;")
        title.setMaximumHeight(38)
        main_layout.addWidget(title)
        
        # Settings section (no title heading)
        settings_group = QGroupBox("Settings")
        settings_group.setMaximumHeight(50)  # Limit height to 50 pixels
        settings_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-size: 10px;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                margin: 0;
                padding: 2px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
        """)
        
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(5)
        settings_layout.setContentsMargins(3, 0, 3, 0)
        
        # Show platform icons toggle
        self.icons_checkbox = QCheckBox("Icons")
        self.icons_checkbox.setChecked(self.show_platform_icons)
        self.icons_checkbox.setToolTip("Display streaming platform source icon")
        self.icons_checkbox.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.icons_checkbox.stateChanged.connect(self.togglePlatformIcons)
        settings_layout.addWidget(self.icons_checkbox)
        
        # Show user colors toggle
        self.colors_checkbox = QCheckBox("Colors")
        self.colors_checkbox.setChecked(self.show_user_colors)
        self.colors_checkbox.setToolTip("Display username with platform color")
        self.colors_checkbox.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.colors_checkbox.stateChanged.connect(self.toggleUserColors)
        settings_layout.addWidget(self.colors_checkbox)
        
        # Show timestamps toggle
        self.timestamps_checkbox = QCheckBox("Time")
        self.timestamps_checkbox.setChecked(self.show_timestamps)
        self.timestamps_checkbox.setToolTip("Display message timestamp (HH:MM)")
        self.timestamps_checkbox.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.timestamps_checkbox.stateChanged.connect(self.toggleTimestamps)
        settings_layout.addWidget(self.timestamps_checkbox)
        
        # Show badges toggle
        self.badges_checkbox = QCheckBox("Badges")
        self.badges_checkbox.setChecked(self.show_badges)
        self.badges_checkbox.setToolTip("Display user badges")
        self.badges_checkbox.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.badges_checkbox.stateChanged.connect(self.toggleBadges)
        settings_layout.addWidget(self.badges_checkbox)
        
        # Background style dropdown
        # Ensure QComboBox is defined in this scope (may come from PyQt6 stubs)
        QComboBox = globals().get('QComboBox', None)
        try:
            from PyQt6.QtWidgets import QComboBox as _QComboBox, QLabel as QLabelWidget
            QComboBox = _QComboBox
        except Exception:
            # Fall back to already-resolved QLabel/QComboBox stubs
            try:
                import PyQt6
                if hasattr(PyQt6, 'QtWidgets'):
                    QComboBox = getattr(PyQt6.QtWidgets, 'QComboBox', QComboBox)
            except Exception:
                pass
            QLabelWidget = QLabel
        bg_label = QLabelWidget("Visibility:")
        bg_label.setStyleSheet("color: #ffffff; font-size: 12px; margin-left: 10px;")
        settings_layout.addWidget(bg_label)
        
        self.background_combo = QComboBox()
        self.background_combo.addItems(["No background", "Background", "Alternating"])
        self.background_combo.setCurrentText(self.background_style)
        self.background_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 12px;
                min-width: 120px;
            }
            QComboBox:hover {
                border: 1px solid #5d5d5d;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #3d3d3d;
                border: 1px solid #3d3d3d;
            }
        """)
        self.background_combo.currentTextChanged.connect(self.changeBackgroundStyle)
        settings_layout.addWidget(self.background_combo)
        
        settings_layout.addStretch()
        
        # Pause/Unpause button
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #ec971f;
            }
            QPushButton:checked {
                background-color: #5cb85c;
            }
            QPushButton:checked:hover {
                background-color: #449d44;
            }
        """)
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self.togglePause)
        settings_layout.addWidget(self.pause_btn)
        
        # Clear chat button
        clear_btn = QPushButton("Clear Chat")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        clear_btn.clicked.connect(self.clearChat)
        
        # Dump chat HTML button (debug helper)
        dump_btn = QPushButton("Dump Chat")
        dump_btn.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #31b0d5;
            }
        """)
        dump_btn.clicked.connect(lambda: self.dump_chat_body())
        settings_layout.addWidget(dump_btn)
        settings_layout.addWidget(clear_btn)
        
        settings_group.setLayout(settings_layout)
        # Wrap settings in a horizontal scroll area so controls can overflow horizontally
        try:
            from PyQt6.QtWidgets import QScrollArea
        except Exception:
            try:
                import PyQt6
                QScrollArea = getattr(PyQt6.QtWidgets, 'QScrollArea', None)
            except Exception:
                QScrollArea = globals().get('QScrollArea', None)
        settings_container = QWidget()
        sc_layout = QHBoxLayout(settings_container)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.addWidget(settings_group)

        settings_scroll = QScrollArea()
        settings_scroll.setWidget(settings_container)
        settings_scroll.setWidgetResizable(False)  # Keep content natural size so horizontal scrollbar appears
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        settings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Match the group's max height so scroll area doesn't consume extra vertical space
        try:
            settings_scroll.setFixedHeight(settings_group.maximumHeight() + 6)
        except Exception:
            pass

        main_layout.addWidget(settings_scroll)
        
        # Chat messages area (QWebEngineView for animated GIF support)
        self.chat_display = QWebEngineView()
        # Ensure the chat display expands to fill available space in the page
        try:
            self.chat_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            # A reasonable minimum height so the area is usable even when window is short
            self.chat_display.setMinimumHeight(150)
        except Exception:
            pass
        
        # Set up initial HTML with dark background and styling
        initial_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 13px;
                    margin: 8px;
                    padding: 0;
                }
                .message {
                    margin: 0;
                    padding: 0;
                    line-height: 1.4;
                    display: block;
                    /* Allow long messages to wrap to next line instead of forcing horizontal scroll */
                    white-space: pre-wrap; /* Preserve newlines, allow wrapping */
                    word-break: break-word; /* Break long words if needed */
                    overflow-wrap: anywhere;
                    max-width: 100%;
                }

                /* Ensure any images/emotes inside messages scale to container */
                .message img {
                    max-width: 100%;
                    height: auto;
                    vertical-align: middle;
                }

                /* Placeholder emote styling while warming */
                .emote.placeholder {
                    opacity: 0.6;
                    filter: grayscale(1);
                    transition: opacity 200ms linear, filter 200ms linear;
                }
                
                /* Slide in from bottom animation */
                @keyframes slideInFromBottom {
                    0% {
                        transform: translateY(100px);
                        opacity: 0;
                    }
                    100% {
                        transform: translateY(0);
                        opacity: 1;
                    }
                }
                
                /* Wiggle animation */
                @keyframes wiggle {
                    0%, 100% {
                        transform: rotate(0deg) scale(1);
                    }
                    10% {
                        transform: rotate(2deg) scale(1.02);
                    }
                    20% {
                        transform: rotate(-2deg) scale(1.02);
                    }
                    30% {
                        transform: rotate(2deg) scale(1.01);
                    }
                    40% {
                        transform: rotate(-2deg) scale(1.01);
                    }
                    50% {
                        transform: rotate(1deg) scale(1.01);
                    }
                    60% {
                        transform: rotate(-1deg) scale(1.01);
                    }
                    70% {
                        transform: rotate(1deg) scale(1);
                    }
                    80% {
                        transform: rotate(-1deg) scale(1);
                    }
                    90% {
                        transform: rotate(0.5deg) scale(1);
                    }
                }
                
                /* Animation classes */
                .message-slide-in {
                    animation: slideInFromBottom 0.8s ease-out;
                }
                
                .message-wiggle {
                    animation: wiggle 2s ease-in-out;
                }
            </style>
        </head>
        <body id="chat-body">
        </body>
        </html>
        '''
        self.chat_display.setHtml(initial_html)
        self.chat_display.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_display.customContextMenuRequested.connect(self.showContextMenu)
        # Listen for the WebEngine loadFinished to confirm page readiness
        try:
            # QWebEngineView emits loadFinished(bool)
            self.chat_display.loadFinished.connect(self._on_page_load_finished)
        except Exception:
            pass
        # Chat display should expand to fill remaining space and resize dynamically
        main_layout.addWidget(self.chat_display, 1)
        
        # Setup message interaction JavaScript
        self.setup_message_interaction()
    
    def setup_message_interaction(self):
        """Setup JavaScript for message interaction and context menu"""
        # Inject JavaScript to handle message selection and context menu
        script = QWebEngineScript()
        script.setName("message_interaction")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)  # Use MainWorld instead of ApplicationWorld
        script.setSourceCode("""
            window.selectedMessageId = null;
            
            document.addEventListener('click', function(e) {
                // Find the message div that was clicked
                let target = e.target;
                while (target && target !== document.body && !target.classList.contains('message')) {
                    target = target.parentElement;
                }
                
                if (target && target.classList.contains('message') && target.dataset.messageId) {
                    // Check if this message is already selected
                    if (window.selectedMessageId === target.dataset.messageId) {
                        // Unselect it
                        target.style.outline = '';
                        window.selectedMessageId = null;
                        window.selectedMessageText = null;
                    } else {
                        // Remove previous selection
                        document.querySelectorAll('.message').forEach(msg => {
                            msg.style.outline = '';
                        });
                        
                        // Highlight selected message
                        target.style.outline = '2px solid #4a90e2';
                        
                        // Store the message ID
                        window.selectedMessageId = target.dataset.messageId;
                        window.selectedMessageText = target.textContent;
                    }
                }
            });
            
            document.addEventListener('contextmenu', function(e) {
                // Find the message div that was right-clicked
                let target = e.target;
                while (target && target !== document.body && !target.classList.contains('message')) {
                    target = target.parentElement;
                }
                
                if (target && target.classList.contains('message') && target.dataset.messageId) {
                    // Remove previous selection
                    document.querySelectorAll('.message').forEach(msg => {
                        msg.style.outline = '';
                    });
                    
                    // Highlight right-clicked message
                    target.style.outline = '2px solid #4a90e2';
                    
                    // Store the message ID
                    window.selectedMessageId = target.dataset.messageId;
                    window.selectedMessageText = target.textContent;
                }
            });
        """)
        self.chat_display.page().scripts().insert(script)

    def _on_page_load_finished(self, ok: bool):
        """Handler for QWebEngineView.loadFinished; probe document.readyState and emit `page_ready` when appropriate."""
        try:
            if not ok:
                # loadFinished False - schedule a retry to probe readiness later
                QTimer.singleShot(200, self._check_document_ready)
                return
        except Exception:
            pass
        # Probe document.readyState
        self._check_document_ready()

    def _check_document_ready(self):
        """Run a short JS probe to determine document.readyState and emit `page_ready` once."""
        # Avoid repeated emissions
        try:
            if getattr(self, '_page_ready_emitted', False):
                return
        except Exception:
            pass

        def _cb(state):
            try:
                s = (state or '').lower()
                if s in ('complete', 'interactive'):
                    try:
                        self._page_ready_emitted = True
                    except Exception:
                        pass
                    try:
                        self.page_ready.emit()
                    except Exception:
                        pass
                else:
                    # Not ready yet - re-probe shortly
                    QTimer.singleShot(200, self._check_document_ready)
            except Exception:
                # Swallow errors and retry once
                try:
                    QTimer.singleShot(200, self._check_document_ready)
                except Exception:
                    pass

        try:
            # Use runJavaScript to fetch document.readyState; callback will handle emission
            self.chat_display.page().runJavaScript('document.readyState', _cb)
        except Exception:
            # If runJavaScript fails (view not ready), retry shortly
            try:
                QTimer.singleShot(200, self._check_document_ready)
            except Exception:
                pass
    
    @pyqtSlot(str, str, str, dict)
    @pyqtSlot(str, str, str, dict)
    def addMessage(self, platform, username, message, metadata=None):
        """Add a new chat message (or queue if paused)"""
        # TRACE: incoming message to ChatPage
        try:
            preview = message[:120] if message else ''
        except Exception:
            preview = ''
        # Persistent receipt debug so we can see calls even if display path later suppresses
        try:
            import time, os
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            dbg = os.path.join(log_dir, 'chat_page_received.log')
            mid = None
            try:
                if isinstance(metadata, dict):
                    mid = metadata.get('message_id') or metadata.get('id')
            except Exception:
                mid = None
            with open(dbg, 'a', encoding='utf-8', errors='replace') as df:
                df.write(f"{time.time():.3f} RECEIVED platform={platform} username={username} message_id={repr(mid)} preview={repr(preview)} metadata_keys={list(metadata.keys()) if isinstance(metadata, dict) else None}\n")
                # Persistent diagnostic: record that we queued a DOM insertion
                try:
                    import time, os
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df2:
                        df2.write(f"{time.time():.3f} QUEUE message_id={mid} has_img={metadata.get('has_img', False)}\n")
                except Exception:
                    pass
        except Exception:
            pass
        # Early normalization: some connectors embed IRC tag blob into `username` (e.g. '... :realuser')
        # Extract message_id and clean username so duplicate raw/normalized events are deduplicated.
        try:
            if isinstance(metadata, dict) is False:
                metadata = metadata or {}
            if platform == 'twitch' and username and ' :' in username:
                raw_user = username
                try:
                    tag_part, real_user = raw_user.split(' :', 1)
                    # extract id=... if present
                    for kv in tag_part.split(';'):
                        if '=' in kv:
                            k, v = kv.split('=', 1)
                            k = k.strip()
                            v = v.strip()
                            if k in ('id', 'message-id', 'message_id') and v:
                                metadata['message_id'] = v
                    # update username to cleaned value
                    username = real_user.strip() or username
                except Exception:
                    pass
        except Exception:
            pass

        # Deduplicate by platform message id if we've already seen it
        try:
            platform_msg_id = None
            if isinstance(metadata, dict):
                platform_msg_id = metadata.get('message_id') or metadata.get('id')
            if platform_msg_id:
                key = f"{platform}:{platform_msg_id}"
                if key in self.platform_message_id_map:
                    logger.debug(f"Duplicate message ignored platform={platform} message_id={platform_msg_id}")
                    return
        except Exception:
            pass
        try:
            logger.debug(f"[TRACE] addMessage called: platform={platform} username={username} preview={preview} paused={self.is_paused} chat_page_id={id(self)} chat_manager_id={id(self.chat_manager)}")
        except Exception:
            logger.debug(f"[TRACE] addMessage called: platform={platform} username={username} preview={preview} paused={self.is_paused}")
        if self.is_paused:
            # Queue the message instead of displaying
            self.message_queue.append((platform, username, message, metadata))
            logger.debug(f"[TRACE] Message queued (paused). queue_length={len(self.message_queue)}")
            return
        
        self._displayMessage(platform, username, message, metadata)
    
    def _displayMessage(self, platform, username, message, metadata=None):
        """Internal method to display a message"""
        logger.info(f"addMessage: platform={platform}, username={username}, message={message}, metadata={metadata}")
        # TRACE: confirm display entry
        try:
            preview = message[:120] if message else ''
        except Exception:
            preview = ''
        logger.debug(f"[TRACE] _displayMessage: platform={platform} username={username} preview={preview}")
        if metadata is None:
            metadata = {}
        
        # Check if message contains blocked terms and highlight them
        blocked_terms_found = self.blocked_terms_manager.get_blocked_terms_in_message(message)
        message_deleted_from_platform = False
        
        if blocked_terms_found:
            logger.warning(f"Message contains blocked terms: {blocked_terms_found}")
            
            # Highlight blocked terms in the message
            import re
            for term in blocked_terms_found:
                # Case-insensitive replacement while preserving original case
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                message = pattern.sub(lambda m: f'<span style="background-color: #ff4444; color: white; padding: 1px 3px; border-radius: 2px;">{m.group(0)}</span>', message)
            
            # Attempt to delete message from platform
            platform_msg_id = metadata.get('message_id')
            if platform_msg_id:
                logger.debug(f"Attempting to delete message {platform_msg_id} from {platform} due to blocked terms")
                try:
                    deletion_success = self.chat_manager.deleteMessage(platform.lower(), platform_msg_id)
                    if deletion_success:
                        message_deleted_from_platform = True
                        logger.info(f"Successfully deleted message from {platform}")
                    else:
                        logger.warning(f"Failed to delete message from {platform} (not supported or error)")
                except Exception as e:
                    logger.error(f"Error deleting message from {platform}: {e}")
            else:
                logger.debug(f"No platform message_id available to delete from {platform}")
        
        # Prefer using the platform-provided message_id when available
        platform_msg_id = None
        try:
            if isinstance(metadata, dict):
                platform_msg_id = metadata.get('message_id') or metadata.get('id')
        except Exception:
            platform_msg_id = None

        if platform_msg_id:
            # Use the platform id directly to avoid accidental dedupe of distinct messages
            message_id = str(platform_msg_id)
            try:
                # still advance counter to keep it moving for non-platform IDs
                self.message_count += 1
            except Exception:
                pass
        else:
            # Generate unique synthetic message ID
            message_id = f"msg_{self.message_count}"
            try:
                self.message_count += 1
            except Exception:
                pass
        
        # Store message data for moderation
        self.message_data[message_id] = {
            'platform': platform,
            'username': username,
            'message': message,
            'metadata': metadata
        }

        # Increment Python-side display counter for tests/environments where
        # QWebEngine callbacks may not run. This ensures we can assert that
        # messages reached the UI layer even if the DOM wasn't updated.
        try:
            self._python_display_count += 1
        except Exception:
            pass
        
        # Map platform message_id to our internal message_id for deletion events
        platform_msg_id = metadata.get('message_id')
        if platform_msg_id:
            self.platform_message_id_map[f"{platform}:{platform_msg_id}"] = message_id
        
        # Get timestamp
        import datetime
        timestamp = metadata.get('timestamp', datetime.datetime.now())
        if isinstance(timestamp, str):
            # Parse ISO 8601 timestamp from Kick API
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.datetime.now()
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.datetime.fromtimestamp(timestamp)
        time_str = timestamp.strftime("%H:%M") if self.show_timestamps else ""
        
        # Check if this is a stream event (follow, sub, raid, etc.)
        event_type = metadata.get('event_type')
        is_event = event_type in ['follow', 'subscription', 'raid', 'bits', 'highlight', 'redemption', 'spell', 'magic_chat']
        
        # Get platform icon (image or emoji)
        icon_html = get_platform_icon_html(platform, size=18) if self.show_platform_icons else ''
        
        # Get username color
        if self.show_user_colors:
            if 'color' in metadata and metadata['color']:
                # Use platform-provided color
                user_color = metadata['color']
                if not user_color.startswith('#'):
                    user_color = f'#{user_color}'
            else:
                # Assign a consistent color based on username
                user_color = get_username_color(username)
        else:
            user_color = '#ffffff'
        
        # Get badges
        badges_html = ''
        if self.show_badges and 'badges' in metadata and metadata['badges']:
            badges = metadata['badges']
            if isinstance(badges, list):
                for badge in badges:
                    # Try to get badge image, passing platform for proper lookup
                    badge_img = get_badge_html(badge, platform)
                    if badge_img:
                        badges_html += badge_img
                    else:
                        # Fallback to text badge
                        badge_name = badge.split('/')[0] if '/' in badge else badge
                        badges_html += f'<span style="background-color: #3d3d3d; padding: 2px 4px; border-radius: 3px; font-size: 10px; margin-right: 2px;">{badge_name}</span>'
            elif isinstance(badges, str):
                # Try to get badge image, passing platform for proper lookup
                badge_img = get_badge_html(badges, platform)
                if badge_img:
                    badges_html = badge_img
                else:
                    # Fallback to text badge
                    badge_name = badges.split('/')[0] if '/' in badges else badges
                    badges_html = f'<span style="background-color: #3d3d3d; padding: 2px 4px; border-radius: 3px; font-size: 10px; margin-right: 2px;">{badge_name}</span>'
        
        # Format message as HTML with conditional spacing
        # Order: icon, timestamp, badges, username, message
        # Only add spaces between elements that are actually displayed
        components = []
        
        # Platform icon (first)
        if icon_html:
            components.append(icon_html)

        # Timestamp
        if time_str:
            components.append(f'<span style="color: #888888; font-size: 11px;">[{time_str}]</span>')

        # Badges
        if badges_html:
            components.append(badges_html)

        # Prepare emotes_tag (may be populated from metadata or recovered by heuristic)
        emotes_tag = None

        # Heuristic: some connectors may misplace IRC tag payload into `username`.
        # Try to recover emotes and real username for Twitch regardless of metadata presence,
        # but only override emotes_tag if we detect a tag-like payload.
        try:
            if platform == 'twitch':
                raw_user = username or ''
                # look for the pattern '... :username' where the left side is semicolon-delimited IRC tags
                if ' :' in raw_user:
                    tag_part, real_user = raw_user.split(' :', 1)
                    first_token = tag_part.split(';', 1)[0]
                    import re as _re
                    if first_token and (_re.search(r"\d+-\d+", first_token) or 'emotesv2_' in first_token or 'id=' in tag_part):
                        # Recover emotes tag only if we haven't got one already
                        if not emotes_tag:
                            emotes_tag = first_token
                        # Update username to the real username portion
                        username = real_user.strip()
                        # Attempt to pull message_id and common keys if metadata is a dict
                        try:
                            if not isinstance(metadata, dict):
                                metadata = {}
                            for kv in tag_part.split(';'):
                                if '=' in kv:
                                    k, v = kv.split('=', 1)
                                    k = k.strip()
                                    v = v.strip()
                                    if not v:
                                        continue
                                    if k in ('id', 'message-id', 'message_id'):
                                        metadata['message_id'] = v
                                    elif k in ('room-id', 'room_id', 'channel_id', 'broadcaster_id'):
                                        metadata['room-id'] = v
                                        metadata['channel_id'] = v
                                    elif k in ('room', 'channel', 'broadcaster'):
                                        metadata['channel'] = v
                        except Exception:
                            pass
                        # Durable debug line for recovered values
                        try:
                            import time, os
                            log_dir = os.path.join(os.getcwd(), 'logs')
                            os.makedirs(log_dir, exist_ok=True)
                            fname = os.path.join(log_dir, 'chat_page_received_fixed.log')
                            with open(fname, 'a', encoding='utf-8', errors='replace') as f:
                                f.write(f"{time.time():.3f} FIXED raw_username={repr(raw_user)} recovered_username={repr(username)} emotes_tag={repr(emotes_tag)}\n")
                        except Exception:
                            pass
        except Exception:
            pass

        # Username
        # Escape username to prevent raw HTML from being injected (connectors may include tag blobs)
        safe_username = html.escape(username or '')
        username_html = f'<span style="color: {user_color}; font-weight: bold;">{safe_username}</span>'
        components.append(username_html)

        # Message - replace emotes where possible (use unified renderer)
        # Common metadata keys for emotes across connectors
        for k in ('emotes', 'emotes_tag', 'emote_tags', 'emotes_raw'):
            if emotes_tag:
                break
            if k in metadata and metadata.get(k):
                emotes_tag = metadata.get(k)
                break

        # If structured fragments are available from EventSub, prefer them
        # and ignore legacy `emotes_tag` so the fragment renderer takes priority.
        try:
            if isinstance(metadata, dict) and metadata.get('fragments'):
                emotes_tag = None
        except Exception:
            pass

        

        # Prefer rendering fragments with local cached images when possible
        message_html = None
        has_img = False
        try:
            frags = None
            if isinstance(metadata, dict):
                frags = metadata.get('fragments') or metadata.get('message_fragments')
            if frags and isinstance(frags, list):
                try:
                    # Attempt to render using local cached emote files
                    from core.twitch_emotes import get_manager as _get_twitch_manager
                    mgr = _get_twitch_manager() if _get_twitch_manager is not None else None
                except Exception:
                    mgr = None

                frag_parts = []
                try:
                    broadcaster_id = None
                    try:
                        broadcaster_id = metadata.get('room-id') or metadata.get('room_id') or metadata.get('channel_id')
                    except Exception:
                        broadcaster_id = None

                    for frag in frags:
                        try:
                            if not isinstance(frag, dict):
                                frag_parts.append(html.escape(str(frag)))
                                continue
                            ftype = frag.get('type')
                            if not ftype or ftype == 'text':
                                frag_parts.append(html.escape(frag.get('text') or ''))
                                continue

                            # Warn on unexpected fragment types to help diagnose new/unknown types
                            try:
                                if ftype not in ('text', 'emote', 'cheermote'):
                                    try:
                                        logger.warning(f"ChatPage: unknown fragment type: {ftype} fragment={json.dumps(frag, default=str)}")
                                    except Exception:
                                        logger.warning(f"ChatPage: unknown fragment type: {ftype}")
                            except Exception:
                                pass

                            if ftype == 'emote':
                                emobj = frag.get('emote') or {}
                                emote_id = None
                                try:
                                    emote_id = str(emobj.get('id') or emobj.get('emote_id') or frag.get('id')) if isinstance(emobj, dict) else None
                                except Exception:
                                    emote_id = None

                                uri_used = None
                                try:
                                    # If we don't have an explicit emote id but the fragment
                                    # references an emote set, attempt to fetch that set
                                    # and resolve the emote id by name from the cache.
                                    if not emote_id:
                                        try:
                                            # Possible keys that may reference an emote set
                                            set_ids = []
                                            sid = None
                                            if isinstance(emobj, dict):
                                                sid = emobj.get('emote_set_id') or emobj.get('emote_set') or emobj.get('set_id')
                                            sid = sid or frag.get('emote_set_id') or frag.get('emote_set') or frag.get('set_id')
                                            if sid:
                                                if isinstance(sid, (list, tuple)):
                                                    set_ids = [str(s) for s in sid if s]
                                                elif isinstance(sid, str) and ',' in sid:
                                                    set_ids = [p.strip() for p in sid.split(',') if p.strip()]
                                                elif sid:
                                                    set_ids = [str(sid)]

                                            # Emote name we can use to resolve after warming cache
                                            emote_name = None
                                            try:
                                                emote_name = (emobj.get('name') if isinstance(emobj, dict) else None) or frag.get('text') or frag.get('name')
                                            except Exception:
                                                emote_name = frag.get('text') if isinstance(frag, dict) else None

                                            if set_ids and mgr:
                                                try:
                                                    # Enqueue warming of emote sets for background processing.
                                                    # Always call the scheduler from a background thread
                                                    # to avoid risk of synchronous network fetches blocking
                                                    # the UI when the throttler isn't active.
                                                    try:
                                                        import threading as _threading
                                                        _threading.Thread(target=lambda: (mgr.schedule_emote_set_fetch(set_ids)), daemon=True).start()
                                                    except Exception:
                                                        # Last-resort fallback: try to schedule directly
                                                        try:
                                                            mgr.schedule_emote_set_fetch(set_ids)
                                                        except Exception:
                                                            # If scheduling fails, spawn a fetch thread instead
                                                            try:
                                                                import threading as _threading
                                                                _threading.Thread(target=lambda: (mgr.fetch_emote_sets(set_ids)), daemon=True).start()
                                                            except Exception:
                                                                pass
                                                except Exception:
                                                    pass

                                            # Try to resolve id by name synchronously (manager will warm if needed)
                                            if mgr and emote_name:
                                                try:
                                                    resolved = mgr.get_emote_id_by_name(emote_name, broadcaster_id=broadcaster_id)
                                                    if resolved:
                                                        emote_id = str(resolved)
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass

                                    if mgr and emote_id:
                                        # If manager doesn't have details for this emote id,
                                        # try to warm any referenced emote_set_id so the
                                        # manager's `id_map` gets populated.
                                        emobj2 = mgr.id_map.get(str(emote_id))
                                        if not emobj2:
                                            try:
                                                set_ids = []
                                                sid = None
                                                if isinstance(emobj, dict):
                                                    sid = emobj.get('emote_set_id') or emobj.get('emote_set') or emobj.get('set_id')
                                                sid = sid or frag.get('emote_set_id') or frag.get('emote_set') or frag.get('set_id')
                                                if sid:
                                                    if isinstance(sid, (list, tuple)):
                                                        set_ids = [str(s) for s in sid if s]
                                                    elif isinstance(sid, str) and ',' in sid:
                                                        set_ids = [p.strip() for p in sid.split(',') if p.strip()]
                                                    elif sid:
                                                        set_ids = [str(sid)]

                                                if set_ids:
                                                    try:
                                                        mgr.schedule_emote_set_fetch(set_ids)
                                                    except Exception:
                                                        try:
                                                            mgr.fetch_emote_sets(set_ids)
                                                        except Exception:
                                                            pass
                                            except Exception:
                                                pass
                                            # try again after warming
                                            emobj2 = mgr.id_map.get(str(emote_id)) or {}
                                        else:
                                            emobj2 = emobj2 or {}
                                        url = mgr._select_image_url(emobj2) if emobj2 else None
                                        ext = 'gif' if url and url.lower().endswith('.gif') else 'png'
                                        name = emobj2.get('name') or emobj2.get('emote_name') or emobj2.get('code') or ''
                                        base_part = f"twitch_{emote_id}_{name}" if name else f"twitch_{emote_id}"
                                        safe_base = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in base_part)
                                        if len(safe_base) > 50:
                                            safe_base = safe_base[:50]
                                        import hashlib as _hashlib
                                        h = _hashlib.sha1((name or str(emote_id)).encode('utf-8')).hexdigest()[:8]
                                        safe_fname = f"{safe_base}_{h}.{ext}"
                                        fpath = None
                                        try:
                                            cache_dir = getattr(mgr, 'cache_dir', None) or os.path.join('resources', 'emotes')
                                            fpath = os.path.join(cache_dir, safe_fname)
                                        except Exception:
                                            fpath = None

                                        if fpath and os.path.exists(fpath):
                                            # Use file:// URL for local file (WebEngine can load local files)
                                            # Normalize to forward slashes for URL
                                            abs_path = os.path.abspath(fpath).replace('\\', '/')
                                            uri_used = f'file:///{abs_path}'
                                        else:
                                            # Fallback to data URI via manager
                                            try:
                                                uri_used = mgr.get_emote_data_uri(emote_id, broadcaster_id=broadcaster_id) if mgr else None
                                            except Exception:
                                                uri_used = None
                                except Exception:
                                    uri_used = None

                                if uri_used:
                                    has_img = True
                                    # Log emote resolution for diagnostics (main thread)
                                    try:
                                        import time, os
                                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                            emid = emote_id or (emobj.get('id') if isinstance(emobj, dict) else None)
                                            df.write(f"{time.time():.3f} QUEUE_EMOTE_URI message_id={message_id} emote_id={emid} uri={uri_used}\n")
                                    except Exception:
                                        pass
                                    frag_parts.append(f'<img src="{uri_used}" alt="{html.escape(frag.get("text") or "emote")}" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />')
                                else:
                                    frag_parts.append(html.escape(frag.get('text') or ''))
                                continue

                            # Other fragment types
                            frag_parts.append(html.escape(frag.get('text') or ''))
                        except Exception:
                            try:
                                frag_parts.append(html.escape(str(frag)))
                            except Exception:
                                frag_parts.append('')

                    message_html = ''.join(frag_parts)
                except Exception:
                    message_html = None

        except Exception:
            message_html = None

        # If we didn't render from fragments above, fall back to unified renderer
        if not message_html:
            try:
                from core.emotes import render_message
                message_html, has_img = render_message(message, emotes_tag, metadata)
                if not message_html:
                    message_html = html.escape(message)
            except Exception:
                # If the unified renderer fails for any reason, fall back to legacy replacement
                try:
                    logger.exception('core.emotes.render_message failed, falling back')
                except Exception:
                    pass
                message_html = self.replace_emotes_with_images(message, emotes_tag)

        # Do not append `message_html` here — the background render worker
        # will re-render and append message text to avoid duplicate content
        # in cases where both main-thread and worker rendering occur.

        # Background render worker will produce `wrapped` HTML and emit `render_ready`.
        def _render_worker(components_snapshot, bg_style_snapshot, message_id_snapshot, metadata_snapshot, platform_snapshot, username_snapshot, message_snapshot, user_color_snapshot):
            try:
                # Persist diagnostic: worker started
                try:
                    import time, os
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} WORKER_START message_id={message_id_snapshot}\n")
                except Exception:
                    pass
                final_parts = list(components_snapshot)
                # Re-run fragment/emote rendering logic in background
                final_message_html = None
                final_has_img = False
                try:
                    # Use same fragment rendering block as above but operate on local copies
                    frags_local = None
                    if isinstance(metadata_snapshot, dict):
                        frags_local = metadata_snapshot.get('fragments') or metadata_snapshot.get('message_fragments')
                    if frags_local and isinstance(frags_local, list):
                        try:
                            from core.twitch_emotes import get_manager as _get_twitch_manager
                            mgr_local = _get_twitch_manager() if _get_twitch_manager is not None else None
                        except Exception:
                            mgr_local = None

                        # If caller requested synchronous per-message warming, attempt
                        # to prefetch all emote sets referenced by this message
                        try:
                            ensure = bool(metadata_snapshot.get('ensure_emotes')) if isinstance(metadata_snapshot, dict) else False
                        except Exception:
                            ensure = False

                        if ensure and mgr_local:
                            try:
                                all_set_ids = set()
                                for _frag in frags_local:
                                    try:
                                        if not isinstance(_frag, dict):
                                            continue
                                        sid = None
                                        emobj_frag = _frag.get('emote') or {}
                                        sid = emobj_frag.get('emote_set_id') or emobj_frag.get('emote_set') or emobj_frag.get('set_id')
                                        sid = sid or _frag.get('emote_set_id') or _frag.get('emote_set') or _frag.get('set_id')
                                        if sid:
                                            if isinstance(sid, (list, tuple)):
                                                for s in sid:
                                                    if s:
                                                        all_set_ids.add(str(s))
                                            elif isinstance(sid, str) and ',' in sid:
                                                for p in sid.split(','):
                                                    p = p.strip()
                                                    if p:
                                                        all_set_ids.add(str(p))
                                            else:
                                                all_set_ids.add(str(sid))
                                    except Exception:
                                        continue

                                if all_set_ids:
                                    import time, os
                                    try:
                                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                            df.write(f"{time.time():.3f} PREFETCH_START message_id={message_id_snapshot} sets={','.join(list(all_set_ids))}\n")
                                            try:
                                                df.flush(); os.fsync(df.fileno())
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass

                                    start_ts = time.time()
                                    try:
                                        mgr_local.fetch_emote_sets(list(all_set_ids))
                                    except Exception:
                                        pass
                                    duration = max(0, int((time.time() - start_ts) * 1000))
                                    try:
                                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                            df.write(f"{time.time():.3f} PREFETCH_END message_id={message_id_snapshot} sets={','.join(list(all_set_ids))} duration_ms={duration}\n")
                                            try:
                                                df.flush(); os.fsync(df.fileno())
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        frag_parts_local = []
                        try:
                            broadcaster_id_local = None
                            try:
                                broadcaster_id_local = metadata_snapshot.get('room-id') or metadata_snapshot.get('room_id') or metadata_snapshot.get('channel_id')
                            except Exception:
                                broadcaster_id_local = None

                            for frag_local in frags_local:
                                try:
                                    if not isinstance(frag_local, dict):
                                        frag_parts_local.append(html.escape(str(frag_local)))
                                        continue
                                    ftype_local = frag_local.get('type')
                                    if not ftype_local or ftype_local == 'text':
                                        frag_parts_local.append(html.escape(frag_local.get('text') or ''))
                                        continue

                                    if ftype_local == 'emote':
                                        emobj_local = frag_local.get('emote') or {}
                                        emote_id_local = None
                                        try:
                                            emote_id_local = str(emobj_local.get('id') or emobj_local.get('emote_id') or frag_local.get('id')) if isinstance(emobj_local, dict) else None
                                        except Exception:
                                            emote_id_local = None

                                        uri_used_local = None
                                        try:
                                            # Attempt emote_set warming and resolution (best-effort)
                                            if not emote_id_local:
                                                try:
                                                    set_ids_local = []
                                                    sid_local = None
                                                    if isinstance(emobj_local, dict):
                                                        sid_local = emobj_local.get('emote_set_id') or emobj_local.get('emote_set') or emobj_local.get('set_id')
                                                    sid_local = sid_local or frag_local.get('emote_set_id') or frag_local.get('emote_set') or frag_local.get('set_id')
                                                    if sid_local:
                                                        if isinstance(sid_local, (list, tuple)):
                                                            set_ids_local = [str(s) for s in sid_local if s]
                                                        elif isinstance(sid_local, str) and ',' in sid_local:
                                                            set_ids_local = [p.strip() for p in sid_local.split(',') if p.strip()]
                                                        elif sid_local:
                                                            set_ids_local = [str(sid_local)]

                                                    emote_name_local = None
                                                    try:
                                                        emote_name_local = (emobj_local.get('name') if isinstance(emobj_local, dict) else None) or frag_local.get('text') or frag_local.get('name')
                                                    except Exception:
                                                        emote_name_local = frag_local.get('text') if isinstance(frag_local, dict) else None

                                                    if set_ids_local and mgr_local:
                                                        try:
                                                            mgr_local.fetch_emote_sets(set_ids_local)
                                                        except Exception:
                                                            pass

                                                    if mgr_local and emote_name_local:
                                                        try:
                                                            resolved_local = mgr_local.get_emote_id_by_name(emote_name_local, broadcaster_id=broadcaster_id_local)
                                                            if resolved_local:
                                                                emote_id_local = str(resolved_local)
                                                        except Exception:
                                                            pass
                                                except Exception:
                                                    pass

                                            if mgr_local and emote_id_local:
                                                emobj2_local = mgr_local.id_map.get(str(emote_id_local)) or {}
                                                url_local = mgr_local._select_image_url(emobj2_local) if emobj2_local else None
                                                ext_local = 'gif' if url_local and url_local.lower().endswith('.gif') else 'png'
                                                try:
                                                    cache_dir_local = getattr(mgr_local, 'cache_dir', None) or os.path.join('resources', 'emotes')
                                                except Exception:
                                                    cache_dir_local = os.path.join('resources', 'emotes')
                                                safe_fname_local = f"twitch_{emote_id_local}.{ext_local}"
                                                fpath_local = os.path.join(cache_dir_local, safe_fname_local)

                                                if fpath_local and os.path.exists(fpath_local):
                                                    abs_path_local = os.path.abspath(fpath_local).replace('\\', '/')
                                                    uri_used_local = f'file:///{abs_path_local}'
                                                else:
                                                    try:
                                                        uri_used_local = mgr_local.get_emote_data_uri(emote_id_local, broadcaster_id=broadcaster_id_local) if mgr_local else None
                                                    except Exception:
                                                        uri_used_local = None
                                        except Exception:
                                            uri_used_local = None

                                        if uri_used_local:
                                            final_has_img = True
                                            # Log emote resolution for diagnostics
                                            try:
                                                import time, os
                                                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                                    emid = emote_id_local or (emobj_local.get('id') if isinstance(emobj_local, dict) else None)
                                                    df.write(f"{time.time():.3f} QUEUE_EMOTE_URI message_id={message_id_snapshot} emote_id={emid} uri={uri_used_local}\n")
                                            except Exception:
                                                pass
                                            frag_parts_local.append(f'<img src="{uri_used_local}" alt="{html.escape(frag_local.get("text") or "emote")}" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />')
                                        else:
                                            # Insert a lightweight placeholder image so the
                                            # message can be rendered immediately and later
                                            # patched when the emote image is cached.
                                            try:
                                                placeholder = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=='
                                                emid_for_attr = html.escape(str(emote_id_local)) if emote_id_local else html.escape(str(frag_local.get('text') or ''))
                                                img_html = f'<img data-emote-id="{emid_for_attr}" src="{placeholder}" alt="{html.escape(frag_local.get("text") or "emote")}" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" class="emote placeholder" />'
                                                frag_parts_local.append(img_html)
                                                # Instrumentation: record placeholder insertion
                                                try:
                                                    import time, os
                                                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                                        df.write(f"{time.time():.3f} QUEUE_EMOTE_URI placeholder message_id={message_id_snapshot} emote_id={emote_id_local}\n")
                                                        try:
                                                            df.flush(); os.fsync(df.fileno())
                                                        except Exception:
                                                            pass
                                                except Exception:
                                                    pass
                                                # Best-effort: trigger background warming for this emote
                                                try:
                                                        if mgr_local and emote_id_local:
                                                            try:
                                                                # Determine any emote_set_id available from fragment or cached emobj
                                                                sid_local = None
                                                                try:
                                                                    sid_local = None
                                                                    if isinstance(emobj2_local, dict):
                                                                        sid_local = emobj2_local.get('emote_set_id') or emobj2_local.get('emote_set') or emobj2_local.get('set_id')
                                                                    # frag_local may include an 'emote' object with emote_set_id
                                                                    if not sid_local and isinstance(frag_local, dict):
                                                                        em_in_frag = frag_local.get('emote') if isinstance(frag_local.get('emote'), dict) else None
                                                                        sid_local = sid_local or (em_in_frag.get('emote_set_id') if em_in_frag else None) or frag_local.get('emote_set_id') or frag_local.get('emote_set') or frag_local.get('set_id')
                                                                except Exception:
                                                                    sid_local = None

                                                                # Use public helper to attempt immediate prefetch (background safe)
                                                                if hasattr(mgr_local, 'prefetch_emote_by_id'):
                                                                    try:
                                                                        if sid_local:
                                                                            mgr_local.prefetch_emote_by_id(emote_id_local, background=True, emote_set_ids=[sid_local])
                                                                        else:
                                                                            mgr_local.prefetch_emote_by_id(emote_id_local, background=True)
                                                                    except TypeError:
                                                                        # Older manager signature may not accept emote_set_ids
                                                                        mgr_local.prefetch_emote_by_id(emote_id_local, background=True)
                                                                else:
                                                                    # fallback to internal prefetch if helper missing
                                                                    import threading as _th
                                                                    _th.Thread(target=lambda: (mgr_local._prefetch_emote_images([emote_id_local]) if hasattr(mgr_local, '_prefetch_emote_images') else None), daemon=True).start()
                                                            except Exception:
                                                                pass
                                                except Exception:
                                                    pass
                                            except Exception:
                                                try:
                                                    frag_parts_local.append(html.escape(frag_local.get('text') or ''))
                                                except Exception:
                                                    frag_parts_local.append('')
                                        continue

                                    # Other fragment types
                                    frag_parts_local.append(html.escape(frag_local.get('text') or ''))
                                except Exception:
                                    try:
                                        frag_parts_local.append(html.escape(str(frag_local)))
                                    except Exception:
                                        frag_parts_local.append('')

                            final_message_html = ''.join(frag_parts_local)
                        except Exception:
                            final_message_html = None

                except Exception:
                    final_message_html = None

                if not final_message_html:
                    try:
                        from core.emotes import render_message
                        final_message_html, final_has_img = render_message(message_snapshot, None, metadata_snapshot)
                        if not final_message_html:
                            final_message_html = html.escape(message_snapshot)
                    except Exception:
                        try:
                            final_message_html = html.escape(message_snapshot)
                        except Exception:
                            final_message_html = ''

                final_parts.append(final_message_html)
                combined_html = ' '.join(final_parts)
                wrapped_local = f'<div class="message" data-message-id="{message_id_snapshot}" style="{bg_style_snapshot} padding: 2px 6px; border-radius: 4px; margin-bottom: 2px; cursor: pointer;">{combined_html}</div>'

                # Emit to main thread for DOM insertion
                try:
                    # Persist diagnostic: about to emit render_ready
                    try:
                        import time, os
                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} WORKER_EMIT_RENDER_READY message_id={message_id_snapshot} has_img={bool(final_has_img)}\n")
                    except Exception:
                        pass
                    # Attempt to emit the signal for normal operation; if that fails
                    # (cross-thread issues), fall back to pushing into the worker queue.
                    emitted_ok = False
                    try:
                        self.render_ready.emit(message_id_snapshot, wrapped_local, bool(final_has_img))
                        emitted_ok = True
                        # If there's no running Qt event loop (e.g., headless tests where
                        # initUI was stubbed), the queued connection won't dispatch.
                        # In that case, call the handler directly as a best-effort fallback.
                        try:
                            from PyQt6.QtCore import QCoreApplication
                            if QCoreApplication.instance() is None:
                                try:
                                    self._on_render_ready(message_id_snapshot, wrapped_local, bool(final_has_img))
                                except Exception:
                                    pass
                        except Exception:
                            # If PyQt6 not available or import fails, silently continue
                            try:
                                self._on_render_ready(message_id_snapshot, wrapped_local, bool(final_has_img))
                            except Exception:
                                pass
                    except Exception:
                        emitted_ok = False

                    # Only push into the worker queue fallback if emitting the
                    # queued signal failed; otherwise prefer the main-thread
                    # `render_ready` handler to enqueue JS execution.
                    try:
                        if not emitted_ok:
                            if getattr(self, '_worker_queue', None) is not None and getattr(self, '_worker_queue_lock', None) is not None:
                                try:
                                    with self._worker_queue_lock:
                                        already = False
                                        try:
                                            if message_id_snapshot and message_id_snapshot in self._queued_message_ids:
                                                already = True
                                        except Exception:
                                            already = False
                                        if not already:
                                            try:
                                                self._worker_queue.append((wrapped_local, message_id_snapshot, bool(final_has_img)))
                                                if message_id_snapshot:
                                                    try:
                                                        self._queued_message_ids.add(message_id_snapshot)
                                                    except Exception:
                                                        pass
                                                # Best-effort: if the main-thread timer isn't running (tests/headless),
                                                # try to drain the worker queue immediately so messages are inserted.
                                                try:
                                                    if not getattr(self, '_worker_queue_timer', None) or not getattr(self._worker_queue_timer, 'isActive', lambda: True)():
                                                        # call drain directly as a best-effort fallback
                                                        try:
                                                            self._drain_worker_queue()
                                                        except Exception:
                                                            pass
                                                except Exception:
                                                    pass
                                            except Exception:
                                                pass
                                except Exception:
                                    pass
                    except Exception:
                        pass
                except Exception:
                    # If signal emit fails, fall back to queueing JS directly (best-effort)
                    try:
                        import time, os, traceback
                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} WORKER_EMIT_EXCEPTION message_id={message_id_snapshot} err=emit_failed\n")
                    except Exception:
                        pass
                    try:
                        js_code_fallback = f"var chatBody = document.getElementById('chat-body'); if (chatBody) {{ chatBody.insertAdjacentHTML('beforeend', `{wrapped_local}`); window.scrollTo(0, document.body.scrollHeight); }} true;"
                        self._invoke_queue_js(js_code_fallback, message_id_snapshot)
                    except Exception:
                        pass
            except Exception:
                try:
                    import time, os, traceback
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} WORKER_EXCEPTION message_id={message_id_snapshot} err={repr(traceback.format_exc())}\n")
                except Exception:
                    pass

        # Determine background style (kept here so closure can use bg_style)
        bg_style = ''
        if self.background_style == 'Background':
            bg_style = 'background-color: #23272e;'
        elif self.background_style == 'Alternating':
            if self.message_count % 2 == 0:
                bg_style = 'background-color: #23272e;'
            else:
                bg_style = 'background-color: #181b20;'
            self.message_count += 1

        # Restore original has_img gating: wait for emote images to be available
        # before emitting to the DOM, but retry a few times in case emotes load
        # shortly after render. This was temporarily bypassed for diagnosis.
        def _emit_or_retry(attempt=1):
            try:
                final_has_img = (has_img is True)
            except Exception:
                final_has_img = False

            # If we have an image, emit now
            if final_has_img:
                emit_message(components, message_html, True)
                return

            # Otherwise retry up to 5 attempts with 200ms interval
            max_attempts = 5
            if attempt > max_attempts:
                # Give up and emit without images to avoid message loss
                emit_message(components, message_html, False)
                return

            # Retry attempt (instrumentation removed)

            # Schedule next retry
            try:
                QTimer.singleShot(200, lambda: _retry_emit(attempt + 1))
            except Exception:
                # If timers aren't available, fallback to immediate emit
                emit_message(components, message_html, False)

        def _retry_emit(attempt):
            # Re-run the renderer to check for images again (best-effort)
            try:
                from core.emotes import render_message
                m_html, m_has_img = render_message(message, emotes_tag, metadata)
            except Exception:
                m_html, m_has_img = message_html, False

            # If rendering changed the HTML, update local copy
            if m_html:
                try:
                    # update outer-scope message_html if possible
                    pass
                except Exception:
                    pass

            if m_has_img:
                emit_message(components, m_html, True)
            else:
                _emit_or_retry(attempt)

        # Kick off background render task so UI remains responsive
        try:
            import threading as _threading
            # Ensure worker queue exists even if `initUI` was stubbed in tests
            try:
                if not getattr(self, '_worker_queue', None):
                    self._worker_queue = []
                    import threading as _threading_local
                    self._worker_queue_lock = _threading_local.Lock()
                    self._worker_queue_timer = None
            except Exception:
                pass
            t = _threading.Thread(target=_render_worker, args=(components, bg_style, message_id, metadata, platform, username, message, user_color), daemon=True)
            t.start()
            # Persist diagnostic: thread started for render
            try:
                import time, os
                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                    df.write(f"{time.time():.3f} THREAD_START name={t.name} alive={t.is_alive()} message_id={message_id}\n")
            except Exception:
                pass
            self._render_threads.append(t)
        except Exception:
            # Fallback to immediate emit if threading unavailable
            try:
                import time, os
                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                    df.write(f"{time.time():.3f} THREAD_FALLBACK_INVOKE message_id={message_id}\n")
            except Exception:
                pass
            _render_worker(components, bg_style, message_id, metadata, platform, username, message, user_color)
    
    def togglePlatformIcons(self, state):
        """Toggle platform icon visibility"""
        old_state = self.show_platform_icons
        self.show_platform_icons = (state == Qt.CheckState.Checked.value)
        
        # Save setting to config
        if self.config:
            self.config.set('ui.show_platform_icons', self.show_platform_icons)
    
    def toggleUserColors(self, state):
        """Toggle username color display"""
        self.show_user_colors = (state == Qt.CheckState.Checked.value)
        
        # Save setting to config
        if self.config:
            self.config.set('ui.show_user_colors', self.show_user_colors)
    
    def toggleTimestamps(self, state):
        """Toggle timestamp display"""
        self.show_timestamps = (state == Qt.CheckState.Checked.value)
        
        # Save setting to config
        if self.config:
            self.config.set('ui.show_timestamps', self.show_timestamps)
    
    def toggleBadges(self, state):
        """Toggle badge display"""
        self.show_badges = (state == Qt.CheckState.Checked.value)
        
        # Save setting to config
        if self.config:
            self.config.set('ui.show_badges', self.show_badges)
    
    def changeBackgroundStyle(self, style):
        """Change background style for messages"""
        self.background_style = style
        
        # Reset message count when changing to alternating
        if style == "Alternating":
            self.message_count = 0
        
        # Save setting to config
        if self.config:
            self.config.set('ui.background_style', style)
    
    def clearChat(self):
        """Clear all chat messages."""
        js_code = "document.getElementById('chat-body').innerHTML = '';"
        self.chat_display.page().runJavaScript(js_code)
        self.message_data.clear()
        self.message_queue.clear()
        self.platform_message_id_map.clear()
        self.message_count = 0
        logger.info("Chat cleared")
    
    def _queueJavaScriptExecution(self, js_code, message_id=None):
        """Queue JavaScript execution to prevent message loss during high volume"""
        # Deduplicate by both internal message_id and platform message_id (if available)
        try:
            dedupe_keys = set()
            if message_id:
                dedupe_keys.add(message_id)
                try:
                    meta = self.message_data.get(message_id, {}).get('metadata', {})
                    platform_mid = meta.get('message_id') if isinstance(meta, dict) else None
                    if platform_mid:
                        dedupe_keys.add(platform_mid)
                except Exception:
                    platform_mid = None

            already = any(k in self._queued_message_ids for k in dedupe_keys if k)
            if already:
                try:
                    import time, os
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        # Log first available key for readability
                        log_key = next((k for k in dedupe_keys if k), message_id)
                        df.write(f"{time.time():.3f} QUEUE_DUPLICATE message_id={log_key}\n")
                        try:
                            df.flush(); os.fsync(df.fileno())
                        except Exception:
                            pass
                except Exception:
                    pass
                return

        except Exception:
            pass

        # Avoid enqueuing duplicate JS entries for the same message_id
        try:
            if message_id and any(item[1] == message_id for item in self.js_execution_queue):
                try:
                    import time, os
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} QUEUE_DUPLICATE message_id={message_id}\n")
                        try:
                            df.flush(); os.fsync(df.fileno())
                        except Exception:
                            pass
                except Exception:
                    pass
                return

        except Exception:
            pass

        # Support metadata-priority items which should be applied promptly
        try:
            PRIORITY_MARKER = '/*META_PRIORITY*/'
            priority = False
            js_to_enqueue = js_code
            if isinstance(js_code, str) and js_code.startswith(PRIORITY_MARKER):
                priority = True
                js_to_enqueue = js_code[len(PRIORITY_MARKER):]
        except Exception:
            priority = False
            js_to_enqueue = js_code

        # Force verbose diagnostics for metadata-like patches even when the
        # explicit priority marker is not present. This helps capture
        # IMMEDIATE_* events in logs during repro runs.
        try:
            import time, os
            maybe_meta = False
            try:
                maybe_meta = isinstance(js_to_enqueue, str) and ('data:image' in js_to_enqueue or 'setEmoteDataUri' in js_to_enqueue)
            except Exception:
                maybe_meta = False
            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
            os.makedirs(os.path.dirname(dlog), exist_ok=True)
            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                df.write(f"{time.time():.3f} IMMEDIATE_VERBOSE_DETECT priority={int(bool(priority))} maybe_meta={int(bool(maybe_meta))} message_id={message_id}\n")
                try:
                    df.flush(); os.fsync(df.fileno())
                except Exception:
                    pass
        except Exception:
            pass

        # If we didn't already mark this snippet as priority, promote
        # metadata-like patches (data URI or setEmoteDataUri) so they
        # can take the immediate execution path during repro/testing.
        try:
            if not priority:
                try:
                    is_meta_patch = isinstance(js_to_enqueue, str) and ('data:image' in js_to_enqueue or 'setEmoteDataUri' in js_to_enqueue)
                except Exception:
                    is_meta_patch = False
                if is_meta_patch:
                    priority = True
                    try:
                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} IMMEDIATE_PROMOTED_BY_META_PRECHECK message_id={message_id}\n")
                            try:
                                df.flush(); os.fsync(df.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    # Log when precheck did not promote - include snippet preview for diagnosis
                    try:
                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                        preview = (js_to_enqueue[:140] + '...') if isinstance(js_to_enqueue, str) and len(js_to_enqueue) > 140 else (js_to_enqueue if isinstance(js_to_enqueue, str) else '')
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} IMMEDIATE_PRECHECK_SKIPPED message_id={message_id} maybe_meta=0 preview={preview}\n")
                            try:
                                df.flush(); os.fsync(df.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass

        if priority:
            # Try to execute metadata-priority JS immediately if possible to
            # avoid being delayed by a busy queue. Fall back to inserting
            # at the front of the queue if immediate execution isn't possible.
            try:
                import time, os
                page = self.chat_display.page() if getattr(self, 'chat_display', None) else None
                # Diagnostic log for detection
                try:
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} QUEUE_EMOTE_URI_META_DETECTED message_id={message_id} page_present={bool(page)} pending_js={self.pending_js_count} max_pending_js={self.max_pending_js}\n")
                        try:
                            df.flush(); os.fsync(df.fileno())
                        except Exception:
                            pass
                except Exception:
                    pass

                # Clean up timestamps older than 1s
                try:
                    now = time.time()
                    self._immediate_call_timestamps = [t for t in self._immediate_call_timestamps if t > now - 1]
                except Exception:
                    now = time.time()

                # If we have a page, attempt immediate execution subject to simple rate limiting.
                if page:
                    recent = len(self._immediate_call_timestamps)
                    # Detect tiny metadata/data-uri patches and apply a higher per-second quota for them
                    try:
                        is_meta_patch = isinstance(js_to_enqueue, str) and ('data:image' in js_to_enqueue or 'setEmoteDataUri' in js_to_enqueue)
                    except Exception:
                        is_meta_patch = False
                    # Promote metadata-like patches to priority so the immediate-path
                    # instrumentation (IMMEDIATE_* logs) runs during repro/testing.
                    try:
                        if is_meta_patch:
                            priority = True
                            # small diagnostic so logs show promotion source
                            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                            os.makedirs(os.path.dirname(dlog), exist_ok=True)
                            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                df.write(f"{time.time():.3f} IMMEDIATE_PROMOTED_BY_META message_id={message_id}\n")
                                try:
                                    df.flush(); os.fsync(df.fileno())
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    limit = getattr(self, '_meta_immediate_rate_limit' if is_meta_patch else '_immediate_rate_limit', 40 if is_meta_patch else 20)
                    # Instrumentation (include which limit we're using)
                    try:
                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} IMMEDIATE_CALL_ATTEMPT message_id={message_id} recent={recent} limit={limit} meta_patch={int(is_meta_patch)}\n")
                            try:
                                df.flush(); os.fsync(df.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # If forced by env, bypass the recent<limit check
                    try:
                        env_force = bool(os.environ.get('AZB_FORCE_IMMEDIATE') in ('1', 'true', 'True'))
                    except Exception:
                        env_force = False

                    if env_force or recent < limit:
                        # Run JS directly with a lightweight callback
                        def _immediate_cb(result):
                            try:
                                self.pending_js_count = max(0, self.pending_js_count - 1)
                            except Exception:
                                pass
                            try:
                                if message_id:
                                    try:
                                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                            df.write(f"{time.time():.3f} IMMEDIATE_SUCCESS message_id={message_id}\n")
                                            try:
                                                df.flush(); os.fsync(df.fileno())
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                                    try:
                                        self.message_rendered.emit(message_id or '')
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                            # Continue processing queue if items remain
                            try:
                                if self.js_execution_queue:
                                    self._processNextJavaScript()
                            except Exception:
                                pass

                        try:
                            # record timestamp then attempt run
                            try:
                                self._immediate_call_timestamps.append(now)
                            except Exception:
                                pass
                            self.pending_js_count += 1
                            try:
                                self._run_js_with_diagnostics(page, js_to_enqueue, _immediate_cb, message_id=message_id, tag='IMMEDIATE_CALL', timeout_ms=3000)
                                return
                            except Exception:
                                # Fallback if wrapper fails
                                try:
                                    page.runJavaScript(js_to_enqueue, _immediate_cb)
                                    return
                                except Exception:
                                    pass
                        except Exception:
                            # log failure and fall back to queue insertion
                            try:
                                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                    df.write(f"{time.time():.3f} IMMEDIATE_CALL_FAIL message_id={message_id}\n")
                                    try:
                                        df.flush(); os.fsync(df.fileno())
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    else:
                        # Rate limit hit, fall back to front-insert and log which limit prevented execution
                        try:
                            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                            os.makedirs(os.path.dirname(dlog), exist_ok=True)
                            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                df.write(f"{time.time():.3f} IMMEDIATE_RATE_LIMIT message_id={message_id} recent={recent} limit={limit} meta_patch={int(is_meta_patch)}\n")
                                try:
                                    df.flush(); os.fsync(df.fileno())
                                except Exception:
                                    pass
                        except Exception:
                            pass
                else:
                    # No page available to run JS immediately
                    try:
                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} IMMEDIATE_NO_PAGE message_id={message_id}\n")
                            try:
                                df.flush(); os.fsync(df.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass

            except Exception:
                pass

            # Insert at front so small metadata-driven patches run ASAP
            try:
                self.js_execution_queue.insert(0, (js_to_enqueue, message_id))
            except Exception:
                self.js_execution_queue.append((js_to_enqueue, message_id))
        else:
            self.js_execution_queue.append((js_to_enqueue, message_id))
        # Record both keys (internal and platform) to avoid duplicate insertion
        try:
            if message_id:
                self._queued_message_ids.add(message_id)
                try:
                    import time, os
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} QUEUE_ADD message_id={message_id}\n")
                        try:
                            df.flush(); os.fsync(df.fileno())
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    meta = self.message_data.get(message_id, {}).get('metadata', {})
                    platform_mid = meta.get('message_id') if isinstance(meta, dict) else None
                    if platform_mid and str(platform_mid) != str(message_id):
                        self._queued_message_ids.add(platform_mid)
                        try:
                            import time, os
                            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                            os.makedirs(os.path.dirname(dlog), exist_ok=True)
                            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                df.write(f"{time.time():.3f} QUEUE_ADD message_id={platform_mid}\n")
                                try:
                                    df.flush(); os.fsync(df.fileno())
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        
        # Warn if queue is getting large
        queue_size = len(self.js_execution_queue)
        if queue_size > 50:
            logger.warning(f"⚠️ JavaScript queue size: {queue_size} - Possible message delay or drops")
        elif queue_size > 100:
            logger.error(f"⚠️⚠️ CRITICAL: JavaScript queue size: {queue_size} - Messages likely being dropped!")
        
        # Queue state updated (instrumentation removed)

        # Start processing if not already running and under pending limit
        try:
            import time, os
            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
            os.makedirs(os.path.dirname(dlog), exist_ok=True)
            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                df.write(f"{time.time():.3f} QUEUE_STATUS is_processing={self.is_processing_js} pending_js_count={self.pending_js_count} max_pending_js={self.max_pending_js} queue_size={queue_size}\n")
        except Exception:
            pass

        if not self.is_processing_js and self.pending_js_count < self.max_pending_js:
            try:
                import time, os
                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                    df.write(f"{time.time():.3f} INVOKE_PROCESS message_id={message_id}\n")
            except Exception:
                pass
            self._processNextJavaScript()
        else:
            try:
                import time, os
                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                    df.write(f"{time.time():.3f} SKIP_PROCESS message_id={message_id} is_processing={self.is_processing_js} pending_js_count={self.pending_js_count} max_pending_js={self.max_pending_js}\n")
            except Exception:
                pass
    
    def _processNextJavaScript(self):
        """Process the next JavaScript execution from queue"""
        if not self.js_execution_queue:
            self.is_processing_js = False
            return
        
        self.is_processing_js = True
        js_code, message_id = self.js_execution_queue.pop(0)
        # Persist diagnostic: processing this queued JS entry
        try:
            import time, os
            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
            os.makedirs(os.path.dirname(dlog), exist_ok=True)
            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                df.write(f"{time.time():.3f} PROCESS message_id={message_id}\n")
        except Exception:
            pass
        
        self.pending_js_count += 1
        retry_count = getattr(self, '_js_retry_count', {})
        
        # Execute with callback to track completion
        def on_complete(result):
            self.pending_js_count -= 1

            # JS execution completed (instrumentation removed)
            
            if result is None or result is False:
                # Execution failed - retry up to 3 times
                current_retries = retry_count.get(message_id, 0)
                if current_retries < 3 and message_id:
                    retry_count[message_id] = current_retries + 1
                    logger.warning(f"⚠️ JS execution failed for {message_id}, retry {current_retries + 1}/3")
                    # Re-queue at front for immediate retry
                    self.js_execution_queue.insert(0, (js_code, message_id))
                else:
                    if message_id:
                        logger.error(f"✗ JS execution failed permanently for {message_id} - MESSAGE DROPPED")
                        # Clean up retry counter
                        retry_count.pop(message_id, None)
                        # Persist diagnostic for dropped message
                        try:
                            import time, os
                            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                            os.makedirs(os.path.dirname(dlog), exist_ok=True)
                            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                df.write(f"{time.time():.3f} DROPPED message_id={message_id}\n")
                                try:
                                    df.flush()
                                    os.fsync(df.fileno())
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        try:
                            # Remove both internal and platform keys
                            self._queued_message_ids.discard(message_id)
                            try:
                                meta = self.message_data.get(message_id, {}).get('metadata', {})
                                platform_mid = meta.get('message_id') if isinstance(meta, dict) else None
                                if platform_mid:
                                    self._queued_message_ids.discard(platform_mid)
                            except Exception:
                                pass
                        except Exception:
                            pass
            else:
                # Success - clean up retry counter
                if message_id:
                    retry_count.pop(message_id, None)
                    # Persist diagnostic for successful JS execution
                    try:
                        import time, os
                        dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                        os.makedirs(os.path.dirname(dlog), exist_ok=True)
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} SUCCESS message_id={message_id}\n")
                            try:
                                df.flush()
                                os.fsync(df.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        # Remove both internal and platform keys from dedupe set
                        self._queued_message_ids.discard(message_id)
                        try:
                            import time, os
                            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                            os.makedirs(os.path.dirname(dlog), exist_ok=True)
                            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                df.write(f"{time.time():.3f} QUEUE_REMOVE message_id={message_id}\n")
                                try:
                                    df.flush(); os.fsync(df.fileno())
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        try:
                            meta = self.message_data.get(message_id, {}).get('metadata', {})
                            platform_mid = meta.get('message_id') if isinstance(meta, dict) else None
                            if platform_mid:
                                self._queued_message_ids.discard(platform_mid)
                                try:
                                    import time, os
                                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                        df.write(f"{time.time():.3f} QUEUE_REMOVE message_id={platform_mid}\n")
                                        try:
                                            df.flush(); os.fsync(df.fileno())
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    except Exception:
                        pass
                # Notify listeners/tests that a message was rendered
                try:
                    # Emit message_id if available, else empty string
                    self.message_rendered.emit(message_id or '')
                except Exception:
                    pass
            
            # Process next item in queue
            if self.js_execution_queue:
                self._processNextJavaScript()
            else:
                self.is_processing_js = False
        
        try:
            # Persist diagnostic: invoked runJavaScript call
            try:
                import time, os
                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                    df.write(f"{time.time():.3f} CALL message_id={message_id}\n")
                    try:
                        df.flush()
                        os.fsync(df.fileno())
                    except Exception:
                        pass
            except Exception:
                pass
            # Ensure we have a page to run JS on; log and raise if missing
            page = self.chat_display.page() if self.chat_display else None
            if not page:
                try:
                    import time, os
                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} NO_PAGE message_id={message_id}\n")
                except Exception:
                    pass
                raise RuntimeError("No QWebEnginePage available for runJavaScript")
            # Use diagnostic wrapper to capture callback entry/result and timeouts
            try:
                self._run_js_with_diagnostics(page, js_code, on_complete, message_id=message_id, tag='QUEUED_CALL', timeout_ms=5000)
            except Exception:
                # Fallback to direct call if wrapper fails
                page.runJavaScript(js_code, on_complete)
        except Exception as e:
            logger.error(f"✗ Exception executing JavaScript: {e}")
            try:
                import time, os
                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                    df.write(f"{time.time():.3f} EXCEPTION_JS message_id={message_id} err={repr(e)}\n")
                    try:
                        df.flush()
                        os.fsync(df.fileno())
                    except Exception:
                        pass
            except Exception:
                pass
            import traceback
            traceback.print_exc()
            # If the underlying QWebEngineView has been deleted, don't retry
            # endlessly - clear the queue and stop processing.
            msg = str(e) or ''
            if 'has been deleted' in msg or 'wrapped C/C++ object' in msg:
                try:
                    # Drop entire queue - view is gone
                    self.js_execution_queue.clear()
                except Exception:
                    pass
                self.pending_js_count = max(0, self.pending_js_count - 1)
                self.is_processing_js = False
                try:
                    self._queued_message_ids.clear()
                except Exception:
                    pass
                return

            # Retry logic for other transient exceptions
            self.pending_js_count = max(0, self.pending_js_count - 1)
            current_retries = retry_count.get(message_id, 0)
            if current_retries < 3 and message_id:
                retry_count[message_id] = current_retries + 1
                self.js_execution_queue.insert(0, (js_code, message_id))

            # Continue processing queue
            if self.js_execution_queue:
                self._processNextJavaScript()
            else:
                self.is_processing_js = False
        
        # Store retry counter
        if not hasattr(self, '_js_retry_count'):
            self._js_retry_count = {}
        self._js_retry_count = retry_count

    def _invoke_queue_js(self, js_code, message_id=None):
        """Invoke the queued JS execution function safely.

        This helper handles cases where tests monkeypatch `ChatPage._queueJavaScriptExecution`
        with a plain function (no `self` parameter). It will attempt the normal bound
        call first, and fall back to calling the class attribute as an unbound
        function if that raises a TypeError due to signature mismatch.
        """
        try:
            try:
                return self._queueJavaScriptExecution(js_code, message_id)
            except TypeError:
                # Possibly replaced by an unbound function in tests; call via class
                try:
                    return type(self)._queueJavaScriptExecution(js_code, message_id)
                except Exception:
                    # Last resort: try calling with only js_code
                    try:
                        return self._queueJavaScriptExecution(js_code)
                    except Exception:
                        return None
        except Exception:
            return None

    def _run_js_with_diagnostics(self, page, js, callback=None, message_id=None, tag='CALL', timeout_ms=5000):
        """Run `page.runJavaScript` while logging callback entry/result and timeouts.

        - `tag` is an identifier added to log lines for easier grepping.
        - `timeout_ms` specifies how long to wait before emitting a timeout diagnostic
          if the JavaScript callback hasn't fired.
        """
        try:
            import time, os, traceback
            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
            os.makedirs(os.path.dirname(dlog), exist_ok=True)
        except Exception:
            dlog = None

        invoked = {'called': False}

        def _internal_cb(result):
            try:
                invoked['called'] = True
            except Exception:
                pass
            try:
                if dlog:
                    try:
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} JS_CALLBACK_ENTER tag={tag} message_id={message_id} result={repr(result)}\n")
                            try:
                                df.flush(); os.fsync(df.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                if callback:
                    try:
                        callback(result)
                    except Exception:
                        if dlog:
                            try:
                                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                    df.write(f"{time.time():.3f} JS_CALLBACK_EXCEPTION tag={tag} message_id={message_id} err={repr(traceback.format_exc())}\n")
                                    try:
                                        df.flush(); os.fsync(df.fileno())
                                    except Exception:
                                        pass
                            except Exception:
                                pass
            except Exception:
                pass

        try:
            # Wrap arbitrary JS in a safe IIFE so it always returns a value
            # and any exceptions are caught and surface to the Python callback.
            try:
                wrapped_js = (
                    "(function(){ try{ " + js + " ; return true; } catch(e) {"
                    " console.error('AZB_JS_EXCEPTION', e); return 'AZB_EXN:' + String(e); } })()"
                )
            except Exception:
                # Fallback: if concatenation fails for any reason, use original js
                wrapped_js = js

            page.runJavaScript(wrapped_js, _internal_cb)
            # Log that runJavaScript was invoked successfully (callback may still not fire)
            try:
                if dlog:
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} JS_INVOKED tag={tag} message_id={message_id}\n")
                        try:
                            df.flush(); os.fsync(df.fileno())
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception as e:
            # Log runJavaScript invocation failure
            try:
                if dlog:
                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                        df.write(f"{time.time():.3f} JS_RUN_EXCEPTION tag={tag} message_id={message_id} err={repr(e)}\n")
                        try:
                            df.flush(); os.fsync(df.fileno())
                        except Exception:
                            pass
            except Exception:
                pass
            raise

        # Schedule a timeout diagnostic if callback not invoked
        try:
            def _timeout():
                try:
                    if not invoked.get('called'):
                        if dlog:
                            try:
                                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                    df.write(f"{time.time():.3f} JS_CALLBACK_TIMEOUT tag={tag} message_id={message_id} timeout_ms={timeout_ms}\n")
                                    try:
                                        df.flush(); os.fsync(df.fileno())
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                except Exception:
                    pass

            QTimer.singleShot(timeout_ms, _timeout)
        except Exception:
            pass

    def _drain_worker_queue(self):
        """Drain items pushed by background render workers into the main thread."""
        try:
            if not getattr(self, '_worker_queue', None):
                return
            try:
                # Pop all available items under lock and process them on main thread
                with self._worker_queue_lock:
                    items = list(self._worker_queue)
                    self._worker_queue.clear()
            except Exception:
                items = []

            for wrapped_local, message_id_snapshot, final_has_img in items:
                try:
                    js_code_fallback = f"var chatBody = document.getElementById('chat-body'); if (chatBody) {{ chatBody.insertAdjacentHTML('beforeend', `{wrapped_local}`); window.scrollTo(0, document.body.scrollHeight); }} true;"
                    self._invoke_queue_js(js_code_fallback, message_id_snapshot)
                except Exception:
                    pass
        except Exception:
            pass
    
    def togglePause(self):
        """Toggle pause/unpause for message display"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.pause_btn.setText("▶ Resume")
            logger.info(f"Message display paused. Queuing new messages...")
        else:
            self.pause_btn.setText("⏸ Pause")
            logger.info(f"Message display resumed. Displaying {len(self.message_queue)} queued messages...")
            
            # Display all queued messages
            while self.message_queue:
                platform, username, message, metadata = self.message_queue.pop(0)
                self._displayMessage(platform, username, message, metadata)
    
    def _on_render_ready(self, message_id, wrapped_html, final_has_img):
        """Handle insertion of rendered HTML into the DOM on the main thread."""
        try:
            js_code_local = f"var chatBody = document.getElementById('chat-body'); if (chatBody) {{ chatBody.insertAdjacentHTML('beforeend', `{wrapped_html}`); var messages = chatBody.querySelectorAll('.message'); var newMessage = messages[messages.length - 1]; newMessage.classList.add('message-slide-in'); setTimeout(function() {{ newMessage.classList.remove('message-slide-in'); newMessage.classList.add('message-wiggle'); setTimeout(function() {{ newMessage.classList.remove('message-wiggle'); }}, 2000); }}, 800); window.scrollTo(0, document.body.scrollHeight); }} true;"
            self._invoke_queue_js(js_code_local, message_id)

            # After inserting the message, proactively check for any placeholders
            # that might already be cached (race: emote cached before DOM insert).
            try:
                page = self.chat_display.page() if self.chat_display else None
                if page:
                    js_find = f'''(function() {{ var node = document.querySelector('.message[data-message-id="{message_id}"]'); if(!node) return []; var imgs = node.querySelectorAll('img[data-emote-id]'); return Array.from(imgs).map(i => i.getAttribute('data-emote-id')); }})()'''

                    def _cb(ids):
                        try:
                            if not ids:
                                return
                            try:
                                from core.twitch_emotes import get_manager as _get_twitch_manager
                                mgr = _get_twitch_manager() if _get_twitch_manager is not None else None
                            except Exception:
                                mgr = None
                            if not mgr:
                                return
                            for emid in ids:
                                try:
                                    if not emid:
                                        continue
                                    data_uri = mgr.get_emote_data_uri(str(emid))
                                    if not data_uri:
                                        continue
                                    safe_uri = data_uri.replace('\\', '\\\\').replace('"', '\\"')
                                    js_set = f'''(function() {{ try {{ var imgs = document.querySelectorAll('.message[data-message-id="{message_id}"] img[data-emote-id="{emid}"]'); for(var i=0;i<imgs.length;i++){{ try{{ imgs[i].src="{safe_uri}"; imgs[i].classList.remove('placeholder'); }}catch(e){{}} }} }}catch(e){{}} }})()'''
                                    try:
                                        self._invoke_queue_js(js_set, None)
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    try:
                        try:
                            self._run_js_with_diagnostics(page, js_find, _cb, message_id=message_id, tag='FIND_PLACEHOLDERS', timeout_ms=2000)
                        except Exception:
                            page.runJavaScript(js_find, _cb)
                    except Exception:
                        pass
            except Exception:
                pass

            # (Direct run bypass removed — rely on queued execution and worker queue)

            # Notify overlay_server if available (best-effort)
            try:
                meta = self.message_data.get(message_id, {}).get('metadata', {})
                platform = self.message_data.get(message_id, {}).get('platform')
                username = self.message_data.get(message_id, {}).get('username')
                message_text = self.message_data.get(message_id, {}).get('message')
                is_event_local = meta.get('event_type') is not None
                if self.overlay_server and not is_event_local and final_has_img:
                    badges = meta.get('badges', [])
                    color = meta.get('color') if self.show_user_colors else None
                    self.overlay_server.add_message(platform, username, message_text, message_id, badges, color)
            except Exception:
                pass

            try:
                self.message_rendered.emit(message_id or '')
            except Exception:
                pass
        except Exception:
            pass

    def _on_emote_image_cached(self, payload):
        """Handle emote cache events and replace placeholder images in-place.

        Payload is expected to be a dict with at least 'emote_id'.
        """
        try:
            if not payload:
                return
            emote_id = str(payload.get('emote_id') or payload.get('id') or '')
            if not emote_id:
                return
            # Get manager to convert cached file to data URI (cache-first)
            try:
                from core.twitch_emotes import get_manager as _get_twitch_manager
                mgr = _get_twitch_manager() if _get_twitch_manager is not None else None
            except Exception:
                mgr = None

            if not mgr:
                return

            try:
                data_uri = mgr.get_emote_data_uri(emote_id)
            except Exception:
                data_uri = None

            if not data_uri:
                return

            # Instrumentation: log update
            try:
                import time, os
                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                    df.write(f"{time.time():.3f} QUEUE_EMOTE_URI update emote_id={emote_id}\n")
                    try:
                        df.flush(); os.fsync(df.fileno())
                    except Exception:
                        pass
            except Exception:
                pass

            # Escape double-quotes and backslashes in the URI for safe JS embedding
            try:
                safe_uri = data_uri.replace('\\', '\\\\').replace('"', '\\"')
            except Exception:
                safe_uri = data_uri

            js = f'''(function() {{
                try {{
                    var imgs = document.querySelectorAll('img[data-emote-id="{emote_id}"]');
                    for (var i=0;i<imgs.length;i++) {{
                        try {{ imgs[i].src = "{safe_uri}"; imgs[i].classList.remove('placeholder'); }} catch(e){{}}
                    }}
                }} catch(e) {{}}
            }})();'''

            # Queue JS execution on main thread
            try:
                self._invoke_queue_js(js, None)
            except Exception:
                pass
        except Exception:
            pass

    def _on_emote_set_metadata_ready(self, payload):
        """Handle early metadata-ready emits: attempt lightweight patching for emote_ids.

        Payload expected to include an 'emote_ids' iterable or 'emote_ids' key.
        """
        try:
            # Diagnostic: log that handler was invoked and payload summary
            try:
                import time, os, json
                dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                os.makedirs(os.path.dirname(dlog), exist_ok=True)
                with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                    try:
                        short = json.dumps(payload) if payload and isinstance(payload, (dict, list, tuple)) else str(payload)
                    except Exception:
                        short = str(payload)
                    df.write(f"{time.time():.3f} META_HANDLER_CALLED payload={short}\n")
                    try:
                        df.flush(); os.fsync(df.fileno())
                    except Exception:
                        pass
            except Exception:
                pass
            if not payload:
                return
            emote_ids = payload.get('emote_ids') if isinstance(payload, dict) else None
            if not emote_ids:
                # payload may be a tuple/list of ids
                if isinstance(payload, (list, tuple)):
                    emote_ids = payload
                else:
                    return

            try:
                from core.twitch_emotes import get_manager as _get_twitch_manager
                mgr = _get_twitch_manager() if _get_twitch_manager is not None else None
            except Exception:
                mgr = None

            if not mgr:
                return

            import time, os
            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
            os.makedirs(os.path.dirname(dlog), exist_ok=True)

            for eid in list(emote_ids)[:200]:
                try:
                    emote_id = str(eid)
                    data_uri = None
                    try:
                        data_uri = mgr.get_emote_data_uri(emote_id)
                    except Exception:
                        data_uri = None

                    if not data_uri:
                        continue

                    # instrumentation
                    try:
                        with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                            df.write(f"{time.time():.3f} QUEUE_EMOTE_URI meta emote_id={emote_id}\n")
                            try:
                                df.flush(); os.fsync(df.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass

                    safe_uri = data_uri.replace('\\', '\\\\').replace('"', '\\"')
                    # Mark this JS as metadata-priority so it can bypass queue delays
                    js_body = f'''(function() {{
                        try {{
                            var imgs = document.querySelectorAll('img[data-emote-id="{emote_id}"]');
                            for (var i=0;i<imgs.length;i++) {{
                                try {{ imgs[i].src = "{safe_uri}"; imgs[i].classList.remove('placeholder'); }} catch(e){{}}
                            }}
                        }} catch(e) {{}}
                    }})();'''

                    js = '/*META_PRIORITY*/' + js_body

                    try:
                        self._invoke_queue_js(js, None)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

    def emote_prefetch_sync(self, emote_set_ids=None, broadcaster_id=None, timeout_s=10):
        """Synchronous, blocking emote set prefetch helper.

        Best-effort: calls the `TwitchEmoteManager.fetch_emote_sets` if a manager
        is available. This blocks the calling thread until the fetch returns
        or an exception occurs. Use sparingly; preferred to run inside a
        background worker thread (the render worker already supports this).

        Returns True on success, False on failure.
        """
        try:
            if not emote_set_ids:
                return False
            try:
                from core.twitch_emotes import get_manager as _get_twitch_manager
                mgr = _get_twitch_manager() if _get_twitch_manager is not None else None
            except Exception:
                mgr = None

            if not mgr:
                return False

            # Perform blocking fetch
            try:
                mgr.fetch_emote_sets(list(emote_set_ids))
                return True
            except Exception:
                return False
        except Exception:
            return False
    
    def showContextMenu(self, pos):
        """Show context menu for message moderation"""
        def handle_message_id(message_id):
            logger.debug(f"Context menu - message_id: {message_id}")
            logger.debug(f"Available message IDs: {list(self.message_data.keys())}")
            
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 20px;
                }
                QMenu::item:selected {
                    background-color: #4a90e2;
                }
                QMenu::separator {
                    background-color: #3d3d3d;
                    height: 1px;
                    margin: 3px 0px;
                }
            """)
            
            # If a message is selected, show actions for that specific message
            if message_id and message_id in self.message_data:
                msg_data = self.message_data[message_id]
                username = msg_data['username']
                platform = msg_data['platform']
                
                logger.debug(f"Showing context menu for message from {username} on {platform}")
                
                # Delete message action
                delete_action = QAction(f"Delete Message", self)
                delete_action.triggered.connect(lambda: self.deleteMessage(message_id))
                menu.addAction(delete_action)
                
                # Ban user action
                ban_action = QAction(f"Ban User: {username}", self)
                ban_action.triggered.connect(lambda: self.banUser(message_id))
                menu.addAction(ban_action)
                
                # View message JSON (pretty-print)
                def _view_message_json():
                    try:
                        msg_obj = self.message_data.get(message_id, {})
                        pretty = json.dumps(msg_obj, indent=2, ensure_ascii=False, default=str)
                        try:
                            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
                            dlg = QDialog(self)
                            dlg.setWindowTitle('Message JSON')
                            dlg.setMinimumSize(640, 420)
                            layout = QVBoxLayout(dlg)
                            te = QTextEdit()
                            te.setReadOnly(True)
                            te.setPlainText(pretty)
                            layout.addWidget(te)
                            btn = QPushButton('Close')
                            btn.clicked.connect(dlg.accept)
                            layout.addWidget(btn)
                            dlg.exec()
                        except Exception:
                            # Fallback for headless/tests: show truncated in info box
                            QMessageBox.information(self, 'Message JSON', pretty[:2000])
                    except Exception as e:
                        try:
                            logger.exception(f"Error showing message JSON: {e}")
                        except Exception:
                            pass

                view_json_action = QAction('View Message JSON', self)
                view_json_action.triggered.connect(_view_message_json)
                menu.addAction(view_json_action)

                menu.addSeparator()
                
                # Block selected text from this message
                block_selection_action = QAction("Block Selected Text", self)
                block_selection_action.triggered.connect(lambda: self.blockSelectedText())
                menu.addAction(block_selection_action)
            else:
                logger.debug(f"No message selected or message not found")
                # No message selected - show general actions
                # Block selected text action
                block_selection_action = QAction("Block Selected Text", self)
                block_selection_action.triggered.connect(lambda: self.blockSelectedText())
                menu.addAction(block_selection_action)
            
            # Block custom term action (always available)
            block_custom_action = QAction("Block Custom Term...", self)
            block_custom_action.triggered.connect(self.blockCustomTerm)
            menu.addAction(block_custom_action)
            
            menu.addSeparator()
            
            # View blocked terms action (always available)
            view_blocked_action = QAction("View Blocked Terms...", self)
            view_blocked_action.triggered.connect(self.viewBlockedTerms)
            menu.addAction(view_blocked_action)
            
            menu.exec(self.chat_display.mapToGlobal(pos))
        
        # Get the selected message ID from JavaScript
        self.chat_display.page().runJavaScript("window.selectedMessageId", handle_message_id)
    
    def deleteMessage(self, message_id):
        """Delete a message from the chat"""
        if message_id not in self.message_data:
            return
        
        msg_data = self.message_data[message_id]
        platform = msg_data['platform']
        
        # Remove message from UI completely
        js_code = f"""
            var msg = document.querySelector('[data-message-id="{message_id}"]');
            if (msg) {{
                msg.remove();
            }}
        """
        self.chat_display.page().runJavaScript(js_code)
        
        # Remove from reverse lookup map
        platform_msg_id = msg_data['metadata'].get('message_id')
        if platform_msg_id:
            map_key = f"{platform}:{platform_msg_id}"
            self.platform_message_id_map.pop(map_key, None)
        
        # Remove from message_data
        del self.message_data[message_id]
        
        # Send deletion to overlay server
        if self.overlay_server:
            self.overlay_server.remove_message(message_id)
        
        # Try to delete from platform (if supported)
        if self.chat_manager and hasattr(self.chat_manager, 'deleteMessage'):
            self.chat_manager.deleteMessage(platform, msg_data['metadata'].get('message_id'))
        
        logger.info(f"Deleted message: {message_id}")

    def dump_chat_body(self, filename=None):
        """Write the current `#chat-body` innerHTML to a file for debugging."""
        try:
            import os
            if filename is None:
                filename = os.path.join(os.getcwd(), 'logs', 'chat_body_snapshot.html')
            js = "document.getElementById('chat-body') ? document.getElementById('chat-body').innerHTML : ''"

            def _cb(html):
                try:
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(html or '')
                except Exception:
                    pass

            page = self.chat_display.page() if self.chat_display else None
            if page:
                try:
                    page.runJavaScript(js, _cb)
                except Exception:
                    # Older Qt versions may not accept callback; try synchronous-ish fallback
                    try:
                        html = page.toHtml()
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(html or '')
                    except Exception:
                        pass
        except Exception:
            pass
    
    def onPlatformMessageDeleted(self, platform: str, platform_message_id: str):
        """Handle message deletion event from platform (moderator or auto-moderation)"""
        # Look up our internal message ID from the platform's message ID
        map_key = f"{platform}:{platform_message_id}"
        message_id = self.platform_message_id_map.get(map_key)
        
        if not message_id or message_id not in self.message_data:
            logger.debug(f"Platform deleted unknown message: {platform}:{platform_message_id}")
            return
        
        logger.info(f"Platform deleted message: {platform}:{platform_message_id} (internal: {message_id})")
        
        # Remove message from UI
        js_code = f"""
            var msg = document.querySelector('[data-message-id="{message_id}"]');
            if (msg) {{
                msg.style.opacity = '0.3';
                msg.style.textDecoration = 'line-through';
                setTimeout(function() {{
                    msg.remove();
                }}, 500);
            }}
        """
        self.chat_display.page().runJavaScript(js_code)
        
        # Clean up tracking
        self.platform_message_id_map.pop(map_key, None)
        del self.message_data[message_id]
        
        # Send deletion to overlay server
        if self.overlay_server:
            self.overlay_server.remove_message(message_id)
    
    def banUser(self, message_id):
        """Ban a user"""
        if message_id not in self.message_data:
            return
        
        msg_data = self.message_data[message_id]
        username = msg_data['username']
        platform = msg_data['platform']
        
        reply = QMessageBox.question(
            self,
            "Ban User",
            f"Ban user '{username}' from {platform}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Try to ban on platform (if supported)
            if self.chat_manager and hasattr(self.chat_manager, 'banUser'):
                self.chat_manager.banUser(platform, username, msg_data['metadata'].get('user_id'))
            
            logger.info(f"Banned user: {username} on {platform}")
            QMessageBox.information(self, "User Banned", f"User '{username}' has been banned.")
    
    def blockSelectedText(self):
        """Block selected text as a term and delete the message from the platform"""
        def handle_selected_text(text):
            if text and text.strip():
                self.blocked_terms_manager.add_term(text.strip())
                
                # Get the currently selected message ID to delete it from the platform
                def handle_message_id(message_id):
                    if message_id and message_id in self.message_data:
                        msg_data = self.message_data[message_id]
                        platform = msg_data['platform']
                        platform_msg_id = msg_data['metadata'].get('message_id')
                        
                        # Delete from platform if supported
                        if self.chat_manager and hasattr(self.chat_manager, 'deleteMessage') and platform_msg_id:
                            success = self.chat_manager.deleteMessage(platform, platform_msg_id)
                            if success:
                                logger.info(f"Deleted message from {platform} after blocking term: '{text.strip()}'")
                            else:
                                logger.warning(f"Could not delete message from {platform} (not supported or failed)")
                
                self.chat_display.page().runJavaScript("window.selectedMessageId", handle_message_id)
                
                QMessageBox.information(
                    self,
                    "Term Blocked",
                    f"Blocked term: '{text.strip()}'\nMessage deleted from platform."
                )
        
        self.chat_display.page().runJavaScript("window.getSelection().toString()", handle_selected_text)
    
    def blockCustomTerm(self):
        """Block a custom term"""
        term, ok = QInputDialog.getText(
            self,
            "Block Term",
            "Enter word or phrase to block:"
        )
        
        if ok and term.strip():
            self.blocked_terms_manager.add_term(term.strip())
            QMessageBox.information(
                self,
                "Term Blocked",
                f"Blocked term: '{term.strip()}'"
            )
    
    def viewBlockedTerms(self):
        """View and manage blocked terms"""
        terms = self.blocked_terms_manager.get_blocked_terms()
        
        if not terms:
            QMessageBox.information(self, "Blocked Terms", "No blocked terms.")
            return
        
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QHBoxLayout
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Blocked Terms")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)
        
        layout = QVBoxLayout()
        
        # List widget
        list_widget = QListWidget()
        list_widget.addItems(terms)
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
            }
        """)
        layout.addWidget(list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        remove_btn.clicked.connect(lambda: self._removeSelectedTerm(list_widget))
        button_layout.addWidget(remove_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        clear_all_btn.clicked.connect(lambda: self._clearAllTerms(dialog))
        button_layout.addWidget(clear_all_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #449d44;
            }
        """)
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        dialog.exec()
    
    def _removeSelectedTerm(self, list_widget):
        """Remove selected term from blocked terms list"""
        current_item = list_widget.currentItem()
        if current_item:
            term = current_item.text()
            self.blocked_terms_manager.remove_term(term)
            list_widget.takeItem(list_widget.row(current_item))
            QMessageBox.information(self, "Term Removed", f"Removed blocked term: '{term}'")
    
    def _clearAllTerms(self, dialog):
        """Clear all blocked terms"""
        reply = QMessageBox.question(
            self,
            "Clear Blocked Terms",
            "Clear all blocked terms?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.blocked_terms_manager.clear()
            dialog.accept()
            QMessageBox.information(self, "Cleared", "All blocked terms cleared.")
