from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

# --- Custom ToggleSwitch Widget ---
class ToggleSwitch(QCheckBox):
        
    def mousePressEvent(self, event):
        if self.isEnabled():
            self.setChecked(not self.isChecked())
        super().mousePressEvent(event)
        
    def __init__(self, parent=None, width=34, height=17, bg_color_on="#4a90e2", bg_color_off="#555", knob_color="#fff", border_color="#888"):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._width = width
        self._height = height
        self._bg_color_on = QColor(bg_color_on)
        self._bg_color_off = QColor(bg_color_off)
        self._knob_color = QColor(knob_color)
        self._border_color = QColor(border_color)
        self.setFixedSize(self._width, self._height)
        self._offset = 2.0  # Always initialize to a valid float
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self._offset = self._get_offset_for_state(self.isChecked())
        self.stateChanged.connect(self._on_state_changed)

    def _get_offset_for_state(self, checked):
        # Always return a float, never None
        try:
            return float(self._width - self._height + 2) if checked else float(2)
        except Exception:
            return 2.0

    def _on_state_changed(self, state):
        end = self._get_offset_for_state(state == Qt.CheckState.Checked.value)
        start = self._offset if self._offset is not None else 2.0
        if end is None:
            end = 2.0
        self._anim.stop()
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        try:
            self._anim.valueChanged.disconnect(self._on_anim_value_changed)
        except TypeError:
            pass
        self._anim.valueChanged.connect(self._on_anim_value_changed)
        self._anim.start()

    def _on_anim_value_changed(self, value):
        self._offset = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRect(0, 0, self._width, self._height)
        # Draw background
        bg_color = self._bg_color_on if self.isChecked() else self._bg_color_off
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(self._border_color, 2))
        painter.drawRoundedRect(rect, self._height / 2, self._height / 2)
        # Draw knob
        knob_diameter = self._height - 4
        knob_rect = QRect(int(self._offset), 2, knob_diameter, knob_diameter)
        painter.setBrush(QBrush(self._knob_color))
        painter.setPen(QPen(self._border_color, 1))
        painter.drawEllipse(knob_rect)

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        return self.size()

    def get_offset(self):
        # Always return a valid float
        try:
            return float(self._offset)
        except Exception:
            return 2.0

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = pyqtProperty(float, fget=get_offset, fset=set_offset)
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
        print("\n[DIAGNOSTICS] Variables Tab Layout:")
        print(f"  TabWidget geometry: {self.tab_widget.geometry()}")
        print(f"  Variables tab QWidget geometry: {self.variables_tab.geometry()}")
        print(f"  Variables tab QWidget size: {self.variables_tab.size()}")
        print(f"  Variables tab QWidget minimumSize: {self.variables_tab.minimumSize()}")
        print(f"  Variables tab QWidget maximumSize: {self.variables_tab.maximumSize()}")
        margins = self.variables_tab.contentsMargins()
        print(f"  Variables tab QWidget contentsMargins: left={margins.left()}, top={margins.top()}, right={margins.right()}, bottom={margins.bottom()}")
        print(f"  Variables rows container count: {self.variables_rows_container.count()}")
        for i in range(self.variables_rows_container.count()):
            row_widget = self.variables_rows_container.itemAt(i).widget()
            if row_widget:
                print(f"    Row {i}: {row_widget.geometry()} size={row_widget.size()} min={row_widget.minimumSize()} max={row_widget.maximumSize()} policy={row_widget.sizePolicy()}")
                for child in row_widget.findChildren(QWidget):
                    print(f"      Child: {type(child).__name__} geometry={child.geometry()} size={child.size()} min={child.minimumSize()} max={child.maximumSize()} policy={child.sizePolicy()}")

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
        print(f"[VariablesTab] DEBUG: add_variable_row called with name='{name}', value='{value}', default='{default}', initialize={initialize}")
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
        # Save when Value or Default field loses focus
        row_widget.value_edit.installEventFilter(row_widget)
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
        print(f"[VariablesTab] DEBUG: add_variable_row finished, row widget added")
        return row_widget

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
        print("[VariablesTab] DEBUG: Add Variable button clicked")
        self.add_variable_row()
        print("[VariablesTab] DEBUG: add_variable_row() called")
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
        QTimer.singleShot(500, self.load_all_platform_info)
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
        self.stream_info_tab = self.create_stream_info_tab()

        self.tab_widget.addTab(self.variables_tab, "🔣 Variables")
        self.tab_widget.addTab(self.functions_tab, "🧩 Functions")
        self.tab_widget.addTab(self.commands_tab, "🎯 Triggers")
        self.tab_widget.addTab(self.timers_tab, "⏰ Timers")
        self.tab_widget.addTab(self.events_tab, "⚡ Events")
        self.tab_widget.addTab(self.stream_info_tab, "📡 Stream Info")

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
    
    def add_timer_group(self, group_name=None, display_name=None, interval=300, messages=None, platforms=None, send_as_streamer=False):
        """Add a new timer message group"""
        # Validate group_name if provided
        if group_name is not None and not isinstance(group_name, str):
            print(f"[TimerMessages] Invalid group_name type: {type(group_name)}, value: {group_name}")
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
            'allow_offline': False,
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
        send_as_streamer_checkbox = QCheckBox("Send as Streamer")
        send_as_streamer_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-weight: bold;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 8px;
                height: 8px;
                background-color: #555555;
                border: 2px solid #ffffff;
                border-radius: 5px;
            }
            QCheckBox::indicator:checked {
                background-color: #ffffff;
                border: 2px solid #ffffff;
            }
        """)
        send_as_streamer_checkbox.setChecked(self.timer_groups[group_name].get('send_as_streamer', False))
        send_as_streamer_checkbox.stateChanged.connect(lambda state: self.update_send_as_streamer(group_name, state == Qt.CheckState.Checked.value))
        send_as_streamer_checkbox.setToolTip("Send messages using streamer account instead of bot account")
        send_allow_vbox.addWidget(send_as_streamer_checkbox)

        allow_offline_checkbox = QCheckBox("Allow Offline")
        allow_offline_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-weight: bold;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 8px;
                height: 8px;
                background-color: #555555;
                border: 2px solid #ffffff;
                border-radius: 5px;
            }
            QCheckBox::indicator:checked {
                background-color: #ffffff;
                border: 2px solid #ffffff;
            }
        """)
        allow_offline_checkbox.setChecked(self.timer_groups[group_name].get('allow_offline', False))
        allow_offline_checkbox.stateChanged.connect(lambda state: self.update_allow_offline(group_name, state == Qt.CheckState.Checked.value))
        allow_offline_checkbox.setToolTip("Allow this group to send messages even when no streams are active")
        send_allow_vbox.addWidget(allow_offline_checkbox)
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
        
        checkbox = QCheckBox(f"  {platform.title()}")
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-weight: normal;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 8px;
                height: 8px;
                background-color: #555555;
                border: 2px solid #ffffff;
                border-radius: 5px;
            }
            QCheckBox::indicator:checked {
                background-color: #ffffff;
                border: 2px solid #ffffff;
            }
        """)
        checkbox.setChecked(self.timer_groups[group_name]['platforms'].get(platform, False))
        checkbox.stateChanged.connect(lambda state, p=platform, g=group_name: self.update_platform_toggle(g, p, state == Qt.CheckState.Checked.value))
        
        # Try to load platform icon
        icon_path = self.get_platform_icon_path(platform)
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                # Scale icon to checkbox size (16x16)
                scaled_pixmap = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon = QIcon(scaled_pixmap)
                checkbox.setIcon(icon)
                checkbox.setIconSize(QSize(16, 16))
        
        return checkbox
    
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
            'trovo': os.path.join(base_dir, 'resources', 'icons', 'trovo.png'),
            'twitter': os.path.join(base_dir, 'resources', 'icons', 'twitter.png'),
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
                    
                    # Determine which account to use: bot (if available), otherwise streamer
                    if send_as_streamer:
                        # Force use of streamer account
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        account_type = 'streamer'
                    else:
                        # Prefer bot account, fallback to streamer
                        bot_username = platform_config.get('bot_username')
                        bot_token = platform_config.get('bot_token')
                        
                        if bot_username and bot_token:
                            username = bot_username
                            token = bot_token
                            account_type = 'bot'
                        else:
                            username = platform_config.get('streamer_username')
                            token = platform_config.get('streamer_token')
                            account_type = 'streamer'
                    
                    if not username or not token:
                        continue
                    
                    # Send message via direct API call
                    success = self.send_message_as_account(platform, message, username, token, account_type)
                    if success:
                        platforms_sent.append(f"{platform}({account_type})")
                        
                except Exception as e:
                    print(f"[TimerMessages] Error sending specific message to {platform}: {e}")
        
        if platforms_sent:
            print(f"[TimerMessages] SPECIFIC SEND from '{group_name}' to {platforms_sent}: {message}")
        else:
            QMessageBox.warning(
                self,
                "Send Failed",
                f"Could not send message to any platform.\n\n"
                f"Make sure platforms are enabled and credentials are configured."
            )
    
    def update_send_as_streamer(self, group_name, enabled):
        """Update send_as_streamer setting for a timer group"""
        if group_name in self.timer_groups:
            self.timer_groups[group_name]['send_as_streamer'] = enabled
            self.save_timer_config()
            print(f"[TimerMessages] Group '{group_name}' send_as_streamer: {enabled}")
    
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
        
        # Send to enabled platforms
        platforms_sent = []
        for platform, enabled in group['platforms'].items():
            if enabled and self.chat_manager:
                try:
                    # Reload config to get fresh bot credentials
                    from core.config import ConfigManager
                    fresh_config = ConfigManager()
                    platform_config = fresh_config.get_platform_config(platform)
                    
                    # Determine which account to use: bot (if available), otherwise streamer
                    if send_as_streamer:
                        # Force use of streamer account
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        account_type = 'streamer'
                        print(f"[TimerMessages] Test: {platform} - Using STREAMER account (send_as_streamer=True)")
                    else:
                        # Prefer bot account, fallback to streamer
                        bot_username = platform_config.get('bot_username')
                        bot_token = platform_config.get('bot_token')
                        print(f"[TimerMessages] Test: {platform} - Checking bot credentials: username='{bot_username}', has_token={bool(bot_token)}")
                        
                        if bot_username and bot_token:
                            username = bot_username
                            token = bot_token
                            account_type = 'bot'
                            print(f"[TimerMessages] Test: {platform} - Using BOT account: {bot_username}")
                        else:
                            username = platform_config.get('streamer_username')
                            token = platform_config.get('streamer_token')
                            account_type = 'streamer'
                            print(f"[TimerMessages] Test: {platform} - Bot not available, falling back to STREAMER account")
                    
                    if not username or not token:
                        print(f"[TimerMessages] Test: No credentials for {platform} ({account_type} account)")
                        continue
                    
                    # Send message via direct API call (don't touch the active connection)
                    success = self.send_message_as_account(platform, message, username, token, account_type)
                    if success:
                        platforms_sent.append(f"{platform}({account_type})")
                        
                except Exception as e:
                    print(f"[TimerMessages] Test: Error sending to {platform}: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"[TimerMessages] TEST SEND from '{group_name}' to {platforms_sent}: {message}")
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
                if child.__class__.__name__ == "ToggleSwitch":
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
            print(f"[TimerMessages] Group '{group_name}' has no messages, skipping")
            return
        
        # Check if any stream is live (unless allow_offline is enabled)
        if not group.get('allow_offline', False) and not self.any_stream_live:
            print(f"[TimerMessages] Group '{group_name}' waiting for stream to start (allow_offline=False)")
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
        print(f"[TimerMessages] Started group '{display_name}' with {len(group['messages'])} messages, interval: {group['interval']}s (first message in {group['interval']}s){offline_status}")
    
    def stop_timer_group(self, group_name):
        """Stop sending messages for a timer group"""
        if group_name in self.timer_state:
            timer = self.timer_state[group_name].get('timer')
            if timer:
                timer.stop()
                timer.deleteLater()
            del self.timer_state[group_name]
            print(f"[TimerMessages] Stopped group '{group_name}'")
    
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
            print(f"[TimerMessages] Group '{group_name}' reshuffled messages")
        
        # Get next message
        message = state['remaining_messages'].pop(0)
        
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
                    
                    # Determine which account to use: bot (if available), otherwise streamer
                    if send_as_streamer:
                        # Force use of streamer account
                        username = platform_config.get('streamer_username')
                        token = platform_config.get('streamer_token')
                        account_type = 'streamer'
                    else:
                        # Prefer bot account, fallback to streamer
                        bot_username = platform_config.get('bot_username')
                        bot_token = platform_config.get('bot_token')
                        
                        if bot_username and bot_token:
                            username = bot_username
                            token = bot_token
                            account_type = 'bot'
                        else:
                            username = platform_config.get('streamer_username')
                            token = platform_config.get('streamer_token')
                            account_type = 'streamer'
                    
                    if not username or not token:
                        print(f"[TimerMessages] No credentials for {platform} ({account_type} account)")
                        continue
                    
                    # Send message via direct API call (don't touch the active connection)
                    success = self.send_message_as_account(platform, message, username, token, account_type)
                    if success:
                        platforms_sent.append(f"{platform}({account_type})")
                        
                except Exception as e:
                    print(f"[TimerMessages] Error sending to {platform}: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"[TimerMessages] Sent message from '{group_name}' to {platforms_sent}: {message[:50]}...")
    
    def send_message_as_account(self, platform, message, username, token, account_type):
        """Send a message to a platform using specific account credentials"""
        import requests
        
        try:
            # For Twitch, use the appropriate persistent connection
            if platform == 'twitch':
                print(f"[TimerMessages] Twitch send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Use persistent bot connector from chat_manager
                    print(f"[TimerMessages] Calling sendMessageAsBot for Twitch...")
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('twitch', message, allow_fallback=False)
                    if success:
                        print(f"[TimerMessages] ✓ Twitch: Sent via persistent bot connection ({username})")
                        # Don't echo - bot connector will read its own message back from IRC
                        return True
                    else:
                        print(f"[TimerMessages] ⚠ Twitch: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    # Use streamer connector directly
                    connector = self.chat_manager.connectors.get('twitch')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        print(f"[TimerMessages] ✓ Twitch: Sent via persistent streamer connection ({username})")
                        
                        # Don't echo - Twitch IRC echoes back our own messages
                        
                        return True
                    else:
                        print(f"[TimerMessages] ✗ Twitch: Streamer connector not available")
                        return False
            
            elif platform == 'kick':
                # Use Kick persistent connection
                print(f"[TimerMessages] Kick send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Use persistent bot connector from chat_manager
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('kick', message, allow_fallback=False)
                    if success:
                        print(f"[TimerMessages] ✓ Kick: Sent via persistent bot connection ({username})")
                        return True
                    else:
                        print(f"[TimerMessages] ⚠ Kick: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    # Use streamer connector directly
                    connector = self.chat_manager.connectors.get('kick')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        print(f"[TimerMessages] ✓ Kick: Sent via persistent streamer connection ({username})")
                        
                        # No need to echo - Kick webhook will receive it back
                        # (message will appear in chat log via normal webhook flow)
                        return True
                    else:
                        print(f"[TimerMessages] ✗ Kick: Streamer connector not available")
                        return False
            
            elif platform == 'youtube':
                # Use YouTube persistent connection
                print(f"[TimerMessages] YouTube send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('youtube', message, allow_fallback=False)
                    if success:
                        print(f"[TimerMessages] ✓ YouTube: Sent via persistent bot connection ({username})")
                        return True
                    else:
                        print(f"[TimerMessages] ⚠ YouTube: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    connector = self.chat_manager.connectors.get('youtube')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        print(f"[TimerMessages] ✓ YouTube: Sent via persistent streamer connection ({username})")
                        
                        # Echo the message to chat log
                        from datetime import datetime
                        metadata = {
                            'timestamp': datetime.now(),
                            'color': '#22B2B2',
                            'badges': [],
                            'emotes': ''
                        }
                        self.chat_manager.message_received.emit('youtube', username, message, metadata)
                        return True
                    else:
                        print(f"[TimerMessages] ✗ YouTube: Streamer connector not available")
                        return False
            
            elif platform == 'trovo':
                # Use Trovo persistent connection
                print(f"[TimerMessages] Trovo send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('trovo', message, allow_fallback=False)
                    if success:
                        print(f"[TimerMessages] ✓ Trovo: Sent via persistent bot connection ({username})")
                        return True
                    else:
                        print(f"[TimerMessages] ⚠ Trovo: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    connector = self.chat_manager.connectors.get('trovo')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        print(f"[TimerMessages] ✓ Trovo: Sent via persistent streamer connection ({username})")
                        
                        # Echo the message to chat log
                        from datetime import datetime
                        metadata = {
                            'timestamp': datetime.now(),
                            'color': '#22B2B2',
                            'badges': [],
                            'emotes': ''
                        }
                        self.chat_manager.message_received.emit('trovo', username, message, metadata)
                        return True
                    else:
                        print(f"[TimerMessages] ✗ Trovo: Streamer connector not available")
                        return False
            
            elif platform == 'dlive':
                # Use DLive persistent connection
                print(f"[TimerMessages] DLive send: account_type={account_type}, username={username}")
                if account_type == 'bot':
                    # Disable fallback to ensure only bot sends (no streamer fallback)
                    success = self.chat_manager.sendMessageAsBot('dlive', message, allow_fallback=False)
                    if success:
                        print(f"[TimerMessages] ✓ DLive: Sent via persistent bot connection ({username})")
                        return True
                    else:
                        print(f"[TimerMessages] ⚠ DLive: Bot connector not available")
                        return False
                else:  # account_type == 'streamer'
                    connector = self.chat_manager.connectors.get('dlive')
                    if connector and hasattr(connector, 'send_message') and getattr(connector, 'connected', False):
                        connector.send_message(message)
                        print(f"[TimerMessages] ✓ DLive: Sent via persistent streamer connection ({username})")
                        
                        # Don't echo - DLive WebSocket subscription will receive the message back
                        return True
                    else:
                        print(f"[TimerMessages] ✗ DLive: Streamer connector not available")
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
                    print(f"[TimerMessages] ✓ Twitter: Sent as {account_type}")
                    return True
                else:
                    print(f"[TimerMessages] ✗ Twitter: Failed ({response.status_code})")
                    return False
            
            else:
                print(f"[TimerMessages] Platform {platform} not supported for direct sending")
                return False
                
        except Exception as e:
            print(f"[TimerMessages] Error sending to {platform}: {e}")
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
        # CRITICAL: Reload config before saving to avoid overwriting other platforms' data
        self.config.config = self.config.load()
        config_data = self.config.get('timer_messages', {})
        config_data['groups'] = self.timer_groups
        self.config.set('timer_messages', config_data)
        self.config.save()
    
    def load_timer_config(self):
        """Load timer configuration from config file"""
        config_data = self.config.get('timer_messages', {})
        groups = config_data.get('groups', {})
        
        for group_name, group_data in groups.items():
            # Skip if group_name is not a valid string
            if not isinstance(group_name, str) or not group_name.strip():
                print(f"[TimerMessages] Skipping invalid group name: {group_name}")
                continue
            
            # Ensure group_data is a dictionary
            if not isinstance(group_data, dict):
                print(f"[TimerMessages] Skipping invalid group data for: {group_name}")
                continue
            
            self.add_timer_group(
                group_name=group_name,
                display_name=group_data.get('display_name', group_name),
                interval=group_data.get('interval', 300),
                messages=group_data.get('messages', []),
                platforms=group_data.get('platforms', {}),
                send_as_streamer=group_data.get('send_as_streamer', False)
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
            print(f"[TimerMessages] Stream started, activating timer groups")
            for group_name, group in self.timer_groups.items():
                if group.get('active', False) and group_name not in self.timer_state:
                    self.start_timer_group(group_name)
        
        # If all streams stopped, stop all timers
        elif not any_live and was_live:
            print(f"[TimerMessages] All streams stopped, pausing timer groups")
            for group_name in list(self.timer_state.keys()):
                self.stop_timer_group(group_name)
    
    def create_stream_info_tab(self):
        """Create the Stream Info tab"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title
        title = QLabel("Stream Information")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff;")
        main_layout.addWidget(title)
        
        description = QLabel("Manage stream titles, categories, tags, and go-live notifications across all platforms.")
        description.setStyleSheet("color: #cccccc; margin-bottom: 15px;")
        main_layout.addWidget(description)
        
        # Global Settings Section (always visible at top)
        global_group = self.create_global_stream_section()
        main_layout.addWidget(global_group)
        
        # Platform-specific tabs
        platform_tabs = QTabWidget()
        platform_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                background-color: #1e1e1e;
                padding: 10px;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #cccccc;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #353535;
            }
        """)
        
        # Platform configurations: (name, icon_file, has_notification, has_category, has_tags)
        platforms = [
            ('Twitch', None, True, True, True),  # Uses external URL fallback
            ('YouTube', 'youtube_logo.svg', True, True, False),
            ('Kick', 'kick_logo.jpg', True, True, True),
            ('Trovo', None, True, True, False),  # Uses external URL fallback, no tags support
            ('DLive', 'dlive_logo.png', True, False, True),
        ]
        
        for platform_name, icon_file, has_notification, has_category, has_tags in platforms:
            # Create scrollable content for each platform tab
            platform_widget = QWidget()
            platform_layout = QVBoxLayout(platform_widget)
            platform_layout.setContentsMargins(10, 10, 10, 10)
            
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
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            
            # Add platform section
            platform_section = self.create_platform_section(
                platform_name, has_notification, has_category, has_tags
            )
            scroll_layout.addWidget(platform_section)
            scroll_layout.addStretch()
            
            scroll.setWidget(scroll_content)
            platform_layout.addWidget(scroll)
            
            # Load platform icon and add tab
            icon = self.load_platform_icon(platform_name.lower(), icon_file)
            platform_tabs.addTab(platform_widget, icon, platform_name)
        
        main_layout.addWidget(platform_tabs, 1)
        
        return widget
    
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
                        print(f"[AutomationPage] Failed to download icon from URL for {platform_name}: {e}")
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
            print(f"[AutomationPage] Failed to load icon for {platform_name}: {e}")
        
        # Return empty icon if loading fails
        return QIcon()
    
    def create_global_stream_section(self):
        """Create global stream settings section"""
        group = QGroupBox("Global Settings")
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
        
        # Global Stream Title
        title_layout = QHBoxLayout()
        title_label = QLabel("Stream Title:")
        title_label.setStyleSheet("color: #ffffff; font-weight: normal;")
        title_label.setMinimumWidth(150)
        self.global_title_input = QLineEdit()
        self.global_title_input.setPlaceholderText("Enter global stream title...")
        self.global_title_input.setStyleSheet("""
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
        title_layout.addWidget(self.global_title_input)
        layout.addLayout(title_layout)
        
        # Global Go-Live Notification
        notif_layout = QVBoxLayout()
        notif_label = QLabel("Go-Live Notification:")
        notif_label.setStyleSheet("color: #ffffff; font-weight: normal; margin-bottom: 5px;")
        self.global_notification_input = QTextEdit()
        self.global_notification_input.setPlaceholderText("Enter notification message for when you go live...")
        self.global_notification_input.setMaximumHeight(80)
        self.global_notification_input.setStyleSheet("""
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
        notif_layout.addWidget(self.global_notification_input)
        layout.addLayout(notif_layout)
        
        # Apply to All button
        apply_btn = QPushButton("Apply to All Platforms")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a5d8f;
            }
        """)
        apply_btn.clicked.connect(self.apply_global_settings)
        layout.addWidget(apply_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        return group
    
    def create_platform_section(self, platform_name, has_notification, has_category, has_tags):
        """Create a platform-specific settings section"""
        group = QGroupBox(f"{platform_name} Settings")
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
            category_layout = QHBoxLayout()
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
            category_layout.addWidget(category_label)
            category_layout.addWidget(category_input)
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
        if platform_name == 'Twitch':
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
    
    def apply_global_settings(self):
        """Apply global settings to all platforms"""
        # TODO: Implement applying global title and notification to all platforms
        global_title = self.global_title_input.text()
        global_notif = self.global_notification_input.toPlainText()
        
        platforms = ['Twitch', 'YouTube', 'Kick', 'Trovo', 'DLive']
        for platform in platforms:
            title_field = self.findChild(QLineEdit, f"{platform}_title")
            if title_field and global_title:
                title_field.setText(global_title)
            
            notif_field = self.findChild(QTextEdit, f"{platform}_notification")
            if notif_field and global_notif:
                notif_field.setText(global_notif)
        
        print("[AutomationPage] Applied global settings to all platforms")
    
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
                
                # Insert before stretch
                layout.insertWidget(layout.count() - 1, tag_chip)
                
                print(f"[AutomationPage] Added tag '{tag_text}' for {platform_name}")
    
    def remove_tag(self, platform_name, tag_text, tag_chip):
        """Remove a tag from the platform"""
        tag_chip.deleteLater()
        print(f"[AutomationPage] Removed tag '{tag_text}' from {platform_name}")
    
    def refresh_platform_info(self, platform_name):
        """Refresh stream info from the platform API"""
        print(f"[AutomationPage] Refreshing stream info for {platform_name}")
        
        # Get the platform connector
        platform_id = platform_name.lower()
        connector = self.chat_manager.connectors.get(platform_id)
        
        if not connector:
            print(f"[AutomationPage] No connector found for {platform_name}")
            return
        
        # Debug connector attributes
        print(f"[{platform_name}] Connector: {connector.__class__.__name__}")
        print(f"[{platform_name}] Is connected: {getattr(connector, 'is_connected', 'N/A')}")
        
        try:
            if platform_name == 'Twitch':
                self.refresh_twitch_info(connector)
            elif platform_name == 'YouTube':
                self.refresh_youtube_info(connector)
            elif platform_name == 'Kick':
                self.refresh_kick_info(connector)
            elif platform_name == 'Trovo':
                self.refresh_trovo_info(connector)
            elif platform_name == 'DLive':
                self.refresh_dlive_info(connector)
        except Exception as e:
            print(f"[AutomationPage] Error refreshing {platform_name} info: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_twitch_info(self, connector):
        """Refresh Twitch stream info"""
        import requests
        
        print(f"[Twitch] Attempting to refresh info...")
        
        # Try to get credentials from config if connector doesn't have them
        twitch_config = self.config.config.get('platforms', {}).get('twitch', {})
        
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
                    if 'title' in info and 'Twitch' in self.platform_widgets:
                        self.platform_widgets['Twitch']['title'].setText(info['title'])
                        print(f"[Twitch] Loaded title: {info['title']}")
                    
                    # Update category
                    if 'game_name' in info and 'Twitch' in self.platform_widgets:
                        category_widget = self.platform_widgets['Twitch'].get('category')
                        if category_widget:
                            category_widget.setText(info['game_name'])
                            print(f"[Twitch] Loaded category: {info['game_name']}")
                    
                    # Update tags (tags are now in the channel info as a list of strings)
                    if 'tags' in info and info['tags'] and 'Twitch' in self.platform_widgets:
                        tags_display = self.platform_widgets['Twitch'].get('tags_display')
                        if tags_display:
                            # Clear existing tags
                            layout = tags_display.layout()
                            while layout.count() > 1:  # Keep the stretch
                                item = layout.takeAt(0)
                                if item.widget():
                                    item.widget().deleteLater()
                            
                            # Add new tags
                            for tag_name in info['tags']:
                                self.add_tag_chip('Twitch', tag_name, tags_display)
                            print(f"[Twitch] Loaded {len(info['tags'])} tags")
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
                    if 'title' in info and 'YouTube' in self.platform_widgets:
                        self.platform_widgets['YouTube']['title'].setText(info['title'])
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
        kick_config = self.config.config.get('platforms', {}).get('kick', {})
        
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
                    if 'session_title' in stream_info and 'Kick' in self.platform_widgets:
                        self.platform_widgets['Kick']['title'].setText(stream_info['session_title'])
                        print(f"[Kick] Loaded title: {stream_info['session_title']}")
                    
                    # Update category
                    if stream_info.get('categories') and 'Kick' in self.platform_widgets:
                        category_widget = self.platform_widgets['Kick'].get('category')
                        if category_widget and stream_info['categories']:
                            category_name = stream_info['categories'][0].get('name', '')
                            category_widget.setText(category_name)
                            print(f"[Kick] Loaded category: {category_name}")
                    
                    # Update tags
                    if 'Kick' in self.platform_widgets:
                        print(f"[Kick] Checking for tags in stream_info...")
                        print(f"[Kick] stream_info keys: {list(stream_info.keys())}")
                        if 'tags' in stream_info:
                            print(f"[Kick] Tags found: {stream_info['tags']}")
                        
                        if stream_info.get('tags'):
                            tags_display = self.platform_widgets['Kick'].get('tags_display')
                            if tags_display:
                                # Clear existing tags
                                layout = tags_display.layout()
                                while layout.count() > 1:  # Keep the stretch
                                    item = layout.takeAt(0)
                                    if item.widget():
                                        item.widget().deleteLater()
                                
                                # Add new tags (Kick returns tags as a list of strings)
                                for tag_name in stream_info['tags']:
                                    self.add_tag_chip('Kick', tag_name, tags_display)
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
        trovo_config = self.config.config.get('platforms', {}).get('trovo', {})
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
                if 'live_title' in data and 'Trovo' in self.platform_widgets:
                    self.platform_widgets['Trovo']['title'].setText(data['live_title'])
                    print(f"[Trovo] Loaded title: {data['live_title']}")
                
                # Update category
                if 'category_name' in data and 'Trovo' in self.platform_widgets:
                    category_widget = self.platform_widgets['Trovo'].get('category')
                    if category_widget:
                        category_widget.setText(data['category_name'])
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
        
        # Insert before stretch
        layout.insertWidget(layout.count() - 1, tag_chip)
    
    def load_all_platform_info(self):
        """Load stream info for all platforms on startup"""
        print("[AutomationPage] Loading stream info for all platforms...")
        print(f"[AutomationPage] Platform widgets available: {list(self.platform_widgets.keys())}")
        
        platforms = ['Twitch', 'YouTube', 'Kick', 'Trovo', 'DLive']
        for platform in platforms:
            try:
                # First load from local config
                self.load_local_platform_info(platform)
                # Then try to refresh from API (will update title/category from live data)
                self.refresh_platform_info(platform)
            except Exception as e:
                print(f"[AutomationPage] Error loading {platform} info: {e}")
    
    def load_local_platform_info(self, platform_name):
        """Load saved stream info from local config"""
        platform_key = platform_name.lower()
        
        if platform_name not in self.platform_widgets:
            print(f"[AutomationPage] No widgets found for {platform_name}")
            return
        
        stream_info = self.config.config.get('platforms', {}).get(platform_key, {}).get('stream_info', {})
        
        if not stream_info:
            print(f"[{platform_name}] No saved stream info in config")
            return
        
        widgets = self.platform_widgets[platform_name]
        
        # Load title
        if 'title' in stream_info and 'title' in widgets:
            widgets['title'].setText(stream_info['title'])
            print(f"[{platform_name}] Loaded saved title: {stream_info['title']}")
        
        # Load notification
        if 'notification' in stream_info and 'notification' in widgets:
            widgets['notification'].setPlainText(stream_info['notification'])
            print(f"[{platform_name}] Loaded saved notification")
        
        # Load category
        if 'category' in stream_info and 'category' in widgets:
            widgets['category'].setText(stream_info['category'])
            print(f"[{platform_name}] Loaded saved category: {stream_info['category']}")
        
        # Load tags
        if 'tags' in stream_info and 'tags_display' in widgets:
            tags_display = widgets['tags_display']
            # Clear existing tags
            layout = tags_display.layout()
            while layout.count() > 1:  # Keep the stretch
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Add saved tags
            for tag in stream_info['tags']:
                self.add_tag_chip(platform_name, tag, tags_display)
            print(f"[{platform_name}] Loaded {len(stream_info['tags'])} saved tags")
    
    def save_platform_info(self, platform_name):
        """Save stream info locally and update platform API"""
        print(f"[AutomationPage] Saving stream info for {platform_name}")
        
        if platform_name not in self.platform_widgets:
            print(f"[AutomationPage] No widgets found for {platform_name}")
            return
        
        widgets = self.platform_widgets[platform_name]
        
        # Save to local config
        platform_key = platform_name.lower()
        if 'stream_info' not in self.config.config['platforms'].get(platform_key, {}):
            if platform_key not in self.config.config['platforms']:
                self.config.config['platforms'][platform_key] = {}
            self.config.config['platforms'][platform_key]['stream_info'] = {}
        
        stream_info = self.config.config['platforms'][platform_key]['stream_info']
        
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
        
        # CRITICAL: Reload config before saving to avoid overwriting other platforms' data
        self.config.config = self.config.load()
        self.config.save()
        print(f"[AutomationPage] Saved {platform_name} stream info to local config")
        print(f"[AutomationPage] Saved data: {stream_info}")
        
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
    
    def show_reconnect_instructions(self, platform_name):
        """Show instructions for reconnecting with updated OAuth scopes"""
        from PyQt6.QtWidgets import QMessageBox
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(f"Reconnect {platform_name}")
        msg.setText(f"To enable API updates for {platform_name}, you need to reconnect with updated permissions.")
        
        if platform_name == 'Twitch':
            msg.setInformativeText(
                "Steps to get a new Twitch token:\n\n"
                "1. Go to: https://twitchtokengenerator.com/\n"
                "2. Click 'Custom Scope Token'\n"
                "3. Select these scopes:\n"
                "   ✓ chat:read\n"
                "   ✓ chat:edit\n"
                "   ✓ user:edit:broadcast\n"
                "   ✓ channel:manage:broadcast\n"
                "4. Click 'Generate Token' and authorize\n"
                "5. Copy the 'Access Token'\n"
                "6. In the Connections page, disconnect Twitch\n"
                "7. Clear the old token from config:\n"
                "   Edit: ~/.audiblezenbot/config.json\n"
                "   Set: platforms.twitch.oauth_token = \"\"\n"
                "8. Restart the app\n"
                "9. In Connections, paste the new token and connect\n\n"
                "Alternative: Use Twitch CLI to generate token with proper scopes."
            )
        
        msg.exec()
    
    def update_platform_api(self, platform_name, stream_info):
        """Update platform API with stream info (title, category, tags)"""
        try:
            if platform_name == 'Twitch':
                return self.update_twitch_api(stream_info)
            elif platform_name == 'Trovo':
                return self.update_trovo_api(stream_info)
            elif platform_name == 'Kick':
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
                if 'Twitch' in self.platform_widgets:
                    warning_label = self.platform_widgets['Twitch'].get('oauth_warning')
                    reconnect_btn = self.platform_widgets['Twitch'].get('reconnect_btn')
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
        
        trovo_config = self.config.config.get('platforms', {}).get('trovo', {})
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
            kick_config = self.config.config.get('platforms', {}).get('kick', {})
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

