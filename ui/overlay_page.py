"""
Overlay Page - Configuration for OBS/Browser overlay
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QGroupBox, 
    QPushButton, QSpinBox, QCheckBox, QComboBox, QLineEdit,
    QSlider, QFileDialog, QFontComboBox, QColorDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QColor
from core.overlay_server import OverlayServer
import cv2
from core.logger import get_logger

# Structured logger for this module
logger = get_logger('OverlayPage')


def get_windows_camera_names():
    """Get Windows camera device names using PowerShell"""
    import subprocess
    camera_names = []
    
    try:
        # Query only actual video input devices
        # Strategy: Camera/Image classes are always video, MEDIA/USB only if they have video-related names
        cmd = [
            'powershell', '-Command',
            "Get-PnpDevice -Status 'OK' | Where-Object { "
            "("
            # Camera and Image classes are almost always video devices
            "  $_.Class -in @('Camera', 'Image') -or "
            # For MEDIA/USB classes, require explicit video-related names
            "  (($_.Class -in @('MEDIA', 'USB')) -and ("
            "    $_.FriendlyName -like '*camera*' -or "
            "    $_.FriendlyName -like '*webcam*' -or "
            "    $_.FriendlyName -like '*brio*' -or "
            "    $_.FriendlyName -like '*vcam*' -or "
            "    $_.FriendlyName -like 'Live Gamer*' -or "
            "    $_.FriendlyName -like '*capture card*'"
            "  ))"
            ") -and "
            # Exclude all audio/MIDI/mixer/proxy devices
            "$_.FriendlyName -notlike '*audio*' -and "
            "$_.FriendlyName -notlike '*microphone*' -and "
            "$_.FriendlyName -notlike 'Microphone *' -and "
            "$_.FriendlyName -notlike '*midi*' -and "
            "$_.FriendlyName -notlike '*mixer*' -and "
            "$_.FriendlyName -notlike '*proxy*' -and "
            "$_.FriendlyName -notlike '*voicemod*' -and "
            "$_.FriendlyName -notlike '*streaming center*' -and "
            "$_.FriendlyName -notlike '*focusrite*' -and "
            "$_.FriendlyName -notlike '*realtek*' -and "
            "$_.Class -ne 'AudioEndpoint' "
            "} | Select-Object -ExpandProperty FriendlyName"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout:
            # Parse the output - each line is a camera name
            names = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            # Remove duplicates while preserving order
            seen = set()
            camera_names = [x for x in names if not (x in seen or seen.add(x))]
            logger.info(f"Found {len(camera_names)} camera names from Windows: {camera_names}")
        else:
            logger.debug(f"PowerShell camera query returned no results")
    except Exception as e:
        logger.error(f"Error querying Windows camera names: {e}")
    
    return camera_names


def enumerate_video_devices():
    """Enumerate available video devices using OpenCV with Windows device names"""
    devices = []
    logger.debug("Starting camera enumeration...")
    
    # First, get Windows camera names
    windows_names = get_windows_camera_names()
    
    try:
        # Try to open up to 10 camera indices
        opencv_cameras = []
        for i in range(10):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Use DirectShow on Windows
            if cap.isOpened():
                opencv_cameras.append(i)
                cap.release()
            else:
                # If we can't open this index, stop searching
                break
        
        logger.info(f"OpenCV found {len(opencv_cameras)} cameras at indices: {opencv_cameras}")
        
        # Match Windows names with OpenCV indices
        for i, opencv_idx in enumerate(opencv_cameras):
            if i < len(windows_names):
                # Use the Windows device name
                device_name = windows_names[i]
            else:
                # Fallback to generic name if we don't have a Windows name
                device_name = f"Camera {opencv_idx}"
            
            devices.append(f"{device_name}|{opencv_idx}")
            logger.info(f"Found camera: {device_name} (index {opencv_idx})")
            
    except Exception as e:
        logger.error(f"Error during camera enumeration: {e}")
    
    logger.info(f"Camera enumeration complete. Found {len(devices)} device(s)")
    return devices


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
        self.overlay_server.devices_updated.connect(self.onDevicesUpdated)
        
        # Start overlay server
        self.overlay_server.start()
    
    def initUI(self):
        """Initialize the UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #4a90e2;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        scroll_widget = QWidget()
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
        url_group = self.createGroupBox("Overlay URL")
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
        self.copy_btn.setStyleSheet(self.getButtonStyle("#5cb85c", "#449d44"))
        self.copy_btn.clicked.connect(self.copyUrl)
        button_layout.addWidget(self.copy_btn)
        
        self.open_btn = QPushButton("🌐 Open in Browser")
        self.open_btn.setEnabled(False)
        self.open_btn.setStyleSheet(self.getButtonStyle("#0275d8", "#025aa5"))
        self.open_btn.clicked.connect(self.openInBrowser)
        button_layout.addWidget(self.open_btn)
        
        button_layout.addStretch()
        url_layout.addLayout(button_layout)
        
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # Appearance Settings Group
        appearance_group = self.createGroupBox("Appearance Settings")
        appearance_layout = QVBoxLayout()
        
        # Create a horizontal layout for compact vertical columns
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        
        # Column 1: Username Font with Size and Display checkboxes
        col1_layout = QVBoxLayout()
        col1_layout.setSpacing(3)
        
        # Username Font dropdown
        col1_layout.addWidget(self.createLabel("Username Font:", bold=True))
        self.username_font_combo = self.createFontComboBox()
        self.username_font_combo.currentFontChanged.connect(self.onSettingsChanged)
        self.username_font_combo.setFixedWidth(200)
        col1_layout.addWidget(self.username_font_combo)
        
        # Size label and spinbox in horizontal layout
        size_layout_1 = QHBoxLayout()
        size_layout_1.setSpacing(5)
        size_layout_1.addWidget(self.createLabel("Size:"))
        self.username_font_size_spin = self.createSpinBox(10, 48, 18, "px")
        self.username_font_size_spin.valueChanged.connect(self.onSettingsChanged)
        self.username_font_size_spin.setFixedWidth(80)
        size_layout_1.addWidget(self.username_font_size_spin)
        size_layout_1.addStretch()
        col1_layout.addLayout(size_layout_1)
        
        # Display checkboxes (no heading)
        col1_layout.addSpacing(5)
        self.show_badges_check = QCheckBox("Show Badges")
        self.show_badges_check.setChecked(True)
        self.show_badges_check.setStyleSheet("color: #ffffff; font-size: 13px;")
        self.show_badges_check.stateChanged.connect(self.onSettingsChanged)
        col1_layout.addWidget(self.show_badges_check)
        
        self.show_platform_check = QCheckBox("Show Icons")
        self.show_platform_check.setChecked(True)
        self.show_platform_check.setStyleSheet("color: #ffffff; font-size: 13px;")
        self.show_platform_check.stateChanged.connect(self.onSettingsChanged)
        col1_layout.addWidget(self.show_platform_check)
        
        col1_layout.addStretch()
        columns_layout.addLayout(col1_layout)
        
        # Column 2: Message Font with Size
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(3)
        
        # Message Font dropdown
        col2_layout.addWidget(self.createLabel("Message Font:", bold=True))
        self.message_font_combo = self.createFontComboBox()
        self.message_font_combo.currentFontChanged.connect(self.onSettingsChanged)
        self.message_font_combo.setFixedWidth(200)
        col2_layout.addWidget(self.message_font_combo)
        
        # Size label and spinbox in horizontal layout
        size_layout_2 = QHBoxLayout()
        size_layout_2.setSpacing(5)
        size_layout_2.addWidget(self.createLabel("Size:"))
        self.message_font_size_spin = self.createSpinBox(10, 48, 16, "px")
        self.message_font_size_spin.valueChanged.connect(self.onSettingsChanged)
        self.message_font_size_spin.setFixedWidth(80)
        size_layout_2.addWidget(self.message_font_size_spin)
        size_layout_2.addStretch()
        col2_layout.addLayout(size_layout_2)
        
        col2_layout.addStretch()
        columns_layout.addLayout(col2_layout)
        
        # Column 3: Direction, Duration, Entry, Exit
        col3_layout = QVBoxLayout()
        col3_layout.setSpacing(3)
        
        # Direction
        direction_layout = QHBoxLayout()
        direction_layout.setSpacing(5)
        direction_layout.addWidget(self.createLabel("Direction:", bold=True))
        self.direction_combo = self.createComboBox(["Bottom to Top", "Top to Bottom"])
        self.direction_combo.currentTextChanged.connect(self.onSettingsChanged)
        self.direction_combo.setFixedWidth(140)
        direction_layout.addWidget(self.direction_combo)
        direction_layout.addStretch()
        col3_layout.addLayout(direction_layout)
        
        # Duration
        col3_layout.addSpacing(5)
        duration_layout = QHBoxLayout()
        duration_layout.setSpacing(5)
        duration_layout.addWidget(self.createLabel("Duration:", bold=True))
        self.duration_spin = self.createSpinBox(0, 60, 0, "s")
        self.duration_spin.valueChanged.connect(self.onSettingsChanged)
        self.duration_spin.setFixedWidth(80)
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()
        col3_layout.addLayout(duration_layout)
        
        # Entry Animation
        col3_layout.addSpacing(5)
        entry_layout = QHBoxLayout()
        entry_layout.setSpacing(5)
        entry_layout.addWidget(self.createLabel("Entry:", bold=True))
        self.entry_combo = self.createComboBox(["Slide In", "Fade In", "Bounce In", "Zoom In", "None"])
        self.entry_combo.currentTextChanged.connect(self.onSettingsChanged)
        self.entry_combo.setFixedWidth(120)
        entry_layout.addWidget(self.entry_combo)
        entry_layout.addStretch()
        col3_layout.addLayout(entry_layout)
        
        # Exit Animation
        col3_layout.addSpacing(5)
        exit_layout = QHBoxLayout()
        exit_layout.setSpacing(5)
        exit_layout.addWidget(self.createLabel("Exit:", bold=True))
        self.exit_combo = self.createComboBox(["Slide Out", "Fade Out", "Zoom Out", "None"])
        self.exit_combo.currentTextChanged.connect(self.onSettingsChanged)
        self.exit_combo.setFixedWidth(120)
        exit_layout.addWidget(self.exit_combo)
        exit_layout.addStretch()
        col3_layout.addLayout(exit_layout)
        
        col3_layout.addStretch()
        columns_layout.addLayout(col3_layout)
        
        # Column 4: Max Messages, Msg BG Color, Opacity, Blur
        col4_layout = QVBoxLayout()
        col4_layout.setSpacing(3)
        
        # Max Messages
        max_messages_layout = QHBoxLayout()
        max_messages_layout.setSpacing(5)
        max_messages_layout.addWidget(self.createLabel("Max Messages:", bold=True))
        self.max_messages_spin = self.createSpinBox(10, 100, 50, "")
        self.max_messages_spin.valueChanged.connect(self.onSettingsChanged)
        self.max_messages_spin.setFixedWidth(80)
        max_messages_layout.addWidget(self.max_messages_spin)
        max_messages_layout.addStretch()
        col4_layout.addLayout(max_messages_layout)
        
        # Msg BG Color
        col4_layout.addSpacing(5)
        color_layout = QHBoxLayout()
        color_layout.setSpacing(5)
        color_layout.addWidget(self.createLabel("Msg BG Color:", bold=True))
        self.msg_bg_color_btn = QPushButton("Choose")
        self.msg_bg_color_btn.setStyleSheet(self.getColorButtonStyle("#000000"))
        self.msg_bg_color_btn.setFixedWidth(100)
        self.msg_bg_color = QColor(0, 0, 0)
        self.msg_bg_color_btn.clicked.connect(self.chooseMsgBgColor)
        color_layout.addWidget(self.msg_bg_color_btn)
        color_layout.addStretch()
        col4_layout.addLayout(color_layout)
        
        # Opacity
        col4_layout.addSpacing(5)
        opacity_layout = QHBoxLayout()
        opacity_layout.setSpacing(5)
        opacity_layout.addWidget(self.createLabel("Opacity:", bold=True))
        self.msg_opacity_slider = self.createSlider(0, 100, 70)
        self.msg_opacity_slider.valueChanged.connect(self.onSettingsChanged)
        self.msg_opacity_slider.setFixedWidth(100)
        opacity_layout.addWidget(self.msg_opacity_slider)
        self.msg_opacity_value = QLabel("70%")
        self.msg_opacity_value.setStyleSheet("color: #ffffff; font-size: 13px; min-width: 35px;")
        self.msg_opacity_slider.valueChanged.connect(lambda v: self.msg_opacity_value.setText(f"{v}%"))
        opacity_layout.addWidget(self.msg_opacity_value)
        opacity_layout.addStretch()
        col4_layout.addLayout(opacity_layout)
        
        # Blur
        col4_layout.addSpacing(5)
        blur_layout = QHBoxLayout()
        blur_layout.setSpacing(5)
        blur_layout.addWidget(self.createLabel("Blur:", bold=True))
        self.msg_blur_spin = self.createSpinBox(0, 20, 10, "px")
        self.msg_blur_spin.valueChanged.connect(self.onSettingsChanged)
        self.msg_blur_spin.setFixedWidth(80)
        blur_layout.addWidget(self.msg_blur_spin)
        blur_layout.addStretch()
        col4_layout.addLayout(blur_layout)
        
        col4_layout.addStretch()
        columns_layout.addLayout(col4_layout)
        
        columns_layout.addStretch()
        appearance_layout.addLayout(columns_layout)
        
        # Overlay background settings - all on one line with dynamic controls
        appearance_layout.addWidget(self.createLabel("Overlay Background:", bold=True, margin_top=True))
        
        overlay_bg_layout = QHBoxLayout()
        overlay_bg_layout.setSpacing(10)
        
        # Type selector (always visible)
        overlay_bg_layout.addWidget(self.createLabel("Type:"))
        # NOTE: "Video Device" option removed - it interferes with Snap Cam and other virtual camera device settings
        self.overlay_bg_combo = self.createComboBox(["Transparent", "Solid Color", "Image", "Video"])
        self.overlay_bg_combo.setFixedWidth(130)
        self.overlay_bg_combo.currentTextChanged.connect(self.onOverlayBgTypeChanged)
        overlay_bg_layout.addWidget(self.overlay_bg_combo)
        
        # Solid Color picker (hidden by default)
        self.overlay_bg_color_btn = QPushButton("Choose Color")
        self.overlay_bg_color_btn.setStyleSheet(self.getColorButtonStyle("#1a1a1a"))
        self.overlay_bg_color = QColor(26, 26, 26)
        self.overlay_bg_color_btn.clicked.connect(self.chooseOverlayBgColor)
        self.overlay_bg_color_btn.setVisible(False)
        overlay_bg_layout.addWidget(self.overlay_bg_color_btn)
        
        # Image/Video browse button and path (hidden by default)
        self.overlay_media_browse_btn = QPushButton("Browse...")
        self.overlay_media_browse_btn.setStyleSheet(self.getButtonStyle("#0275d8", "#025aa5"))
        self.overlay_media_browse_btn.clicked.connect(self.browseOverlayMedia)
        self.overlay_media_browse_btn.setVisible(False)
        overlay_bg_layout.addWidget(self.overlay_media_browse_btn)
        
        # Clickable path label (styled as link)
        self.overlay_media_path = QPushButton("No file specified")
        self.overlay_media_path.setFlat(True)
        self.overlay_media_path.setCursor(Qt.CursorShape.PointingHandCursor)
        self.overlay_media_path.setStyleSheet("""
            QPushButton {
                color: #4a90e2;
                font-size: 13px;
                font-style: italic;
                text-align: left;
                padding: 0;
                border: none;
            }
            QPushButton:hover:enabled {
                color: #6ab0ff;
                text-decoration: underline;
            }
            QPushButton:disabled {
                color: #808080;
                font-style: italic;
            }
        """)
        self.overlay_media_path.clicked.connect(self.browseOverlayMedia)
        self.overlay_media_path.setEnabled(False)  # Start disabled
        self.overlay_media_path.setVisible(False)
        overlay_bg_layout.addWidget(self.overlay_media_path, 1)
        
        # Store separate paths for image and video
        self.overlay_image_path = ""
        self.overlay_video_path = ""
        
        # NOTE: Video Device feature disabled - it interferes with Snap Cam and other virtual camera device settings
        # The device enumeration was causing conflicts with applications using virtual cameras
        # Keeping the combo/button objects to avoid breaking existing code, but not enumerating devices
        
        # # Video Device selector (hidden by default)
        # # Enumerate video devices using OpenCV
        # print("[OverlayPage] About to enumerate video devices during initialization...")
        # initial_devices = enumerate_video_devices()
        # print(f"[OverlayPage] Enumeration returned: {initial_devices}")
        # 
        # if not initial_devices:
        #     initial_devices = ["No cameras detected"]
        #     print("[OverlayPage] No cameras detected during initialization")
        # else:
        #     print(f"[OverlayPage] Populating device combo with: {initial_devices}")
        
        initial_devices = ["Feature Disabled"]
        self.overlay_device_combo = self.createComboBox(initial_devices)
        self.overlay_device_combo.currentTextChanged.connect(self.onSettingsChanged)
        self.overlay_device_combo.setVisible(False)
        overlay_bg_layout.addWidget(self.overlay_device_combo)
        
        # Add refresh button for camera devices (disabled)
        self.refresh_devices_btn = QPushButton("🔄")
        self.refresh_devices_btn.setFixedWidth(40)
        self.refresh_devices_btn.setToolTip("Feature disabled - interferes with Snap Cam")
        self.refresh_devices_btn.clicked.connect(self.onRefreshDevices)
        self.refresh_devices_btn.setVisible(False)
        self.refresh_devices_btn.setEnabled(False)
        overlay_bg_layout.addWidget(self.refresh_devices_btn)
        
        overlay_bg_layout.addStretch()
        appearance_layout.addLayout(overlay_bg_layout)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        # Instructions Group
        instructions_group = self.createGroupBox("Setup Instructions")
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
        scroll_widget.setLayout(layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        
        # Load saved settings after UI is initialized
        self.loadSettings()
    
    def createGroupBox(self, title):
        """Create a styled group box"""
        group = QGroupBox(title)
        group.setStyleSheet("""
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
        return group
    
    def createLabel(self, text, bold=False, margin_top=False, margin_left=False):
        """Create a styled label"""
        label = QLabel(text)
        style = "color: #ffffff; font-size: 13px;"
        if bold:
            style += " font-weight: bold;"
        if margin_top:
            style += " margin-top: 10px;"
        if margin_left:
            style += " margin-left: 10px;"
        label.setStyleSheet(style)
        return label
    
    def createComboBox(self, items):
        """Create a styled combo box"""
        combo = QComboBox()
        combo.addItems(items)
        combo.setMaxVisibleItems(20)  # Show up to 20 items in dropdown
        combo.setStyleSheet("""
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
        return combo
    
    def createSpinBox(self, min_val, max_val, default_val, suffix=""):
        """Create a styled spin box with visible arrows"""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default_val)
        if suffix:
            spin.setSuffix(suffix)
        # Use NoButtons and add text to show it's adjustable
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        spin.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
            }
        """)
        # Make it clear the value is editable by allowing direct typing and mouse wheel
        spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        return spin
    
    def createFontComboBox(self):
        """Create a styled font combo box"""
        combo = QFontComboBox()
        combo.setCurrentFont(QFont("Arial"))
        combo.setStyleSheet("""
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
        return combo
    
    def createSlider(self, min_val, max_val, default_val):
        """Create a styled slider"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3d3d3d;
                height: 8px;
                background: #2d2d2d;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4a90e2;
                border: 1px solid #3d3d3d;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #357abd;
            }
        """)
        return slider
    
    def getButtonStyle(self, bg_color, hover_color):
        """Get button style with colors"""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: #ffffff;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
            }}
            QPushButton:hover:enabled {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #3d3d3d;
                color: #888888;
            }}
        """
    
    def getColorButtonStyle(self, bg_color):
        """Get color button style"""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                border-color: #4a90e2;
            }}
        """
    
    @pyqtSlot(str)
    def onOverlayServerStarted(self, url):
        """Handle overlay server startup"""
        self.overlay_url = url
        self.url_label.setText(f"<b>Overlay URL:</b><br>{url}")
        self.copy_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        logger.info(f"Overlay server started: {url}")
    
    def onRefreshDevices(self):
        """Refresh the list of video devices"""
        # NOTE: Video device feature disabled - interferes with Snap Cam and other virtual camera device settings
        logger.debug("Video device refresh disabled - feature interferes with Snap Cam")
        return
        
        # # Save current selection
        # current_selection = self.overlay_device_combo.currentText()
        # 
        # # Enumerate devices
        # devices = enumerate_video_devices()
        # 
        # # Clear and update combo box
        # self.overlay_device_combo.clear()
        # 
        # if devices:
        #     self.overlay_device_combo.addItems(devices)
        #     print(f"[OverlayPage] Found {len(devices)} video devices")
        #     
        #     # Try to restore previous selection if still available
        #     index = self.overlay_device_combo.findText(current_selection)
        #     if index >= 0:
        #         self.overlay_device_combo.setCurrentIndex(index)
        # else:
        #     self.overlay_device_combo.addItem("No cameras detected")
        #     print("[OverlayPage] No video devices found")
    
    def onDevicesUpdated(self, devices):
        """Handle updated list of video devices from browser"""
        logger.info(f"Received {len(devices)} video devices from browser")
        
        # Save current selection
        current_selection = self.overlay_device_combo.currentText()
        
        # Clear and update combo box
        self.overlay_device_combo.clear()
        
        if devices:
            self.overlay_device_combo.addItems(devices)
            
            # Try to restore previous selection if still available
            index = self.overlay_device_combo.findText(current_selection)
            if index >= 0:
                self.overlay_device_combo.setCurrentIndex(index)
        else:
            # No devices found, show placeholder
            self.overlay_device_combo.addItem("No cameras detected")
    
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
        self.copy_btn.setStyleSheet(self.getButtonStyle("#5cb85c", "#449d44"))
    
    def openInBrowser(self):
        """Open overlay in default browser"""
        if self.overlay_url:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(self.overlay_url))
    
    def chooseMsgBgColor(self):
        """Choose message background color"""
        color = QColorDialog.getColor(self.msg_bg_color, self, "Choose Message Background Color")
        if color.isValid():
            self.msg_bg_color = color
            self.msg_bg_color_btn.setStyleSheet(self.getColorButtonStyle(color.name()))
            if color.lightness() < 128:
                self.msg_bg_color_btn.setStyleSheet(self.msg_bg_color_btn.styleSheet().replace("color: #ffffff;", "color: #ffffff;"))
            else:
                self.msg_bg_color_btn.setStyleSheet(self.msg_bg_color_btn.styleSheet().replace("color: #ffffff;", "color: #000000;"))
            self.onSettingsChanged()
    
    def chooseOverlayBgColor(self):
        """Choose overlay background color"""
        color = QColorDialog.getColor(self.overlay_bg_color, self, "Choose Overlay Background Color")
        if color.isValid():
            self.overlay_bg_color = color
            self.overlay_bg_color_btn.setStyleSheet(self.getColorButtonStyle(color.name()))
            if color.lightness() < 128:
                self.overlay_bg_color_btn.setStyleSheet(self.overlay_bg_color_btn.styleSheet().replace("color: #ffffff;", "color: #ffffff;"))
            else:
                self.overlay_bg_color_btn.setStyleSheet(self.overlay_bg_color_btn.styleSheet().replace("color: #ffffff;", "color: #000000;"))
            self.onSettingsChanged()
    
    def onOverlayBgTypeChanged(self, bg_type):
        """Handle overlay background type change"""
        # Hide all controls first
        self.overlay_bg_color_btn.setVisible(False)
        self.overlay_media_browse_btn.setVisible(False)
        self.overlay_media_path.setVisible(False)
        self.overlay_device_combo.setVisible(False)
        self.refresh_devices_btn.setVisible(False)
        
        # Show appropriate controls based on type
        if bg_type == "Solid Color":
            self.overlay_bg_color_btn.setVisible(True)
        elif bg_type == "Image":
            self.overlay_media_browse_btn.setVisible(True)
            self.overlay_media_path.setVisible(True)
            # Update path display for image
            if self.overlay_image_path:
                import os
                self.overlay_media_path.setText(os.path.basename(self.overlay_image_path))
                self.overlay_media_path.setToolTip(self.overlay_image_path)
                self.overlay_media_path.setEnabled(True)
            else:
                self.overlay_media_path.setText("No file specified")
                self.overlay_media_path.setToolTip("")
                self.overlay_media_path.setEnabled(False)
        elif bg_type == "Video":
            self.overlay_media_browse_btn.setVisible(True)
            self.overlay_media_path.setVisible(True)
            # Update path display for video
            if self.overlay_video_path:
                import os
                self.overlay_media_path.setText(os.path.basename(self.overlay_video_path))
                self.overlay_media_path.setToolTip(self.overlay_video_path)
                self.overlay_media_path.setEnabled(True)
            else:
                self.overlay_media_path.setText("No file specified")
                self.overlay_media_path.setToolTip("")
                self.overlay_media_path.setEnabled(False)
        # NOTE: Video Device option removed - interferes with Snap Cam
        # elif bg_type == "Video Device":
        #     self.overlay_device_combo.setVisible(True)
        #     self.refresh_devices_btn.setVisible(True)
        # Transparent shows nothing extra
        
        self.onSettingsChanged()
    
    def browseOverlayMedia(self):
        """Browse for overlay background media file"""
        bg_type = self.overlay_bg_combo.currentText()
        if bg_type == "Image":
            file_filter = "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;All Files (*.*)"
            title = "Select Background Image"
        else:  # Video
            file_filter = "Video Files (*.mp4 *.webm *.ogg *.mov *.avi);;All Files (*.*)"
            title = "Select Background Video"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, "", file_filter
        )
        if file_path:
            import os
            # Store in appropriate variable based on type
            if bg_type == "Image":
                self.overlay_image_path = file_path
            else:  # Video
                self.overlay_video_path = file_path
            
            # Update display and enable button
            self.overlay_media_path.setText(os.path.basename(file_path))
            self.overlay_media_path.setToolTip(file_path)
            self.overlay_media_path.setEnabled(True)
            self.onSettingsChanged()
    
    def getSettings(self):
        """Get current overlay settings as a dictionary"""
        return {
            'direction': self.direction_combo.currentText(),
            'max_messages': self.max_messages_spin.value(),
            'username_font': self.username_font_combo.currentFont().family(),
            'username_font_size': self.username_font_size_spin.value(),
            'message_font': self.message_font_combo.currentFont().family(),
            'message_font_size': self.message_font_size_spin.value(),
            'show_badges': self.show_badges_check.isChecked(),
            'show_platform': self.show_platform_check.isChecked(),
            'entry_animation': self.entry_combo.currentText(),
            'exit_animation': self.exit_combo.currentText(),
            'duration': self.duration_spin.value(),
            'msg_opacity': self.msg_opacity_slider.value(),
            'msg_bg_color': self.msg_bg_color.name(),
            'msg_blur': self.msg_blur_spin.value(),
            'overlay_bg_type': self.overlay_bg_combo.currentText(),
            'overlay_bg_color': self.overlay_bg_color.name(),
            'overlay_media': self.overlay_image_path if self.overlay_bg_combo.currentText() == 'Image' else self.overlay_video_path,
            'overlay_device': self.overlay_device_combo.currentText()
        }
    
    def loadSettings(self):
        """Load overlay settings from config"""
        if not self.config:
            return
        
        overlay_config = self.config.get('overlay', {})
        
        # Direction
        direction = overlay_config.get('direction', 'Bottom to Top')
        index = self.direction_combo.findText(direction)
        if index >= 0:
            self.direction_combo.setCurrentIndex(index)
        
        # Duration
        self.duration_spin.setValue(overlay_config.get('duration', 0))
        
        # Entry animation
        entry = overlay_config.get('entry_animation', 'Slide In')
        index = self.entry_combo.findText(entry)
        if index >= 0:
            self.entry_combo.setCurrentIndex(index)
        
        # Exit animation
        exit_anim = overlay_config.get('exit_animation', 'Fade Out')
        index = self.exit_combo.findText(exit_anim)
        if index >= 0:
            self.exit_combo.setCurrentIndex(index)
        
        # Max messages
        self.max_messages_spin.setValue(overlay_config.get('max_messages', 50))
        
        # Username font
        username_font = overlay_config.get('username_font', 'Arial')
        self.username_font_combo.setCurrentFont(QFont(username_font))
        self.username_font_size_spin.setValue(overlay_config.get('username_font_size', 18))
        
        # Message font
        message_font = overlay_config.get('message_font', 'Arial')
        self.message_font_combo.setCurrentFont(QFont(message_font))
        self.message_font_size_spin.setValue(overlay_config.get('message_font_size', 16))
        
        # Display checkboxes
        self.show_badges_check.setChecked(overlay_config.get('show_badges', True))
        self.show_platform_check.setChecked(overlay_config.get('show_platform', True))
        
        # Msg BG Color
        msg_bg_color = overlay_config.get('msg_bg_color', '#000000')
        self.msg_bg_color = QColor(msg_bg_color)
        self.msg_bg_color_btn.setStyleSheet(self.getColorButtonStyle(msg_bg_color))
        
        # Opacity
        opacity = overlay_config.get('msg_opacity', 70)
        self.msg_opacity_slider.setValue(opacity)
        
        # Blur
        self.msg_blur_spin.setValue(overlay_config.get('msg_blur', 10))
        
        # Overlay background type
        bg_type = overlay_config.get('overlay_bg_type', 'Transparent')
        index = self.overlay_bg_combo.findText(bg_type)
        if index >= 0:
            self.overlay_bg_combo.setCurrentIndex(index)
        
        # Overlay background color
        overlay_bg_color = overlay_config.get('overlay_bg_color', '#1a1a1a')
        self.overlay_bg_color = QColor(overlay_bg_color)
        self.overlay_bg_color_btn.setStyleSheet(self.getColorButtonStyle(overlay_bg_color))
        
        # Overlay media paths
        self.overlay_image_path = overlay_config.get('overlay_image_path', '')
        self.overlay_video_path = overlay_config.get('overlay_video_path', '')
        
        # Overlay device
        device = overlay_config.get('overlay_device', 'Default Camera')
        index = self.overlay_device_combo.findText(device)
        if index >= 0:
            self.overlay_device_combo.setCurrentIndex(index)
        
        logger.debug("Settings loaded from config")
    
    def saveSettings(self):
        """Save overlay settings to config"""
        if not self.config:
            return
        
        settings = self.getSettings()
        # Add the file paths which aren't in getSettings
        settings['overlay_image_path'] = self.overlay_image_path
        settings['overlay_video_path'] = self.overlay_video_path
        
        # Use ConfigManager.set which reloads and saves atomically
        self.config.set('overlay', settings)
        logger.debug("Settings saved to config")
    
    def onSettingsChanged(self):
        """Handle settings change - update overlay server and save to config"""
        settings = self.getSettings()
        self.overlay_server.update_settings(settings)
        self.saveSettings()
        logger.info(f"Settings changed: {settings}")
