"""
Overlay Page - Configuration for OBS/Browser overlay
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QPushButton, QSpinBox, QCheckBox, QComboBox, QLineEdit,
    QSlider, QFileDialog, QFontComboBox, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QColor
from core.overlay_server import OverlayServer


class OverlayPage(QWidget):
    """Page for configuring chat overlay for OBS Studio"""
    
    def __init__(self, overlay_server, config=None, parent=None):
        super().__init__(parent)
        self.overlay_server = overlay_server
        self.config = config
        self.overlay_url = None
        
        self.initUI()
        
        # Connect to overlay server signals
        self.overlay_server.server_started.connect(self.onOverlayServerStarted)
        
        # Start overlay server
        self.overlay_server.start()
    
    def initUI(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Chat Overlay Configuration")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Configure the chat overlay for OBS Studio Browser Source or web browser. "
            "The overlay displays chat messages with transparent background, perfect for streaming."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cccccc; font-size: 13px; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # URL Display Group
        url_group = QGroupBox("Overlay URL")
        url_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        url_layout = QVBoxLayout()
        
        # URL display
        self.url_label = QLabel("Starting overlay server...")
        self.url_label.setStyleSheet("""
            QLabel {
                color: #4a90e2;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: rgba(74, 144, 226, 0.1);
                border-radius: 5px;
                border: 1px solid #4a90e2;
            }
        """)
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.url_label.setCursor(Qt.CursorShape.IBeamCursor)
        self.url_label.setWordWrap(True)
        url_layout.addWidget(self.url_label)
        
        # Copy and Open buttons
        button_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("📋 Copy URL")
        self.copy_btn.setEnabled(False)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: #ffffff;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover:enabled {
                background-color: #449d44;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #888888;
            }
        """)
        self.copy_btn.clicked.connect(self.copyUrl)
        button_layout.addWidget(self.copy_btn)
        
        self.open_btn = QPushButton("🌐 Open in Browser")
        self.open_btn.setEnabled(False)
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #0275d8;
                color: #ffffff;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover:enabled {
                background-color: #025aa5;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #888888;
            }
        """)
        self.open_btn.clicked.connect(self.openInBrowser)
        button_layout.addWidget(self.open_btn)
        
        button_layout.addStretch()
        url_layout.addLayout(button_layout)
        
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # Appearance Settings Group
        appearance_group = QGroupBox("Appearance Settings")
        appearance_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        appearance_layout = QVBoxLayout()
        
        # Message display direction
        direction_layout = QHBoxLayout()
        direction_label = QLabel("Message Direction:")
        direction_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        direction_layout.addWidget(direction_label)
        
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Bottom to Top", "Top to Bottom"])
        self.direction_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
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
        direction_layout.addWidget(self.direction_combo)
        direction_layout.addStretch()
        appearance_layout.addLayout(direction_layout)
        
        # Max messages setting
        max_msg_layout = QHBoxLayout()
        max_msg_label = QLabel("Maximum Messages:")
        max_msg_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        max_msg_layout.addWidget(max_msg_label)
        
        self.max_messages_spin = QSpinBox()
        self.max_messages_spin.setRange(10, 100)
        self.max_messages_spin.setValue(50)
        self.max_messages_spin.setSuffix(" messages")
        self.max_messages_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3d3d3d;
                border: none;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4a90e2;
            }
        """)
        max_msg_layout.addWidget(self.max_messages_spin)
        max_msg_layout.addStretch()
        appearance_layout.addLayout(max_msg_layout)
        
        # Username font settings
        username_font_label = QLabel("Username Font:")
        username_font_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; margin-top: 10px;")
        appearance_layout.addWidget(username_font_label)
        
        username_font_layout = QHBoxLayout()
        username_font_layout.addWidget(QLabel("Font:", styleSheet="color: #ffffff; font-size: 13px;"))
        
        self.username_font_combo = QFontComboBox()
        self.username_font_combo.setCurrentFont(QFont("Arial"))
        self.username_font_combo.setStyleSheet("""
            QFontComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
            }
            QFontComboBox::drop-down {
                border: none;
            }
            QFontComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QFontComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #3d3d3d;
                border: 1px solid #3d3d3d;
            }
        """)
        username_font_layout.addWidget(self.username_font_combo, 1)
        
        username_font_layout.addWidget(QLabel("Size:", styleSheet="color: #ffffff; font-size: 13px; margin-left: 10px;"))
        
        self.username_font_size_spin = QSpinBox()
        self.username_font_size_spin.setRange(10, 48)
        self.username_font_size_spin.setValue(18)
        self.username_font_size_spin.setSuffix("px")
        self.username_font_size_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3d3d3d;
                border: none;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4a90e2;
            }
        """)
        username_font_layout.addWidget(self.username_font_size_spin)
        username_font_layout.addStretch()
        appearance_layout.addLayout(username_font_layout)
        
        # Message font settings
        message_font_label = QLabel("Message Text Font:")
        message_font_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; margin-top: 10px;")
        appearance_layout.addWidget(message_font_label)
        
        message_font_layout = QHBoxLayout()
        message_font_layout.addWidget(QLabel("Font:", styleSheet="color: #ffffff; font-size: 13px;"))
        
        self.message_font_combo = QFontComboBox()
        self.message_font_combo.setCurrentFont(QFont("Arial"))
        self.message_font_combo.setStyleSheet("""
            QFontComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
            }
            QFontComboBox::drop-down {
                border: none;
            }
            QFontComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QFontComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #3d3d3d;
                border: 1px solid #3d3d3d;
            }
        """)
        message_font_layout.addWidget(self.message_font_combo, 1)
        
        message_font_layout.addWidget(QLabel("Size:", styleSheet="color: #ffffff; font-size: 13px; margin-left: 10px;"))
        
        self.message_font_size_spin = QSpinBox()
        self.message_font_size_spin.setRange(10, 48)
        self.message_font_size_spin.setValue(16)
        self.message_font_size_spin.setSuffix("px")
        self.message_font_size_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3d3d3d;
                border: none;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4a90e2;
            }
        """)
        message_font_layout.addWidget(self.message_font_size_spin)
        message_font_layout.addStretch()
        appearance_layout.addLayout(message_font_layout)
        
        # Font size setting (kept for backward compatibility, removed below)
        # (Removed - now using separate username and message font sizes above)
        
        # Animation style
        self.show_badges_check = QCheckBox("Show Platform Badges")
        self.show_badges_check.setChecked(True)
        self.show_badges_check.setStyleSheet("color: #ffffff; font-size: 13px;")
        appearance_layout.addWidget(self.show_badges_check)
        
        # Show platform icons
        self.show_platform_check = QCheckBox("Show Platform Icons")
        self.show_platform_check.setChecked(True)
        self.show_platform_check.setStyleSheet("color: #ffffff; font-size: 13px;")
        appearance_layout.addWidget(self.show_platform_check)
        
        # Animation style
        animation_layout = QHBoxLayout()
        animation_label = QLabel("Animation:")
        animation_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        animation_layout.addWidget(animation_label)
        
        self.animation_combo = QComboBox()
        self.animation_combo.addItems(["Slide In", "Fade In", "Bounce In", "Zoom In", "None"])
        self.animation_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
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
        animation_layout.addWidget(self.animation_combo)
        animation_layout.addStretch()
        appearance_layout.addLayout(animation_layout)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        # Instructions Group
        instructions_group = QGroupBox("Setup Instructions")
        instructions_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        instructions_layout = QVBoxLayout()
        
        instructions_text = QLabel(
            "<b>OBS Studio Setup:</b><br>"
            "1. In OBS Studio, add a new <b>Browser Source</b><br>"
            "2. Paste the overlay URL above into the URL field<br>"
            "3. Set Width: 600, Height: 800 (or adjust to your needs)<br>"
            "4. Check 'Shutdown source when not visible' for performance<br>"
            "5. The background is transparent - perfect for overlays!<br><br>"
            "<b>Web Browser:</b><br>"
            "Click 'Open in Browser' to test the overlay in your browser."
        )
        instructions_text.setWordWrap(True)
        instructions_text.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.5;")
        instructions_layout.addWidget(instructions_text)
        
        instructions_group.setLayout(instructions_layout)
        layout.addWidget(instructions_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    @pyqtSlot(str)
    def onOverlayServerStarted(self, url):
        """Handle overlay server startup"""
        self.overlay_url = url
        self.url_label.setText(f"<b>Overlay URL:</b><br>{url}")
        self.copy_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        print(f"[OverlayPage] Overlay server started: {url}")
    
    def copyUrl(self):
        """Copy overlay URL to clipboard"""
        if self.overlay_url:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.overlay_url)
            
            # Visual feedback
            original_text = self.copy_btn.text()
            self.copy_btn.setText("✓ Copied!")
            self.copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #449d44;
                    color: #ffffff;
                    border: none;
                    padding: 8px 20px;
                    border-radius: 4px;
                    font-size: 13px;
                }
            """)
            
            # Reset after 2 seconds
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.resetCopyButton(original_text))
    
    def resetCopyButton(self, original_text):
        """Reset copy button to original state"""
        self.copy_btn.setText(original_text)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: #ffffff;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #449d44;
            }
        """)
    
    def openInBrowser(self):
        """Open overlay in default browser"""
        if self.overlay_url:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(self.overlay_url))
