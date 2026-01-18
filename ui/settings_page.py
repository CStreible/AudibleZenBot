"""
Settings Page - Configuration and ngrok management
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QGroupBox, QScrollArea, QTextEdit, QCheckBox,
    QFrame, QMessageBox, QColorDialog, QGridLayout, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import os
import sys
from core.logger import get_logger

# Structured logger for this module
logger = get_logger('Settings')


class SettingsPage(QWidget):
    """Settings page for app configuration and ngrok management"""
    
    # Signal to notify when username colors are updated
    colors_updated = pyqtSignal(list)
    
    def __init__(self, ngrok_manager, config, log_manager=None):
        super().__init__()
        self.ngrok_manager = ngrok_manager
        self.config = config
        self.log_manager = log_manager
        self.color_buttons = []  # Store color button references
        self.initUI()
        
        # Connect signals from ngrok_manager
        if self.ngrok_manager:
            self.ngrok_manager.tunnel_started.connect(self.on_tunnel_started)
            self.ngrok_manager.tunnel_stopped.connect(self.on_tunnel_stopped)
            self.ngrok_manager.tunnel_error.connect(self.on_tunnel_error)
            self.ngrok_manager.status_changed.connect(self.on_status_changed)
    
    def initUI(self):
        """Initialize the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        main_layout.addWidget(title)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        
        # === Logging Configuration Section ===
        logging_group = self.create_logging_section()
        scroll_layout.addWidget(logging_group)
        
        # === Username Color Editor Section ===
        color_group = self.create_color_editor_section()
        scroll_layout.addWidget(color_group)
        
        # === Ngrok Configuration Section ===
        ngrok_group = self.create_ngrok_section()
        scroll_layout.addWidget(ngrok_group)
        
        # === Platform Client Credentials Section ===
        creds_group = self.create_credentials_section()
        scroll_layout.addWidget(creds_group)
        
        # === Tunnel Status Section ===
        status_group = self.create_status_section()
        scroll_layout.addWidget(status_group)
        
        # === About Section ===
        about_group = self.create_about_section()
        scroll_layout.addWidget(about_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def create_logging_section(self):
        """Create logging configuration section"""
        group = QGroupBox("📝 Debug Logging")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Description
        desc = QLabel(
            "Save all debug messages to a log file. When enabled, everything shown in the console "
            "will also be written to 'audiblezenbot.log' in your chosen folder."
        )
        desc.setStyleSheet("color: #cccccc; font-size: 12px; padding: 5px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Enable/disable logging checkbox
        self.logging_enabled_checkbox = QCheckBox("Enable debug logging to file")
        self.logging_enabled_checkbox.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        if self.log_manager:
            self.logging_enabled_checkbox.setChecked(self.log_manager.is_enabled())
        self.logging_enabled_checkbox.stateChanged.connect(self.toggle_logging)
        layout.addWidget(self.logging_enabled_checkbox)
        
        # Log folder selection
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Log Folder:")
        folder_label.setStyleSheet("color: #ffffff; min-width: 100px;")
        folder_label.setMinimumWidth(100)
        
        self.log_folder_display = QLineEdit()
        self.log_folder_display.setReadOnly(True)
        self.log_folder_display.setPlaceholderText("No folder selected...")
        self.log_folder_display.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        
        # Set current log folder
        if self.log_manager and self.log_manager.get_log_folder():
            self.log_folder_display.setText(self.log_manager.get_log_folder())
        
        self.browse_folder_btn = QPushButton("📁 Browse...")
        self.browse_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2868a8;
            }
        """)
        self.browse_folder_btn.clicked.connect(self.browse_log_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.log_folder_display)
        folder_layout.addWidget(self.browse_folder_btn)
        layout.addLayout(folder_layout)
        
        # Log file path display and open button
        info_layout = QHBoxLayout()
        
        self.log_file_info = QLabel()
        self.log_file_info.setStyleSheet("color: #888888; font-size: 11px; padding: 5px;")
        self.log_file_info.setWordWrap(True)
        self.update_log_file_info()
        
        self.open_log_btn = QPushButton("📂 Open Log File")
        self.open_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
            QPushButton:pressed {
                background-color: #3d8b3d;
            }
        """)
        self.open_log_btn.clicked.connect(self.open_log_file)
        
        info_layout.addWidget(self.log_file_info, 1)
        info_layout.addWidget(self.open_log_btn)
        layout.addLayout(info_layout)
        
        group.setLayout(layout)
        return group
    
    def create_ngrok_section(self):
        """Create ngrok configuration section"""
        group = QGroupBox("🌐 Ngrok Configuration")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Description
        desc = QLabel(
            "Ngrok is required for platforms that use webhooks (like Kick).\n"
            "Get your free auth token from: https://dashboard.ngrok.com/get-started/your-authtoken"
        )
        desc.setStyleSheet("color: #cccccc; font-size: 12px; padding: 5px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Auth token input
        token_layout = QHBoxLayout()
        token_label = QLabel("Auth Token:")
        token_label.setStyleSheet("color: #ffffff; min-width: 100px;")
        token_label.setMinimumWidth(100)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter your ngrok auth token here...")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #4a90e2;
            }
        """)
        
        # Load existing token
        if self.config:
            ngrok_config = self.config.get('ngrok', {})
            existing_token = ngrok_config.get('auth_token', '')
            if existing_token:
                self.token_input.setText(existing_token)
        
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        layout.addLayout(token_layout)
        
        # Buttons row
        button_layout = QHBoxLayout()
        
        self.save_token_btn = QPushButton("💾 Save Token")
        self.save_token_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2868a8;
            }
        """)
        self.save_token_btn.clicked.connect(self.save_token)
        
        self.test_token_btn = QPushButton("🧪 Test Connection")
        self.test_token_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
            QPushButton:pressed {
                background-color: #3d8b3d;
            }
        """)
        self.test_token_btn.clicked.connect(self.test_token)
        
        self.show_token_btn = QPushButton("👁 Show")
        self.show_token_btn.setCheckable(True)
        self.show_token_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:checked {
                background-color: #545b62;
            }
        """)
        self.show_token_btn.clicked.connect(self.toggle_token_visibility)
        
        button_layout.addWidget(self.save_token_btn)
        button_layout.addWidget(self.test_token_btn)
        button_layout.addWidget(self.show_token_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Auto-start option
        self.auto_start_checkbox = QCheckBox("Automatically start tunnels when connecting to platforms")
        self.auto_start_checkbox.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.auto_start_checkbox.setChecked(True)
        if self.config:
            ngrok_config = self.config.get('ngrok', {})
            self.auto_start_checkbox.setChecked(ngrok_config.get('auto_start', True))
        layout.addWidget(self.auto_start_checkbox)

        # Shared callback port
        port_layout = QHBoxLayout()
        port_label = QLabel("Callback Port:")
        port_label.setStyleSheet("color: #ffffff; min-width: 100px;")
        port_label.setMinimumWidth(100)

        self.callback_port_input = QLineEdit()
        self.callback_port_input.setPlaceholderText("8889")
        self.callback_port_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        # Load existing value
        try:
            if self.config:
                ngcfg = self.config.get('ngrok', {})
                port_val = str(ngcfg.get('callback_port', 8889))
                self.callback_port_input.setText(port_val)
        except Exception:
            pass

        self.save_port_btn = QPushButton("Save Port")
        self.save_port_btn.setStyleSheet("background-color: #4a90e2; color: white; padding: 8px 12px; border-radius: 5px;")
        self.save_port_btn.clicked.connect(self.save_callback_port)

        port_layout.addWidget(port_label)
        port_layout.addWidget(self.callback_port_input)
        port_layout.addWidget(self.save_port_btn)
        layout.addLayout(port_layout)
        
        group.setLayout(layout)
        return group
    
    def create_status_section(self):
        """Create tunnel status section"""
        group = QGroupBox("📊 Tunnel Status")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Status label
        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setStyleSheet("color: #ffffff; font-size: 13px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Update status
        self.update_status_display()
        
        # Tunnel info display
        self.tunnel_info = QTextEdit()
        self.tunnel_info.setReadOnly(True)
        self.tunnel_info.setMaximumHeight(150)
        self.tunnel_info.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.tunnel_info)
        
        # Update tunnel info
        self.update_tunnel_info()
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_status)
        
        self.stop_all_btn = QPushButton("🛑 Stop All Tunnels")
        self.stop_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        self.stop_all_btn.clicked.connect(self.stop_all_tunnels)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.stop_all_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group

    def create_credentials_section(self):
        """Create a small credentials editor for platform client_id/client_secret"""
        group = QGroupBox("🔐 Platform Client Credentials")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        desc = QLabel("Edit platform `client_id` and `client_secret`. These are stored in your local config file.")
        desc.setStyleSheet("color: #cccccc; font-size: 12px; padding: 5px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Platforms to expose
        platforms = ['twitch', 'trovo', 'kick', 'youtube', 'twitter']
        self.cred_rows = {}
        for p in platforms:
            row = QHBoxLayout()
            label = QLabel(p.title())
            label.setStyleSheet("color: #ffffff; min-width: 80px;")
            id_input = QLineEdit()
            id_input.setPlaceholderText("client_id")
            secret_input = QLineEdit()
            secret_input.setPlaceholderText("client_secret")
            secret_input.setEchoMode(QLineEdit.EchoMode.Password)
            save_btn = QPushButton("Save")
            save_btn.setProperty('platform', p)
            save_btn.clicked.connect(self._save_platform_credentials)

            # Populate from config
            try:
                cfg = self.config.get_platform_config(p) if self.config else {}
                id_val = cfg.get('client_id', '')
                sec_val = cfg.get('client_secret', '')
                if id_val:
                    id_input.setText(id_val)
                if sec_val:
                    secret_input.setText(sec_val)
            except Exception:
                pass

            row.addWidget(label)
            row.addWidget(id_input)
            row.addWidget(secret_input)
            row.addWidget(save_btn)
            layout.addLayout(row)
            self.cred_rows[p] = (id_input, secret_input)

        group.setLayout(layout)
        return group

    def _save_platform_credentials(self):
        sender = self.sender()
        platform = sender.property('platform')
        if not platform:
            return
        id_input, secret_input = self.cred_rows.get(platform, (None, None))
        if not id_input or not secret_input:
            return
        client_id = id_input.text().strip()
        client_secret = secret_input.text().strip()
        if not self.config:
            QMessageBox.warning(self, "Error", "Config manager not available to save credentials.")
            return
        try:
            if client_id:
                self.config.set_platform_config(platform, 'client_id', client_id)
            if client_secret:
                self.config.set_platform_config(platform, 'client_secret', client_secret)
            QMessageBox.information(self, "Saved", f"Saved credentials for {platform}.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save credentials: {e}")
    
    def create_color_editor_section(self):
        """Create username color editor section"""
        group = QGroupBox("🎨 Username Color Palette")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Description
        desc = QLabel(
            "Customize the 20 colors used for usernames when platforms don't provide colors.\n"
            "Click any color swatch to open the color picker."
        )
        desc.setStyleSheet("color: #cccccc; font-size: 12px; padding: 5px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Load current colors from config or use defaults
        from ui.chat_page import USERNAME_COLORS
        saved_colors = self.config.get('ui.username_colors', USERNAME_COLORS) if self.config else USERNAME_COLORS
        
        # Create grid of color swatches (4x5 grid)
        grid = QGridLayout()
        grid.setSpacing(10)
        self.color_buttons = []
        
        for i in range(20):
            row = i // 5
            col = i % 5
            
            # Create container for each color slot
            slot_layout = QVBoxLayout()
            slot_layout.setSpacing(5)
            
            # Color button
            color_btn = QPushButton()
            color_btn.setFixedSize(80, 40)
            color_btn.setProperty('color_index', i)
            color = saved_colors[i] if i < len(saved_colors) else '#FFFFFF'
            color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: 2px solid #555555;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            color_btn.clicked.connect(lambda checked, idx=i: self.edit_color(idx))
            self.color_buttons.append(color_btn)
            
            # Label with slot number
            label = QLabel(f"Slot {i+1}")
            label.setStyleSheet("color: #cccccc; font-size: 10px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            slot_layout.addWidget(color_btn)
            slot_layout.addWidget(label)
            
            # Create container widget
            slot_widget = QWidget()
            slot_widget.setLayout(slot_layout)
            
            grid.addWidget(slot_widget, row, col)
        
        layout.addLayout(grid)
        
        # Preset buttons
        preset_layout = QHBoxLayout()
        
        reset_btn = QPushButton("↺ Reset to Defaults")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        reset_btn.clicked.connect(self.reset_colors_to_default)
        
        preset_layout.addWidget(reset_btn)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)
        
        group.setLayout(layout)
        return group
    
    def edit_color(self, index):
        """Open color picker for a specific slot"""
        current_btn = self.color_buttons[index]
        
        # Get current color from button stylesheet
        current_color_str = self.get_button_color(current_btn)
        current_color = QColor(current_color_str)
        
        # Open color dialog
        color = QColorDialog.getColor(current_color, self, f"Choose Color for Slot {index+1}")
        
        if color.isValid():
            color_hex = color.name()
            self.set_button_color(current_btn, color_hex)
            self.save_colors()
    
    def get_button_color(self, button):
        """Extract color from button stylesheet"""
        stylesheet = button.styleSheet()
        # Extract color from "background-color: #RRGGBB;"
        import re
        match = re.search(r'background-color:\s*(#[0-9A-Fa-f]{6})', stylesheet)
        if match:
            return match.group(1)
        return '#FFFFFF'
    
    def set_button_color(self, button, color_hex):
        """Update button color"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_hex};
                border: 2px solid #555555;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #ffffff;
            }}
        """)
    
    def save_colors(self):
        """Save current colors to config and emit signal"""
        colors = [self.get_button_color(btn) for btn in self.color_buttons]
        
        if self.config:
            self.config.set('ui.username_colors', colors)
        
        # Emit signal to update chat page
        self.colors_updated.emit(colors)
        logger.info(f"Saved {len(colors)} username colors")
    
    def reset_colors_to_default(self):
        """Reset all colors to default palette"""
        from ui.chat_page import USERNAME_COLORS
        
        reply = QMessageBox.question(self, "Reset Colors", 
                                    "Reset all colors to default palette?",
                                    QMessageBox.StandardButton.Yes | 
                                    QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            for i, color in enumerate(USERNAME_COLORS):
                if i < len(self.color_buttons):
                    self.set_button_color(self.color_buttons[i], color)
            
            self.save_colors()
            QMessageBox.information(self, "Success", "Colors reset to default palette!")
    
    def create_about_section(self):
        """Create about section"""
        group = QGroupBox("ℹ️ About")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        about_text = QLabel(
            "<b>AudibleZenBot</b> - Multi-Platform Streaming Chat Bot<br>"
            "Version: 1.0.0 (Standalone Executable Edition)<br><br>"
            "This application automatically manages ngrok tunnels for platforms<br>"
            "that require webhooks (like Kick), eliminating manual setup.<br><br>"
            "For support and documentation, visit the project repository."
        )
        about_text.setStyleSheet("color: #cccccc; font-size: 12px; padding: 10px;")
        about_text.setWordWrap(True)
        layout.addWidget(about_text)
        
        group.setLayout(layout)
        return group
    
    def save_token(self):
        """Save ngrok auth token"""
        token = self.token_input.text().strip()
        
        if not token:
            QMessageBox.warning(self, "Missing Token", 
                              "Please enter your ngrok auth token.")
            return
        
        if self.ngrok_manager:
            success = self.ngrok_manager.set_auth_token(token)
            if success:
                # Save auto-start preference using the correct method
                if self.config:
                    self.config.set('ngrok.auto_start', self.auto_start_checkbox.isChecked())
                
                QMessageBox.information(self, "Success", 
                                      "Ngrok auth token saved successfully!")
                self.update_status_display()
            else:
                QMessageBox.critical(self, "Error", 
                                    "Failed to save ngrok auth token.")
        else:
            QMessageBox.warning(self, "Error", 
                              "Ngrok manager not available.")

    def save_callback_port(self):
        """Save the shared callback port to config and optionally restart tunnel"""
        port_text = self.callback_port_input.text().strip()
        if not port_text:
            QMessageBox.warning(self, "Missing Port", "Please enter a callback port.")
            return

        try:
            port = int(port_text)
            if port < 1 or port > 65535:
                raise ValueError("Port out of range")
        except Exception:
            QMessageBox.warning(self, "Invalid Port", "Please enter a valid port number (1-65535).")
            return

        if not self.config:
            QMessageBox.warning(self, "Error", "Config manager not available to save port.")
            return

        try:
            # Read previous port before changing
            try:
                prev_port = int(self.config.get('ngrok.callback_port', 8889))
            except Exception:
                prev_port = None

            # Save main callback port
            self.config.set('ngrok.callback_port', port)
            # Also update default kick tunnel mapping if present
            try:
                self.config.set('ngrok.tunnels.kick.port', port)
            except Exception:
                pass

            # If ngrok is running on the previous port, offer to restart
            if self.ngrok_manager and prev_port and self.ngrok_manager.is_tunnel_active(prev_port) and prev_port != port:
                reply = QMessageBox.question(self, "Restart Tunnel",
                                             f"A tunnel is active on port {prev_port}. Restart it on port {port}?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        self.ngrok_manager.stop_tunnel(prev_port)
                        self.ngrok_manager.start_tunnel(port, name='kick')
                    except Exception as e:
                            logger.error(f"Error restarting tunnel: {e}")

            QMessageBox.information(self, "Saved", f"Callback port saved: {port}")
            self.update_tunnel_info()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save callback port: {e}")
    
    def test_token(self):
        """Test ngrok connection"""
        if not self.ngrok_manager:
            QMessageBox.warning(self, "Error", "Ngrok manager not available.")
            return
        
        if not self.ngrok_manager.is_available():
            QMessageBox.warning(self, "Not Configured", 
                              "Please save your auth token first.")
            return
        
        # Show progress dialog
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import QTimer
        
        progress = QProgressDialog("Testing ngrok connection...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Testing Connection")
        progress.setModal(True)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        # Run test in background using QTimer to avoid blocking UI
        def run_test():
            try:
                # Try to start a test tunnel on a high port
                test_port = 9999
                url = self.ngrok_manager.start_tunnel(test_port, name="test")
                
                progress.close()
                
                if url:
                    QMessageBox.information(self, "Success", 
                                          f"Ngrok connection successful!\n\n"
                                          f"Test tunnel: {url}")
                    # Stop the test tunnel
                    QTimer.singleShot(500, lambda: self.cleanup_test_tunnel(test_port))
                else:
                    QMessageBox.critical(self, "Connection Failed", 
                                       "Failed to connect to ngrok.\n"
                                       "Please check your auth token and internet connection.")
            except Exception as e:
                progress.close()
                QMessageBox.critical(self, "Error", 
                                   f"Failed to test connection:\n{str(e)}")
        
        # Start test after a short delay to let progress dialog show
        QTimer.singleShot(100, run_test)
    
    def cleanup_test_tunnel(self, port):
        """Clean up test tunnel"""
        try:
            self.ngrok_manager.stop_tunnel(port)
            self.update_tunnel_info()
        except Exception as e:
            logger.exception(f"Error stopping test tunnel: {e}")
    
    def toggle_token_visibility(self):
        """Toggle token visibility"""
        if self.show_token_btn.isChecked():
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_btn.setText("🙈 Hide")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_btn.setText("👁 Show")
    
    def update_status_display(self):
        """Update status label"""
        if self.ngrok_manager:
            status = self.ngrok_manager.get_status_summary()
            self.status_label.setText(f"Status: {status}")
        else:
            self.status_label.setText("Status: ⚠ Ngrok manager not available")
    
    def update_tunnel_info(self):
        """Update tunnel information display"""
        if not self.ngrok_manager:
            self.tunnel_info.setText("Ngrok manager not available")
            return
        
        tunnels = self.ngrok_manager.get_all_tunnels()
        
        if not tunnels:
            self.tunnel_info.setText("No active tunnels\n\nTunnels will start automatically when connecting to platforms.")
        else:
            info_lines = ["Active Tunnels:\n"]
            for port, tunnel_data in tunnels.items():
                name = tunnel_data.get('name', f'port_{port}')
                url = tunnel_data.get('public_url', 'N/A')
                protocol = tunnel_data.get('protocol', 'http')
                info_lines.append(f"  • {name} ({protocol}):")
                info_lines.append(f"    {url} -> localhost:{port}\n")
            
            self.tunnel_info.setText('\n'.join(info_lines))
    
    def refresh_status(self):
        """Refresh status displays"""
        self.update_status_display()
        self.update_tunnel_info()
    
    def stop_all_tunnels(self):
        """Stop all active tunnels"""
        if not self.ngrok_manager:
            return
        
        tunnels = self.ngrok_manager.get_all_tunnels()
        if not tunnels:
            QMessageBox.information(self, "No Tunnels", 
                                  "No active tunnels to stop.")
            return
        
        reply = QMessageBox.question(self, "Confirm", 
                                    f"Stop all {len(tunnels)} active tunnel(s)?",
                                    QMessageBox.StandardButton.Yes | 
                                    QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.ngrok_manager.stop_all_tunnels()
            self.update_tunnel_info()
            QMessageBox.information(self, "Success", "All tunnels stopped.")
    
    # Slots for ngrok_manager signals
    @pyqtSlot(int, str)
    def on_tunnel_started(self, port, url):
        """Handle tunnel started event"""
        self.update_tunnel_info()
        self.update_status_display()
    
    @pyqtSlot(int)
    def on_tunnel_stopped(self, port):
        """Handle tunnel stopped event"""
        self.update_tunnel_info()
        self.update_status_display()
    
    @pyqtSlot(int, str)
    def on_tunnel_error(self, port, error):
        """Handle tunnel error event"""
        self.update_tunnel_info()
        self.update_status_display()
    
    @pyqtSlot(str)
    def on_status_changed(self, status):
        """Handle status change event"""
        self.update_status_display()
    
    # === Logging Methods ===
    
    def toggle_logging(self, state):
        """Toggle logging on/off"""
        if not self.log_manager:
            QMessageBox.warning(self, "Error", "Log manager not available.")
            return
        
        enabled = (state == Qt.CheckState.Checked.value)
        
        if enabled:
            # Check if folder is configured
            if not self.log_manager.get_log_folder():
                QMessageBox.warning(
                    self, 
                    "No Folder Selected", 
                    "Please select a log folder first."
                )
                self.logging_enabled_checkbox.setChecked(False)
                return
            
            # Enable logging
            result = self.log_manager.toggle_logging(True)
            if result:
                self.update_log_file_info()
                logger.info("Debug logging enabled")
            else:
                QMessageBox.warning(
                    self, 
                    "Error", 
                    "Failed to enable logging. Check console for details."
                )
                self.logging_enabled_checkbox.setChecked(False)
        else:
            # Disable logging
            self.log_manager.toggle_logging(False)
            self.update_log_file_info()
            logger.info("Debug logging disabled")
    
    def browse_log_folder(self):
        """Open folder browser to select log folder"""
        # Get current folder as starting point
        current_folder = ""
        if self.log_manager and self.log_manager.get_log_folder():
            current_folder = self.log_manager.get_log_folder()
        elif self.config:
            current_folder = self.config.get('logging.folder', '')
        
        # If no folder set, use user's home directory
        if not current_folder or not os.path.exists(current_folder):
            current_folder = os.path.expanduser('~')
        
        # Open folder dialog
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Log Folder",
            current_folder,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            # Update display
            self.log_folder_display.setText(folder)
            
            # Update log manager
            if self.log_manager:
                self.log_manager.set_log_folder(folder)
                self.update_log_file_info()
                logger.info(f"Log folder set to: {folder}")
            
            # If logging is enabled, it will automatically restart with new folder
            if self.log_manager and self.log_manager.is_enabled():
                QMessageBox.information(
                    self,
                    "Folder Updated",
                    f"Log folder updated. New logs will be written to:\n{folder}"
                )
    
    def update_log_file_info(self):
        """Update the log file info label"""
        if not self.log_manager:
            self.log_file_info.setText("Log manager not available")
            return
        
        if self.log_manager.is_enabled():
            log_path = self.log_manager.get_log_path()
            if log_path:
                self.log_file_info.setText(f"✓ Logging to: {log_path}")
                self.log_file_info.setStyleSheet("color: #5cb85c; font-size: 11px; padding: 5px;")
            else:
                self.log_file_info.setText("✗ Logging enabled but no file path")
                self.log_file_info.setStyleSheet("color: #d9534f; font-size: 11px; padding: 5px;")
        else:
            log_path = self.log_manager.get_log_path()
            if log_path:
                self.log_file_info.setText(f"Logging disabled. File: {log_path}")
            else:
                self.log_file_info.setText("Logging disabled. No folder selected.")
            self.log_file_info.setStyleSheet("color: #888888; font-size: 11px; padding: 5px;")
    
    def open_log_file(self):
        """Open the log file in default text editor"""
        if not self.log_manager:
            QMessageBox.warning(self, "Error", "Log manager not available.")
            return
        
        log_path = self.log_manager.get_log_path()
        if not log_path:
            QMessageBox.warning(
                self,
                "No Log File",
                "No log folder configured. Please select a folder first."
            )
            return
        
        if not os.path.exists(log_path):
            QMessageBox.warning(
                self,
                "File Not Found",
                f"Log file does not exist yet:\n{log_path}\n\n"
                "Enable logging to create the file."
            )
            return
        
        # Open file with default application
            try:
                if sys.platform == 'win32':
                    os.startfile(log_path)
                elif sys.platform == 'darwin':
                    os.system(f'open "{log_path}"')
                else:
                    os.system(f'xdg-open "{log_path}"')
                logger.info(f"Opened log file: {log_path}")
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to open log file:\n{e}"
                )
                logger.error(f"Error opening log file: {e}")
