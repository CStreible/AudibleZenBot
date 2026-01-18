from ui.ui_elements import ToggleSwitch
"""
Automation Page - Chat Commands, Events, Timers, and Stream Info
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QScrollArea, QFrame, QLineEdit, QTextEdit,
    QGroupBox, QGridLayout, QComboBox, QCompleter, QCheckBox,
    QSpinBox, QListWidget, QListWidgetItem, QMessageBox, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QByteArray, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from ui.platform_icons import get_platform_icon_html
import os
import sys
import json
import random
import base64
from core.logger import get_logger

logger = get_logger(__name__)




class AutomationPage(QWidget):
    """Automation page for managing chat commands, events, timers, and variables"""

    def create_functions_tab(self):
        from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel, QTextEdit
        tab = QWidget()
        layout = QVBoxLayout(tab)
        label = QLabel("Write and manage interpreted code routines here. These can be triggered from various sources within the bot.")
        label.setStyleSheet("color: #cccccc; font-size: 12px; padding: 10px;")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.functions_editor = QTextEdit()
        self.functions_editor.setPlaceholderText("Write your function code here...")
        self.functions_editor.setStyleSheet("background: #232323; color: #fff; font-family: Consolas, monospace; font-size: 13px;")
        layout.addWidget(self.functions_editor, 1)
        return tab

    def save_variables_to_config(self):
        """Save all variable rows to config under 'automation.variables'"""
        variables = {}
        for i in range(self.variables_rows_container.count()):
            group_box = self.variables_rows_container.itemAt(i).widget()
            if group_box is not None:
                row_widgets = group_box.findChildren(QWidget)
                for w in row_widgets:
                    if hasattr(w, 'get_data'):
                        data = w.get_data()
                        name = data.get('name', '').strip()
                        if name:
                            variables[name] = {
                                'value': data.get('value', ''),
                                'default': data.get('default', ''),
                                'type': data.get('type', 'string'),
                                'initialize': data.get('initialize', False)
                            }
        self.config.set('automation.variables', variables)

    def load_variables_from_config(self):
        self.variables = self.config.get('automation.variables', {}) or {}
        # Remove all current variable rows
        while self.variables_rows_container.count():
            item = self.variables_rows_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for var_name, var_data in self.variables.items():
            self.add_variable_row(
                var_name,
                var_data.get('value', ''),
                var_data.get('default', ''),
                var_data.get('initialize', False),
                var_data.get('type', 'string')
            )
    def detect_type(self, value):
        # Simple type detection: int, float, bool, else string
        if isinstance(value, bool):
            return 'bool'
        if isinstance(value, int):
            return 'int'
        if isinstance(value, float):
            return 'float'
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ('true', 'false'):
                return 'bool'
            try:
                int(value)
                return 'int'
            except Exception:
                pass
            try:
                float(value)
                return 'float'
            except Exception:
                pass
        return 'string'

    def print_variables_tab_diagnostics(self):
        logger.debug("\n[DIAGNOSTICS] Variables Tab Layout:")
        logger.debug(f"  TabWidget geometry: {self.tab_widget.geometry()}")
        logger.debug(f"  Variables tab QWidget geometry: {self.variables_tab.geometry()}")
        logger.debug(f"  Variables tab QWidget size: {self.variables_tab.size()}")
        logger.debug(f"  Variables tab QWidget minimumSize: {self.variables_tab.minimumSize()}")
        logger.debug(f"  Variables tab QWidget maximumSize: {self.variables_tab.maximumSize()}")
        margins = self.variables_tab.contentsMargins()
        logger.debug(f"  Variables tab QWidget contentsMargins: left={margins.left()}, top={margins.top()}, right={margins.right()}, bottom={margins.bottom()}")
        logger.debug(f"  Variables rows container count: {self.variables_rows_container.count()}")
        for i in range(self.variables_rows_container.count()):
            row_widget = self.variables_rows_container.itemAt(i).widget()
            if row_widget:
                logger.debug(f"    Row {i}: {row_widget.geometry()} size={row_widget.size()} min={row_widget.minimumSize()} max={row_widget.maximumSize()} policy={row_widget.sizePolicy()}")
                for child in row_widget.findChildren(QWidget):
                    logger.debug(f"      Child: {type(child).__name__} geometry={child.geometry()} size={child.size()} min={child.minimumSize()} max={child.maximumSize()} policy={child.sizePolicy()}")

    def create_variables_tab(self):
        """Create the Variables tab with a styled box like timer groups"""
        from ui.variable_row_widget import VariableRowWidget
        outer_widget = QWidget()
        outer_layout = QVBoxLayout(outer_widget)
        outer_layout.setContentsMargins(20, 20, 20, 20)
        outer_layout.setSpacing(15)

        # Group box styled like timer groups
        group_box = QGroupBox()
        group_box.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        group_layout = QVBoxLayout(group_box)
        group_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        label = QLabel("🔣 Variables")
        label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        label.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(label)
        header_layout.addStretch()

        # Add/Remove/Diagnostics buttons
        add_btn = QPushButton("Add Variable")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        add_btn.clicked.connect(self._on_add_variable_clicked_with_log)
        header_layout.addWidget(add_btn)

        remove_btn = QPushButton("Delete Selected")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94e77;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0395b;
            }
        """)
        remove_btn.clicked.connect(self.remove_selected_variables)
        header_layout.addWidget(remove_btn)


        group_layout.addLayout(header_layout)

        description = QLabel("Create and manage global variables for use in automations and commands. Variables can be initialized to a default value on startup if desired.")
        description.setStyleSheet("color: #cccccc; margin-bottom: 15px;")
        description.setWordWrap(True)
        group_layout.addWidget(description)

        # Scroll area for variable rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        self.variables_rows_container = QVBoxLayout(scroll_content)
        self.variables_rows_container.setSpacing(15)
        self.variables_rows_container.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(scroll_content)
        group_layout.addWidget(scroll, 1)

        self.load_variables_from_config()
        outer_layout.addWidget(group_box)
        return outer_widget

    def add_variable_row(self, name='', value='', default='', initialize=False, var_type='string'):
        logger.debug(f"[VariablesTab] DEBUG: add_variable_row called with name='{name}', value='{value}', default='{default}', initialize={initialize}")
        from ui.variable_row_widget import VariableRowWidget
        # Always set value to default if Initialize? is selected
        if initialize:
            value = default
        # Wrap each variable row in a QGroupBox styled like timer groups
        group_box = QGroupBox()
        group_box.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        vbox = QVBoxLayout(group_box)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(0)
        row_widget = VariableRowWidget(name, value, default, var_type, initialize)
        vbox.addWidget(row_widget)
        self.variables_rows_container.addWidget(group_box)
        # Save when 'Initialize?' toggled
        row_widget.init_radio.toggled.connect(self.save_variables_to_config)
        # Save when Value or Default field loses focus (handled by this page)
        row_widget.value_edit.installEventFilter(self)
        row_widget.default_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        # Save variables when Value or Default field loses focus
        if event.type() == QEvent.Type.FocusOut:
            # Check if obj is a value_edit or default_edit of any VariableRowWidget
            for i in range(self.variables_rows_container.count()):
                group_box = self.variables_rows_container.itemAt(i).widget()
                if group_box is not None:
                    row_widgets = group_box.findChildren(QWidget)
                    for w in row_widgets:
                        if hasattr(w, 'value_edit') and obj is w.value_edit:
                            self.save_variables_to_config()
                            break
                        if hasattr(w, 'default_edit') and obj is w.default_edit:
                            self.save_variables_to_config()
                            break
        return super().eventFilter(obj, event)

    def remove_selected_variables(self):
        # Remove all variable rows whose checkbox is checked
        to_remove = []
        for i in range(self.variables_rows_container.count()):
            group_box = self.variables_rows_container.itemAt(i).widget()
            if group_box is not None:
                # VariableRowWidget is inside the group box
                row_widgets = group_box.findChildren(QWidget)
                for w in row_widgets:
                    # Look for VariableRowWidget with select_checkbox
                    if hasattr(w, 'select_checkbox') and w.select_checkbox.isChecked():
                        to_remove.append(group_box)
        # Remove selected group boxes
        for group_box in to_remove:
            self.variables_rows_container.removeWidget(group_box)
            group_box.setParent(None)
            group_box.deleteLater()
        self.save_variables_to_config()

    def _on_add_variable_clicked_with_log(self):
        logger.debug("[VariablesTab] DEBUG: Add Variable button clicked")
        self.add_variable_row()
        logger.debug("[VariablesTab] DEBUG: add_variable_row() called")
        # Do NOT call save_variables_to_config() here; only save on cell edit or checkbox toggle

    def __init__(self, chat_manager, config):
        super().__init__()
        self.chat_manager = chat_manager
        self.config = config
        # Store platform widgets for easy access
        self.platform_widgets = {}
        
        # Timer message groups and state
        self.timer_groups = {}  # {group_name: {display_name: str, interval: int, messages: [], platforms: {}, active: bool, send_as_streamer: bool}}
        self.timer_state = {}  # {group_name: {remaining_messages: [], timer: QTimer}}
        self.any_stream_live = False  # Track if any platform is streaming
        
        self.initUI()
        # Initialize variables if needed before anything else
        self.initialize_variables_on_start()
        # Load stream info on startup with a slight delay to ensure UI is fully initialized
        QTimer.singleShot(100, self.load_timer_config)
        # Connect to stream status changes
        if self.chat_manager:
            self.setup_stream_listeners()

    def initialize_variables_on_start(self):
        """Set variable value to default if 'Initialize' is enabled, before routines run"""
        variables = self.config.get('automation.variables', {}) or {}
        changed = False
        for name, data in variables.items():
            if data.get('initialize', False):
                if data.get('value', None) != data.get('default', None):
                    variables[name]['value'] = data.get('default', '')
                    changed = True
        if changed:
            self.config.set('automation.variables', variables)
    
    def initUI(self):
        """Initialize the user interface to match ConnectionsPage tab style"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("Automation")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff; padding: 10px;")
        layout.addWidget(title)

        # Description
        desc = QLabel("Automate chat commands, events, timers, and manage global variables.")
        desc.setStyleSheet("color: #cccccc; font-size: 12px; padding: 0 10px 10px 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)


        # Tabbed widget for automation features
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
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

        # Create tabs
        self.variables_tab = self.create_variables_tab()
        self.functions_tab = self.create_functions_tab()
        self.commands_tab = self.create_commands_tab()
        self.timers_tab = self.create_timers_tab()
        self.events_tab = self.create_events_tab()

        self.tab_widget.addTab(self.variables_tab, "🔣 Variables")
        self.tab_widget.addTab(self.functions_tab, "🧩 Functions")
        self.tab_widget.addTab(self.commands_tab, "🎯 Triggers")
        self.tab_widget.addTab(self.timers_tab, "⏰ Timers")
        self.tab_widget.addTab(self.events_tab, "⚡ Events")

        layout.addWidget(self.tab_widget)

    # ...existing code...

    # ...existing code...

    def infer_type(self, value):
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ['1', 'true']:
                return 'bool'
            if v in ['0', 'false']:
                return 'bool'
            try:
                int(value)
                return 'int'
            except Exception:
                return 'string'
        elif isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        return 'string'
    
    def create_commands_tab(self):
        """Create the Chat Commands tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Placeholder content
        label = QLabel("Chat Commands")
        label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        label.setStyleSheet("color: #ffffff;")
        layout.addWidget(label)
        
        description = QLabel("Configure custom chat commands that users can trigger.")
        description.setStyleSheet("color: #cccccc; margin-bottom: 15px;")
        layout.addWidget(description)
        
        # Placeholder for future content
        placeholder = QLabel("Content will be added here...")
        placeholder.setStyleSheet("color: #888888; font-style: italic;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder, 1)
        
        return widget
    
    def create_events_tab(self):
        """Create the Events tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Placeholder content
        label = QLabel("Events")
        label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        label.setStyleSheet("color: #ffffff;")
        layout.addWidget(label)
        
        description = QLabel("Trigger actions based on stream events (follows, subs, donations, etc.).")
        description.setStyleSheet("color: #cccccc; margin-bottom: 15px;")
        layout.addWidget(description)
        
        # Placeholder for future content
        placeholder = QLabel("Content will be added here...")
        placeholder.setStyleSheet("color: #888888; font-style: italic;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder, 1)
        
        return widget
    
    def create_timers_tab(self):
        """Create the Timers tab for automated recurring messages"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        label = QLabel("⏰ Timer Messages")
        label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        label.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(label)
        
        header_layout.addStretch()
        
        # Add Group button
        add_group_btn = QPushButton("➕ Add Group")
        add_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        add_group_btn.clicked.connect(lambda: self.add_timer_group())
        header_layout.addWidget(add_group_btn)
        
        layout.addLayout(header_layout)
        
        description = QLabel("Create message groups that send recurring messages at set intervals. Messages are sent in random order without repeats until all have been sent.")
        description.setStyleSheet("color: #cccccc; margin-bottom: 15px;")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Scroll area for groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        scroll_content = QWidget()
        self.timers_layout = QVBoxLayout(scroll_content)
        self.timers_layout.setSpacing(15)
        self.timers_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        return widget
    
    def add_timer_group(self, group_name=None, display_name=None, interval=300, messages=None, platforms=None, send_as_streamer=False, allow_offline=False):
        """Add a new timer message group"""
        # Validate group_name if provided
        if group_name is not None and not isinstance(group_name, str):
            logger.warning(f"[TimerMessages] Invalid group_name type: {type(group_name)}, value: {group_name}")
            return
        
        if group_name is None:
            group_name, ok = QInputDialog.getText(
                self,
                "New Timer Group",
                "Enter group ID (internal identifier):"
            )
            if not ok or not group_name or not group_name.strip():
                return
            group_name = group_name.strip()
        
        # Ensure group_name is a string
        group_name = str(group_name)
        
        if group_name in self.timer_groups:
            QMessageBox.warning(self, "Duplicate Group", f"Group '{group_name}' already exists.")
            return
        
        # Get display name if not provided
        if display_name is None:
            display_name, ok = QInputDialog.getText(
                self,
                "Timer Group Display Name",
                "Enter display name:",
                QLineEdit.EchoMode.Normal,
                str(group_name)  # Ensure it's a string
            )
            if not ok:
                display_name = group_name
            elif display_name.strip():
                display_name = display_name.strip()
            else:
                display_name = group_name
        
        # Initialize group data
        self.timer_groups[group_name] = {
            'display_name': display_name,
            'interval': interval if interval else 300,
            'messages': messages if messages else [],
            'platforms': platforms if platforms else {
                'twitch': True,
                'trovo': True,
                'kick': True,
                'dlive': True,
                'youtube': True,
                'twitter': False
            },
            'active': False,
            'allow_offline': allow_offline,
            'send_as_streamer': send_as_streamer
        }
        
        # Create group widget
        group_widget = self.create_timer_group_widget(str(group_name))
        
        # Insert before the stretch
        self.timers_layout.insertWidget(self.timers_layout.count() - 1, group_widget)
        
        self.save_timer_config()
    
    def create_timer_group_widget(self, group_name):
        """Create a widget for a timer group"""
        # Ensure group_name is a string
        group_name = str(group_name)
        
        display_name = self.timer_groups[group_name].get('display_name', group_name)
        group_box = QGroupBox()
        group_box.setObjectName(group_name)  # Store internal name
        group_box.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout(group_box)
        layout.setSpacing(10)
        

        # --- NEW LAYOUT ---
        main_hbox = QHBoxLayout()
        left_vbox = QVBoxLayout()
        right_vbox = QVBoxLayout()
        right_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Active toggle (custom animated switch)
        active_toggle = ToggleSwitch()
        active_toggle.setChecked(self.timer_groups[group_name].get('active', False))
        active_toggle.setToolTip("Enable or disable this timer group")
        active_toggle.stateChanged.connect(lambda state: self.toggle_group_active(group_name, state == Qt.CheckState.Checked.value))
        # Add label next to toggle
        active_toggle_row = QHBoxLayout()
        active_toggle_row.setSpacing(8)
        active_toggle_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        active_toggle_row.addWidget(active_toggle)
        active_label = QLabel("Active")
        active_label.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 13px;")
        active_toggle_row.addWidget(active_label)
        left_vbox.addLayout(active_toggle_row)

        # Header row (name + delete)
        header_layout = QHBoxLayout()
        name_label = QLabel("📋")
        name_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        header_layout.addWidget(name_label)
        name_edit = QLineEdit(display_name)
        name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: bold;
                min-width: 200px;
            }
            QLineEdit:focus {
                border: 1px solid #4a90e2;
            }
        """)
        name_edit.textChanged.connect(lambda text: self.update_group_display_name(group_name, text, group_box))
        header_layout.addWidget(name_edit)
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_timer_group(group_name, group_box))
        header_layout.addWidget(delete_btn)
        header_layout.addStretch()
        left_vbox.addLayout(header_layout)

        # Send as streamer and Allow offline (column, between name and interval)
        send_allow_vbox = QVBoxLayout()
        send_allow_vbox.setSpacing(2)

        # Send as Streamer: use ToggleSwitch with matching size to variables tab
        send_row = QWidget()
        send_row_layout = QHBoxLayout(send_row)
        send_row_layout.setContentsMargins(0, 0, 0, 0)
        send_row_layout.setSpacing(8)
        send_as_streamer_toggle = ToggleSwitch(width=30, height=15)
        send_as_streamer_toggle.setChecked(self.timer_groups[group_name].get('send_as_streamer', False))
        send_as_streamer_toggle.stateChanged.connect(lambda state: self.update_send_as_streamer(group_name, state == Qt.CheckState.Checked.value))
        send_as_streamer_toggle.setToolTip("Send messages using streamer account instead of bot account")
        send_row_layout.addWidget(send_as_streamer_toggle)
        send_as_label = QLabel("Send as Streamer")
        send_as_label.setStyleSheet('color: #cccccc; font-weight: bold;')
        send_row_layout.addWidget(send_as_label)
        send_row_layout.addStretch()
        send_allow_vbox.addWidget(send_row)

        # Allow Offline: ToggleSwitch
        offline_row = QWidget()
        offline_row_layout = QHBoxLayout(offline_row)
        offline_row_layout.setContentsMargins(0, 0, 0, 0)
        offline_row_layout.setSpacing(8)
        allow_offline_toggle = ToggleSwitch(width=30, height=15)
        allow_offline_toggle.setChecked(self.timer_groups[group_name].get('allow_offline', False))
        allow_offline_toggle.stateChanged.connect(lambda state: self.update_allow_offline(group_name, state == Qt.CheckState.Checked.value))
        allow_offline_toggle.setToolTip("Allow this group to send messages even when no streams are active")
        offline_row_layout.addWidget(allow_offline_toggle)
        allow_label = QLabel("Allow Offline")
        allow_label.setStyleSheet('color: #cccccc; font-weight: bold;')
        offline_row_layout.addWidget(allow_label)
        offline_row_layout.addStretch()
        send_allow_vbox.addWidget(offline_row)
        left_vbox.addLayout(send_allow_vbox)

        # Controls row (interval, test send)
        controls_layout = QHBoxLayout()
        interval_label = QLabel("Interval (seconds):")
        interval_label.setStyleSheet("color: #cccccc; font-weight: normal;")
        controls_layout.addWidget(interval_label)
        interval_spin = QSpinBox()
        interval_spin.setRange(1, 86400)  # 1 second to 24 hours
        interval_spin.setValue(self.timer_groups[group_name]['interval'])
        interval_spin.setKeyboardTracking(True)
        interval_spin.setStyleSheet("""
            QSpinBox {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
            }
        """)
        interval_spin.valueChanged.connect(lambda v: self.update_group_interval(group_name, v))
        controls_layout.addWidget(interval_spin)
        test_send_icon = QPushButton("▶")
        test_send_icon.setFixedSize(32, 32)
        test_send_icon.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 2px solid #4a90e2;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #4a90e2;
                color: white;
            }
        """)
        test_send_icon.clicked.connect(lambda: self.test_send_timer_message(group_name))
        test_send_icon.setToolTip("Send a random message from this group immediately")
        controls_layout.addWidget(test_send_icon)
        test_send_label = QLabel("Test Send")
        test_send_label.setStyleSheet("color: #cccccc; font-weight: normal; margin-left: 5px;")
        controls_layout.addWidget(test_send_label)
        controls_layout.addStretch()
        left_vbox.addLayout(controls_layout)

        main_hbox.addLayout(left_vbox, 3)

        # Platform toggles (right, column)
        platform_vbox = QVBoxLayout()
        platform_label = QLabel("Platforms:")
        platform_label.setStyleSheet("color: #cccccc; font-weight: normal;")
        platform_vbox.addWidget(platform_label)
        platforms = ['twitch', 'trovo', 'kick', 'dlive', 'youtube', 'twitter']
        for platform in platforms:
            checkbox = self.create_platform_checkbox(platform, group_name)
            platform_vbox.addWidget(checkbox)
        platform_vbox.addStretch()
        right_vbox.addLayout(platform_vbox)
        main_hbox.addLayout(right_vbox, 1)
        layout.addLayout(main_hbox)
        
        # Messages section
        messages_label = QLabel("Messages:")
        messages_label.setStyleSheet("color: #ffffff; font-weight: bold; margin-top: 10px;")
        layout.addWidget(messages_label)
        
        # Message list container
        message_list_container = QWidget()
        message_list_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)
        message_list_layout = QVBoxLayout(message_list_container)
        message_list_layout.setContentsMargins(5, 5, 5, 5)
        message_list_layout.setSpacing(2)
        
        # Create scroll area for messages
        message_scroll = QScrollArea()
        message_scroll.setWidget(message_list_container)
        message_scroll.setWidgetResizable(True)
        message_scroll.setMaximumHeight(150)
        message_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
        """)
        
        # Store reference to list for add/remove operations
        message_list_container.message_items = []
        
        # Add messages with send buttons
        for msg in self.timer_groups[group_name]['messages']:
            self.add_message_item_widget(group_name, msg, message_list_layout)
        
        message_list_container.message_layout = message_list_layout
        layout.addWidget(message_scroll)
        
        # Store references for later use
        group_box.message_list_container = message_list_container
        group_box.message_scroll = message_scroll
        
        # Message controls
        msg_controls = QHBoxLayout()
        
        add_msg_btn = QPushButton("➕ Add Message")
        add_msg_btn.setStyleSheet("""
            QPushButton {
                background-color: #388e3c;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #2e7d32;
            }
        """)
        add_msg_btn.clicked.connect(lambda: self.add_message_to_group(group_name, message_list_container))
        msg_controls.addWidget(add_msg_btn)
        
        remove_msg_btn = QPushButton("➖ Remove Message")
        remove_msg_btn.setStyleSheet("""
            QPushButton {
                background-color: #f57c00;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #e65100;
            }
        """)
        remove_msg_btn.clicked.connect(lambda: self.remove_message_from_group(group_name, message_list_container))
        msg_controls.addWidget(remove_msg_btn)
        
        msg_controls.addStretch()
        layout.addLayout(msg_controls)
        
        return group_box
    
    def create_platform_checkbox(self, platform, group_name):
        """Create a checkbox with platform icon"""
        from PyQt6.QtCore import QSize
        # Build a small row with ToggleSwitch and label/icon so the ToggleSwitch
        # size matches other toggles used in the UI (30x15).
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        toggle = ToggleSwitch(width=30, height=15)
        toggle.setChecked(self.timer_groups[group_name]['platforms'].get(platform, False))
        toggle.stateChanged.connect(lambda state, p=platform, g=group_name: self.update_platform_toggle(g, p, state == Qt.CheckState.Checked.value))
        row_layout.addWidget(toggle)

        # Icon/label
        label = QLabel(f"  {platform.title()}")
        label.setStyleSheet('color: #cccccc; font-weight: normal;')
        # Try to load platform icon and prepend to label via pixmap label
        icon_path = self.get_platform_icon_path(platform)
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_label = QLabel()
                icon_label.setPixmap(scaled_pixmap)
                row_layout.addWidget(icon_label)

        row_layout.addWidget(label)
        row_layout.addStretch()

        # Expose the toggle on the returned widget for any callers that expect
        # a direct widget reference to the control (e.g., for introspection).
        row._toggle = toggle
        return row
    
    def get_platform_icon_path(self, platform):
        """Get the file path for platform icon"""
        # Get base directory
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Map platforms to icon files
        icon_map = {
            'kick': os.path.join(base_dir, 'resources', 'badges', 'kick', 'kick_logo.jpg'),
            'youtube': os.path.join(base_dir, 'resources', 'badges', 'youtube', 'youtube_logo.svg'),
            'dlive': os.path.join(base_dir, 'resources', 'badges', 'dlive', 'dlive_logo.png'),
            'twitch': os.path.join(base_dir, 'resources', 'icons', 'twitch.png'),
            # Prefer the official Trovo logo SVG from badges (higher-fidelity)
            'trovo': os.path.join(base_dir, 'resources', 'icons', 'trovo.ico'),
            # Use the Twitter/X icon from resources/icons
            'twitter': os.path.join(base_dir, 'resources', 'icons', 'twitter.ico'),
        }
        
        return icon_map.get(platform)
    
    def add_message_item_widget(self, group_name, message, message_layout):
        """Add a message item widget with a send button"""
        message_widget = QWidget()
        message_widget.message_text = message
        message_widget.isSelected = False
        message_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-radius: 4px;
                padding: 2px;
            }
            QWidget:hover {
                background-color: #2b2b2b;
            }
        """)
        
        message_row = QHBoxLayout(message_widget)
        message_row.setContentsMargins(5, 5, 5, 5)
        message_row.setSpacing(8)
        
        # Send button (white triangle)
        send_btn = QPushButton("▶")
        send_btn.setFixedSize(24, 24)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #4a90e2;
                background-color: #2b2b2b;
                border-radius: 4px;
            }
        """)
        send_btn.clicked.connect(lambda: self.send_specific_message(group_name, message))
        send_btn.setToolTip("Send this message immediately")
        message_row.addWidget(send_btn)
        
        # Message text label
        message_label = QLabel(message)
        message_label.setStyleSheet("color: #ffffff; padding: 4px;")
        message_label.setWordWrap(True)
        message_row.addWidget(message_label, 1)
        
        # Make widget clickable for selection
        def mousePressEvent(event):
            # Toggle selection
            message_widget.isSelected = not message_widget.isSelected
            if message_widget.isSelected:
                message_widget.setStyleSheet("""
                    QWidget {
                        background-color: #4a90e2;
                        border-radius: 4px;
                        padding: 2px;
                    }
                """)
            else:
                message_widget.setStyleSheet("""
                    QWidget {
                        background-color: #1e1e1e;
                        border-radius: 4px;
                        padding: 2px;
                    }
                    QWidget:hover {
                        background-color: #2b2b2b;
                    }
                """)
        
        message_widget.mousePressEvent = mousePressEvent
        message_layout.addWidget(message_widget)
    
    def send_specific_message(self, group_name, message):
        """Send a specific message from a timer group immediately"""
        if group_name not in self.timer_groups:
            return
        
        group = self.timer_groups[group_name]
        
        # Check if allow_offline is False and no streams are live
        allow_offline = group.get('allow_offline', False)
        if not allow_offline and not self.any_stream_live:
            QMessageBox.warning(
                self, 
                "Stream Offline", 
                f"Cannot send message: No streams are currently live.\n\n"
                f"Enable 'Allow Offline' for this group to send messages when offline."
            )
            return
        
        # Determine whether to use streamer or bot account
        send_as_streamer = group.get('send_as_streamer', False)
        
        # Send to enabled platforms
        platforms_sent = []
        for platform, enabled in group['platforms'].items():
            if enabled and self.chat_manager:
                try:
                    # Reload config to get fresh bot credentials
                    from core.config import ConfigManager
                    fresh_config = ConfigManager()
                    platform_config = fresh_config.get_platform_config(platform)
                    
                    # Determine which account to use: prefer an active bot connector,
                    # otherwise fall back to configured bot creds, then streamer.
                    if send_as_streamer:
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        account_type = 'streamer'
                    else:
                        account_type = 'streamer'
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        # Prefer live bot connector if available
                        try:
                            if self.chat_manager:
                                bot_conns = getattr(self.chat_manager, 'bot_connectors', {}) or {}
                                bot_conn = bot_conns.get(platform)
                                if bot_conn and getattr(bot_conn, 'connected', False):
                                    pc = fresh_config.get_platform_config(platform)
                                    username = pc.get('bot_username') or pc.get('username')
                                    token = pc.get('bot_token')
                                    account_type = 'bot'
                                    logger.info(f"[TimerMessages] Using live bot connector for {platform}: {username}")
                        except Exception:
                            pass

                        # If no live bot, try configured bot creds
                        if account_type != 'bot':
                            bot_username = platform_config.get('bot_username')
                            bot_token = platform_config.get('bot_token')
                            if bot_username and bot_token:
                                username = bot_username
                                token = bot_token
                                account_type = 'bot'
                    
                    if not username or not token:
                        continue
                    
                    # Send message via direct API call
                    success = self.send_message_as_account(platform, message, username, token, account_type)
                    if success:
                        platforms_sent.append(f"{platform}({account_type})")
                        
                except Exception as e:
                    logger.exception(f"[TimerMessages] Error sending specific message to {platform}: {e}")
        
        if platforms_sent:
            logger.info(f"[TimerMessages] SPECIFIC SEND from '{group_name}' to {platforms_sent}: {message}")
        else:
            QMessageBox.warning(
                self,
                "Send Failed",
                f"Could not send message to any platform.\n\n"
                f"Make sure platforms are enabled and credentials are configured."
            )
        
        # (duplicate loop removed)
    
    def update_send_as_streamer(self, group_name, enabled):
        """Update send_as_streamer setting for a timer group"""
        if group_name in self.timer_groups:
            self.timer_groups[group_name]['send_as_streamer'] = enabled
            self.save_timer_config()
            logger.debug(f"[TimerMessages] Group '{group_name}' send_as_streamer: {enabled}")
    
    def test_send_timer_message(self, group_name):
        """Manually send a random message from the timer group immediately"""
        if group_name not in self.timer_groups:
            return
        
        group = self.timer_groups[group_name]
        messages = group.get('messages', [])
        
        if not messages:
            QMessageBox.warning(self, "No Messages", "This timer group has no messages to send.")
            return
        
        # Pick a random message
        message = random.choice(messages)
        
        # Determine whether to use streamer or bot account
        send_as_streamer = group.get('send_as_streamer', False)
        
        # Send to enabled platforms (prefer live bot connector, then config bot creds, then streamer)
        platforms_sent = []
        for platform, enabled in group['platforms'].items():
            if enabled and self.chat_manager:
                try:
                    from core.config import ConfigManager
                    fresh_config = ConfigManager()
                    platform_config = fresh_config.get_platform_config(platform)

                    if send_as_streamer:
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        account_type = 'streamer'
                    else:
                        account_type = 'streamer'
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        # Prefer live bot connector
                        try:
                            bot_conns = getattr(self.chat_manager, 'bot_connectors', {}) or {}
                            bot_conn = bot_conns.get(platform)
                            if bot_conn and getattr(bot_conn, 'connected', False):
                                pc = fresh_config.get_platform_config(platform)
                                username = pc.get('bot_username') or pc.get('username')
                                token = pc.get('bot_token')
                                account_type = 'bot'
                                logger.debug(f"[TimerMessages] Test: {platform} - Using live BOT connector: {username}")
                        except Exception:
                            pass

                        if account_type != 'bot':
                            bot_username = platform_config.get('bot_username')
                            bot_token = platform_config.get('bot_token')
                            logger.debug(f"[TimerMessages] Test: {platform} - Checking bot credentials: username='{bot_username}', has_token={bool(bot_token)}")
                            if bot_username and bot_token:
                                username = bot_username
                                token = bot_token
                                account_type = 'bot'
                                logger.debug(f"[TimerMessages] Test: {platform} - Using BOT account: {bot_username}")
                            else:
                                logger.debug(f"[TimerMessages] Test: {platform} - Bot not available, falling back to STREAMER account")

                    if not username or not token:
                        logger.debug(f"[TimerMessages] Test: No credentials for {platform} ({account_type} account)")
                        continue

                    success = self.send_message_as_account(platform, message, username, token, account_type)
                    if success:
                        platforms_sent.append(f"{platform}({account_type})")
                except Exception as e:
                    logger.exception(f"[TimerMessages] Test: Error sending to {platform}: {e}")
                    import traceback
                    traceback.print_exc()

        logger.info(f"[TimerMessages] TEST SEND from '{group_name}' to {platforms_sent}: {message}")
        QMessageBox.information(self, "Test Message Sent", 
                               f"Message sent to: {', '.join(platforms_sent)}\n\nMessage: {message}")
    
    def add_message_to_group(self, group_name, message_list_container):
        """Add a new message to a timer group"""
        # Create a custom dialog with larger text input
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Add Message")
        dialog.setLabelText("Enter message text:")
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setOption(QInputDialog.InputDialogOption.UsePlainTextEditForTextInput, True)
        dialog.resize(500, 300)
        
        if dialog.exec() == QInputDialog.DialogCode.Accepted:
            message = dialog.textValue()
            if message and message.strip():
                message = message.strip()
                self.timer_groups[group_name]['messages'].append(message)
                # Add widget for the new message
                message_layout = message_list_container.message_layout
                self.add_message_item_widget(group_name, message, message_layout)
                self.save_timer_config()
    
    def remove_message_from_group(self, group_name, message_list_container):
        """Remove selected message from a timer group"""
        # Find selected message widget
        message_layout = message_list_container.message_layout
        selected_widget = None
        selected_message = None
        
        for i in range(message_layout.count()):
            item = message_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'isSelected') and widget.isSelected:
                    selected_widget = widget
                    selected_message = widget.message_text
                    break
        
        if selected_widget and selected_message:
            # Remove from layout and data
            message_layout.removeWidget(selected_widget)
            selected_widget.deleteLater()
            self.timer_groups[group_name]['messages'].remove(selected_message)
            self.save_timer_config()
        else:
            QMessageBox.information(self, "No Selection", "Please select a message to remove by clicking on it.")
    
    def update_group_interval(self, group_name, interval):
        """Update the interval for a timer group"""
        self.timer_groups[group_name]['interval'] = interval
        self.save_timer_config()
        
        # Restart timer if active
        if self.timer_groups[group_name].get('active', False) and group_name in self.timer_state:
            timer = self.timer_state[group_name].get('timer')
            if timer:
                timer.setInterval(interval * 1000)
    
    def update_platform_toggle(self, group_name, platform, enabled):
        """Update platform toggle for a timer group"""
        self.timer_groups[group_name]['platforms'][platform] = enabled
        self.save_timer_config()
    
    def update_allow_offline(self, group_name, enabled):
        """Update allow offline setting for a timer group"""
        self.timer_groups[group_name]['allow_offline'] = enabled
        self.save_timer_config()
        
        # If enabling offline mode and group is active but not started, start it now
        if enabled and self.timer_groups[group_name].get('active', False) and group_name not in self.timer_state:
            self.start_timer_group(group_name)
    
    def toggle_group_active(self, group_name, active):
        """Toggle a timer group active/inactive and ensure toggle reflects actual state"""
        self.timer_groups[group_name]['active'] = active
        self.save_timer_config()

        # Find the toggle widget for this group
        group_box = None
        for i in range(self.timers_layout.count()):
            item = self.timers_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QGroupBox):
                if item.widget().objectName() == group_name:
                    group_box = item.widget()
                    break

        toggle_widget = None
        if group_box:
            # Find ToggleSwitch in group_box
            for child in group_box.findChildren(QWidget):
                if isinstance(child, ToggleSwitch):
                    toggle_widget = child
                    break

        if active:
            # Try to start the timer group
            started = self.start_timer_group_with_result(group_name)
            if not started:
                # If failed, set toggle back to unchecked and show warning
                self.timer_groups[group_name]['active'] = False
                self.save_timer_config()
                if toggle_widget:
                    toggle_widget.blockSignals(True)
                    toggle_widget.setChecked(False)
                    toggle_widget.blockSignals(False)
        else:
            self.stop_timer_group(group_name)
            if toggle_widget:
                toggle_widget.blockSignals(True)
                toggle_widget.setChecked(False)
                toggle_widget.blockSignals(False)

    def start_timer_group_with_result(self, group_name):
        """Start timer group, return True if started, False if not (with feedback)"""
        if group_name not in self.timer_groups:
            return False
        group = self.timer_groups[group_name]
        if not group['messages']:
            QMessageBox.warning(self, "No Messages", "This timer group has no messages to send.")
            return False
        if not group.get('allow_offline', False) and not self.any_stream_live:
            QMessageBox.warning(self, "Stream Offline", "Cannot start timer group: No streams are currently live.\n\nEnable 'Allow Offline' for this group to send messages when offline.")
            return False
        # If all checks pass, start as normal
        self.start_timer_group(group_name)
        return True
    
    def start_timer_group(self, group_name):
        """Start sending messages for a timer group (waits for first interval)"""
        if group_name not in self.timer_groups:
            return
        
        group = self.timer_groups[group_name]
        if not group['messages']:
            logger.info(f"[TimerMessages] Group '{group_name}' has no messages, skipping")
            return
        
        # Check if any stream is live (unless allow_offline is enabled)
        if not group.get('allow_offline', False) and not self.any_stream_live:
            logger.info(f"[TimerMessages] Group '{group_name}' waiting for stream to start (allow_offline=False)")
            return
        
        # Initialize state
        if group_name not in self.timer_state:
            self.timer_state[group_name] = {
                'remaining_messages': [],
                'timer': None
            }
        
        # Shuffle and prepare messages
        self.timer_state[group_name]['remaining_messages'] = group['messages'].copy()
        random.shuffle(self.timer_state[group_name]['remaining_messages'])
        
        # Create and start timer (first message sends after interval expires)
        timer = QTimer()
        timer.timeout.connect(lambda: self.send_next_timer_message(group_name))
        timer.start(group['interval'] * 1000)
        self.timer_state[group_name]['timer'] = timer
        
        display_name = group.get('display_name', group_name)
        offline_status = " (offline mode)" if group.get('allow_offline', False) and not self.any_stream_live else ""
        logger.info(f"[TimerMessages] Started group '{display_name}' with {len(group['messages'])} messages, interval: {group['interval']}s (first message in {group['interval']}s){offline_status}")
    
    def stop_timer_group(self, group_name):
        """Stop sending messages for a timer group"""
        if group_name in self.timer_state:
            timer = self.timer_state[group_name].get('timer')
            if timer:
                timer.stop()
                timer.deleteLater()
            del self.timer_state[group_name]
            logger.info(f"[TimerMessages] Stopped group '{group_name}'")
    
    def send_next_timer_message(self, group_name):
        """Send the next message from a timer group"""
        if group_name not in self.timer_groups or group_name not in self.timer_state:
            return
        
        group = self.timer_groups[group_name]
        state = self.timer_state[group_name]
        
        # If no remaining messages, reshuffle
        if not state['remaining_messages']:
            state['remaining_messages'] = group['messages'].copy()
            random.shuffle(state['remaining_messages'])
            logger.info(f"[TimerMessages] Group '{group_name}' reshuffled messages")
        
        # Get next message
        message = state['remaining_messages'].pop(0)
        
        # Determine whether to use streamer or bot account
        send_as_streamer = group.get('send_as_streamer', False)
        
        # Send to enabled platforms
        platforms_sent = []
        for platform, enabled in group['platforms'].items():
            if enabled and self.chat_manager:
                try:
                    from core.config import ConfigManager
                    fresh_config = ConfigManager()
                    platform_config = fresh_config.get_platform_config(platform)

                    if send_as_streamer:
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        account_type = 'streamer'
                    else:
                        account_type = 'streamer'
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        # Prefer a live bot connector
                        try:
                            bot_conns = getattr(self.chat_manager, 'bot_connectors', {}) or {}
                            bot_conn = bot_conns.get(platform)
                            if bot_conn and getattr(bot_conn, 'connected', False):
                                pc = fresh_config.get_platform_config(platform)
                                username = pc.get('bot_username') or pc.get('username')
                                token = pc.get('bot_token')
                                account_type = 'bot'
                                logger.info(f"[TimerMessages] Using live bot connector for {platform}: {username}")
                        except Exception:
                            pass

                        if account_type != 'bot':
                            bot_username = platform_config.get('bot_username')
                            bot_token = platform_config.get('bot_token')
                            if bot_username and bot_token:
                                username = bot_username
                                token = bot_token
                                account_type = 'bot'

                    if not username or not token:
                        logger.debug(f"[TimerMessages] No credentials for {platform} ({account_type} account)")
                        continue

                    success = self.send_message_as_account(platform, message, username, token, account_type)
                    if success:
                        platforms_sent.append(f"{platform}({account_type})")
                except Exception as e:
                    logger.exception(f"[TimerMessages] Error sending to {platform}: {e}")
                    import traceback
                    traceback.print_exc()
        
        logger.info(f"[TimerMessages] Sent message from '{group_name}' to {platforms_sent}: {message[:50]}...")
    
    def send_message_as_account(self, platform, message, username, token, account_type):
        """Send a message to a platform using specific account credentials"""
        import requests
        import time
        # Persistent log of attempted send from UI layer to aid debugging (pre-attempt)
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                sf.write(f"{time.time():.3f} platform={platform} attempted={account_type} username={username} preview={repr(message)[:200]}\n")
        except Exception:
            pass

        try:
            # For Twitch, use the appropriate persistent connection
            if platform == 'twitch':
                logger.debug(f"[TimerMessages] Twitch send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Use persistent bot connector from chat_manager
                    logger.debug(f"[TimerMessages] Calling sendMessageAsBot for Twitch...")
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('twitch', message, allow_fallback=False)
                    if success:
                        logger.info(f"[TimerMessages] ✓ Twitch: Sent via persistent bot connection ({username})")
                        # Don't echo - bot connector will read its own message back from IRC
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ⚠ Twitch: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    # Use streamer connector directly
                    connector = self.chat_manager.connectors.get('twitch')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        logger.debug(f"[TimerMessages][TRACE] Twitch streamer send: connector_connected={getattr(connector, 'connected', False)} username={username}")
                        result = connector.send_message(message)
                        logger.debug(f"[TimerMessages][TRACE] Twitch streamer send result: {result}")
                        if result:
                            logger.info(f"[TimerMessages] ✓ Twitch: Sent via persistent streamer connection ({username})")
                            # Don't echo - Twitch IRC echoes back our own messages
                            return True
                        else:
                            logger.warning(f"[TimerMessages] ✗ Twitch: send_message returned False for streamer ({username})")
                            return False
                    else:
                        logger.warning(f"[TimerMessages] ✗ Twitch: Streamer connector not available")
                        return False
            
            elif platform == 'kick':
                # Use Kick persistent connection
                logger.debug(f"[TimerMessages] Kick send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Use persistent bot connector from chat_manager
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('kick', message, allow_fallback=False)
                    if success:
                        logger.info(f"[TimerMessages] ✓ Kick: Sent via persistent bot connection ({username})")
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ⚠ Kick: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    # Use streamer connector directly
                    connector = self.chat_manager.connectors.get('kick')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        logger.info(f"[TimerMessages] ✓ Kick: Sent via persistent streamer connection ({username})")
                        
                        # No need to echo - Kick webhook will receive it back
                        # (message will appear in chat log via normal webhook flow)
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ✗ Kick: Streamer connector not available")
                        return False
            
            elif platform == 'youtube':
                # Use YouTube persistent connection
                logger.debug(f"[TimerMessages] YouTube send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('youtube', message, allow_fallback=False)
                    if success:
                        logger.info(f"[TimerMessages] ✓ YouTube: Sent via persistent bot connection ({username})")
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ⚠ YouTube: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    connector = self.chat_manager.connectors.get('youtube')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        logger.info(f"[TimerMessages] ✓ YouTube: Sent via persistent streamer connection ({username})")
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ✗ YouTube: Streamer connector not available")
                        return False
            
            elif platform == 'trovo':
                # Use Trovo persistent connection
                logger.debug(f"[TimerMessages] Trovo send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('trovo', message, allow_fallback=False)
                    if success:
                        logger.info(f"[TimerMessages] ✓ Trovo: Sent via persistent bot connection ({username})")
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ⚠ Trovo: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    connector = self.chat_manager.connectors.get('trovo')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        logger.info(f"[TimerMessages] ✓ Trovo: Sent via persistent streamer connection ({username})")
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ✗ Trovo: Streamer connector not available")
                        return False
            
            elif platform == 'dlive':
                # Use DLive persistent connection
                logger.debug(f"[TimerMessages] DLive send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('dlive', message, allow_fallback=False)
                    if success:
                        logger.info(f"[TimerMessages] ✓ DLive: Sent via persistent bot connection ({username})")
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ⚠ DLive: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    connector = self.chat_manager.connectors.get('dlive')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        logger.info(f"[TimerMessages] ✓ DLive: Sent via persistent streamer connection ({username})")
                        
                        # Don't echo - DLive WebSocket subscription will receive the message back
                        return True
                    else:
                        logger.warning(f"[TimerMessages] ✗ DLive: Streamer connector not available")
                        return False
            
            elif platform == 'twitter':
                # Twitter API v2 - Create tweet
                response = requests.post(
                    "https://api.twitter.com/2/tweets",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": message
                    },
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"[TimerMessages] ✓ Twitter: Sent as {account_type}")
                    return True
                else:
                    logger.warning(f"[TimerMessages] ✗ Twitter: Failed ({response.status_code})")
                    return False
            
            else:
                logger.warning(f"[TimerMessages] Platform {platform} not supported for direct sending")
                return False
                
        except Exception as e:
            logger.exception(f"[TimerMessages] Error sending to {platform}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_timer_group(self, group_name, group_widget):
        """Delete a timer group"""
        reply = QMessageBox.question(
            self,
            "Delete Group",
            f"Are you sure you want to delete the timer group '{group_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Stop timer if active
            self.stop_timer_group(group_name)
            
            # Remove from data
            del self.timer_groups[group_name]
            
            # Remove widget
            group_widget.deleteLater()
            
            self.save_timer_config()
    
    def save_timer_config(self):
        """Save timer configuration to config file"""
        config_data = self.config.get('timer_messages', {})
        config_data['groups'] = self.timer_groups
        # Use ConfigManager.set which reloads and saves atomically
        self.config.set('timer_messages', config_data)
    
    def load_timer_config(self):
        """Load timer configuration from config file"""
        config_data = self.config.get('timer_messages', {})
        groups = config_data.get('groups', {})
        
        for group_name, group_data in groups.items():
            # Skip if group_name is not a valid string
            if not isinstance(group_name, str) or not group_name.strip():
                logger.warning(f"[TimerMessages] Skipping invalid group name: {group_name}")
                continue
            
            # Ensure group_data is a dictionary
            if not isinstance(group_data, dict):
                logger.warning(f"[TimerMessages] Skipping invalid group data for: {group_name}")
                continue
            
            self.add_timer_group(
                group_name=group_name,
                display_name=group_data.get('display_name', group_name),
                interval=group_data.get('interval', 300),
                messages=group_data.get('messages', []),
                platforms=group_data.get('platforms', {}),
                send_as_streamer=group_data.get('send_as_streamer', False),
                allow_offline=group_data.get('allow_offline', False)
            )
            
            # Restore saved settings: active, allow_offline, send_as_streamer
            self.timer_groups[group_name]['active'] = group_data.get('active', False)
            self.timer_groups[group_name]['allow_offline'] = group_data.get('allow_offline', False)
            self.timer_groups[group_name]['send_as_streamer'] = group_data.get('send_as_streamer', False)
            
            # Auto-start active groups if conditions are met
            if group_data.get('active', False):
                self.start_timer_group(group_name)
    
    def update_group_display_name(self, group_name, new_display_name, group_box):
        """Update a timer group's display name as user types"""
        if group_name in self.timer_groups and new_display_name.strip():
            self.timer_groups[group_name]['display_name'] = new_display_name.strip()
            self.save_timer_config()
    
    def setup_stream_listeners(self):
        """Setup listeners for when streams go live"""
        # Connect to each connector's connection status
        for platform, connector in self.chat_manager.connectors.items():
            if hasattr(connector, 'connection_status'):
                connector.connection_status.connect(lambda status, p=platform: self.on_stream_status_changed(p, status))
    
    def on_stream_status_changed(self, platform, status):
        """Handle stream status changes and start/stop timers accordingly"""
        # Check if any stream is now live
        any_live = False
        if self.chat_manager:
            for connector in self.chat_manager.connectors.values():
                if hasattr(connector, 'connected') and connector.connected:
                    any_live = True
                    break
        
        was_live = self.any_stream_live
        self.any_stream_live = any_live
        
        # If we just went live and have active groups, start them
        if any_live and not was_live:
            logger.info(f"[TimerMessages] Stream started, activating timer groups")
            for group_name, group in self.timer_groups.items():
                if group.get('active', False) and group_name not in self.timer_state:
                    self.start_timer_group(group_name)
        
        # If all streams stopped, stop all timers
        elif not any_live and was_live:
            logger.info(f"[TimerMessages] All streams stopped, pausing timer groups")
            for group_name in list(self.timer_state.keys()):
                self.stop_timer_group(group_name)
    
    def load_platform_icon(self, platform_name, icon_file):
        """Load platform icon for tab"""
        try:
            # Determine base directory (for PyInstaller compatibility)
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # If icon_file is None, try to use external URL fallback
            if icon_file is None:
                # For platforms without local icons (like Twitch), use external URL
                from ui.platform_icons import PLATFORM_COLORS
                icon_url = PLATFORM_COLORS.get(platform_name, '')
                if icon_url:
                    # Download and create pixmap from URL
                    import urllib.request
                    try:
                        with urllib.request.urlopen(icon_url, timeout=2) as response:
                            data = response.read()
                            pixmap = QPixmap()
                            pixmap.loadFromData(data)
                            if not pixmap.isNull():
                                scaled_pixmap = pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, 
                                                              Qt.TransformationMode.SmoothTransformation)
                                return QIcon(scaled_pixmap)
                    except Exception as e:
                        logger.exception(f"[AutomationPage] Failed to download icon from URL for {platform_name}: {e}")
                return QIcon()
            
            # Try to load icon from resources - check multiple locations
            icon_paths = [
                os.path.join(base_dir, 'resources', 'badges', platform_name, icon_file),
                os.path.join(base_dir, 'resources', 'badges', icon_file),  # For trovo_logo.svg at root level
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    # Check if it's an SVG file
                    if icon_path.lower().endswith('.svg'):
                        # Use QSvgRenderer for SVG files
                        renderer = QSvgRenderer(icon_path)
                        if renderer.isValid():
                            pixmap = QPixmap(20, 20)
                            pixmap.fill(Qt.GlobalColor.transparent)
                            painter = QPainter(pixmap)
                            renderer.render(painter)
                            painter.end()
                            return QIcon(pixmap)
                    else:
                        # Use QPixmap for PNG/JPG files
                        pixmap = QPixmap(icon_path)
                        if not pixmap.isNull():
                            # Scale icon to appropriate size for tabs
                            scaled_pixmap = pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, 
                                                          Qt.TransformationMode.SmoothTransformation)
                            return QIcon(scaled_pixmap)
        except Exception as e:
            logger.exception(f"[AutomationPage] Failed to load icon for {platform_name}: {e}")
        
        # Return empty icon if loading fails
        return QIcon()