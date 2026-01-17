from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QRadioButton, QPushButton
)
from PyQt6.QtCore import Qt

class VariableRowWidget(QWidget):
    def __init__(self, name='', value='', default='', var_type='string', initialize=False, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))

        # Top row: Selection checkbox, Name (editable, styled as title), and Initialize?
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        from PyQt6.QtWidgets import QCheckBox
        self.select_checkbox = QCheckBox()
        self.select_checkbox.setStyleSheet('QCheckBox { margin-left: 2px; margin-right: 6px; }')
        top_row.addWidget(self.select_checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText('Variable name')
        self.name_edit.setStyleSheet('''
            QLineEdit {
                background: transparent;
                border: none;
                color: #fff;
                font-size: 15px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
        ''')
        self.name_edit.setMinimumWidth(120)
        top_row.addWidget(self.name_edit, 1)

        from ui.ui_elements import ToggleSwitch
        # Use a smaller toggle for the variables tab (~50% size)
        self.init_radio = ToggleSwitch(width=20, height=10)
        self.init_radio.setChecked(initialize)
        top_row.addWidget(self.init_radio, 0, Qt.AlignmentFlag.AlignVCenter)
        init_label = QLabel('Initialize?')
        init_label.setStyleSheet('color: #ccc; font-size: 13px;')
        top_row.addWidget(init_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # Second row: Type (QComboBox)
        from PyQt6.QtWidgets import QComboBox, QMessageBox
        type_row = QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        type_row.setSpacing(10)
        type_label = QLabel('Type:')
        type_label.setStyleSheet('color: #aaa; font-size: 13px; min-width: 60px;')
        type_row.addWidget(type_label, 0)
        self.type_combo = QComboBox()
        type_options = ['string', 'int', 'float', 'bool']
        self.type_combo.addItems(type_options)
        self.type_combo.setCurrentText(var_type)
        self.type_combo.setStyleSheet('color: #fff; font-size: 13px; background: #232323; border: 1px solid #444; border-radius: 4px;')
        # Calculate width: longest value + 30%
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(self.type_combo.font())
        max_text_width = max([metrics.horizontalAdvance(opt) for opt in type_options])
        width_with_padding = int((max_text_width + 24) * 1.3)
        self.type_combo.setFixedWidth(width_with_padding)
        # Keep left edge aligned by using stretch for the label, then fixed width for combo, then stretch
        type_row.addWidget(self.type_combo, 0)
        type_row.addStretch(1)
        # ...existing code...
        # Third row: Value
        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(10)
        value_label = QLabel('Value:')
        value_label.setStyleSheet('color: #aaa; font-size: 13px; min-width: 60px;')
        value_row.addWidget(value_label, 0)
        self.value_edit = QLineEdit(value)
        self.value_edit.setStyleSheet('color: #fff; font-size: 13px; background: #232323; border: 1px solid #444; border-radius: 4px; padding: 4px 8px;')
        value_row.addWidget(self.value_edit, 1)

        # Fourth row: Default
        default_row = QHBoxLayout()
        default_row.setContentsMargins(0, 0, 0, 0)
        default_row.setSpacing(10)
        default_label = QLabel('Default:')
        default_label.setStyleSheet('color: #aaa; font-size: 13px; min-width: 60px;')
        default_row.addWidget(default_label, 0)
        self.default_edit = QLineEdit(default)
        self.default_edit.setStyleSheet('color: #fff; font-size: 13px; background: #232323; border: 1px solid #444; border-radius: 4px; padding: 4px 8px;')
        default_row.addWidget(self.default_edit, 1)

        # Stack all rows vertically
        outer_vbox = QVBoxLayout(self)
        outer_vbox.setContentsMargins(0, 0, 0, 0)
        outer_vbox.setSpacing(6)
        outer_vbox.addLayout(top_row)
        outer_vbox.addLayout(type_row)
        outer_vbox.addLayout(value_row)
        outer_vbox.addLayout(default_row)
        self.setLayout(outer_vbox)

        # Always set value to default if Initialize? is selected (live)
        self.init_radio.toggled.connect(self._on_initialize_toggled)

        # Install event filters for value and default fields
        self.value_edit.installEventFilter(self)
        self.default_edit.installEventFilter(self)

        # Validate value/default fields when type changes
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        # On startup, validate value and default fields
        self._validate_fields_on_startup()

    def _validate_fields_on_startup(self):
        var_type = self.type_combo.currentText()
        value = self.value_edit.text()
        default = self.default_edit.text()
        valid_value = True
        valid_default = True
        if var_type == 'int':
            try:
                int(value)
            except Exception:
                self.value_edit.setText('0')
                valid_value = False
            try:
                int(default)
            except Exception:
                self.default_edit.setText('0')
                valid_default = False
        elif var_type == 'float':
            try:
                float(value)
            except Exception:
                self.value_edit.setText('0.0')
                valid_value = False
            try:
                float(default)
            except Exception:
                self.default_edit.setText('0.0')
                valid_default = False
        elif var_type == 'bool':
            if value.lower() not in ['true', 'false', '1', '0']:
                self.value_edit.setText('false')
                valid_value = False
            if default.lower() not in ['true', 'false', '1', '0']:
                self.default_edit.setText('false')
                valid_default = False
        # string: always valid
        # Optionally show a message if either was invalid
        if not valid_value or not valid_default:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, 'Type Error', f'One or both fields did not match type {var_type}. Reverted to default for type.')

    def _on_initialize_toggled(self, checked):
        if checked:
            self.value_edit.setText(self.default_edit.text())

    def get_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'value': self.value_edit.text(),
            'default': self.default_edit.text(),
            'type': self.type_combo.currentText(),
            'initialize': self.init_radio.isChecked()
        }

    def set_type(self, var_type):
        self.type_combo.setCurrentText(var_type)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        var_type = self.type_combo.currentText()
        if event.type() == QEvent.Type.FocusOut:
            if obj is self.value_edit:
                value = self.value_edit.text()
                valid = True
                if var_type == 'int':
                    try:
                        int(value)
                    except Exception:
                        self.value_edit.setText('0')
                        valid = False
                elif var_type == 'float':
                    try:
                        float(value)
                    except Exception:
                        self.value_edit.setText('0.0')
                        valid = False
                elif var_type == 'bool':
                    if value.lower() not in ['true', 'false', '1', '0']:
                        self.value_edit.setText('false')
                        valid = False
                elif var_type == 'string':
                    pass
                if not valid:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, 'Type Error', f'Value does not match type {var_type}. Reverted to default for type.')
            elif obj is self.default_edit:
                default = self.default_edit.text()
                valid = True
                if var_type == 'int':
                    try:
                        int(default)
                    except Exception:
                        self.default_edit.setText('0')
                        valid = False
                elif var_type == 'float':
                    try:
                        float(default)
                    except Exception:
                        self.default_edit.setText('0.0')
                        valid = False
                elif var_type == 'bool':
                    if default.lower() not in ['true', 'false', '1', '0']:
                        self.default_edit.setText('false')
                        valid = False
                elif var_type == 'string':
                    pass
                if not valid:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, 'Type Error', f'Default does not match type {var_type}. Reverted to default for type.')
        return super().eventFilter(obj, event)

    def _on_type_changed(self, new_type):
        # Validate value field
        value = self.value_edit.text()
        valid_value = True
        if new_type == 'int':
            try:
                int(value)
            except Exception:
                self.value_edit.setText('0')
                valid_value = False
        elif new_type == 'float':
            try:
                float(value)
            except Exception:
                self.value_edit.setText('0.0')
                valid_value = False
        elif new_type == 'bool':
            if value.lower() not in ['true', 'false', '1', '0']:
                self.value_edit.setText('false')
                valid_value = False
        elif new_type == 'string':
            pass
        # Validate default field
        default = self.default_edit.text()
        valid_default = True
        if new_type == 'int':
            try:
                int(default)
            except Exception:
                self.default_edit.setText('0')
                valid_default = False
        elif new_type == 'float':
            try:
                float(default)
            except Exception:
                self.default_edit.setText('0.0')
                valid_default = False
        elif new_type == 'bool':
            if default.lower() not in ['true', 'false', '1', '0']:
                self.default_edit.setText('false')
                valid_default = False
        elif new_type == 'string':
            pass
        # Show message if either was invalid
        if not valid_value or not valid_default:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, 'Type Error', f'One or both fields did not match type {new_type}. Reverted to default for type.')
