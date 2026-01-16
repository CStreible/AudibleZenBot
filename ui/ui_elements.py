"""Common UI elements for the AudibleZenBot application.

Place shared widgets here (ToggleSwitch, future shared controls).
"""
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen


class ToggleSwitch(QCheckBox):
    """A small animated toggle switch.

    Public API:
    - Use `setChecked(bool)` to change state (animation will run).
    - `offset` property is exposed as a `pyqtProperty(float)` for the animation.
    - Do not access internal attributes (prefixed with `_`) from outside.
    """

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
        # Initialize internal offset and animation
        self._offset = float(2.0)
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self._offset = self._get_offset_for_state(self.isChecked())
        self.stateChanged.connect(self._on_state_changed)

    def _get_offset_for_state(self, checked):
        try:
            return float(self._width - self._height + 2) if checked else float(2)
        except Exception:
            return 2.0

    def _on_state_changed(self, state):
        end = self._get_offset_for_state(self.isChecked())
        start = float(self._offset) if self._offset is not None else 2.0
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
        try:
            return float(self._offset)
        except Exception:
            return 2.0

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = pyqtProperty(float, fget=get_offset, fset=set_offset)
