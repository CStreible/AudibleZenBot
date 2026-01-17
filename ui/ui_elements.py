"""Common UI elements for the AudibleZenBot application.

Place shared widgets here (ToggleSwitch, future shared controls).
"""
from PyQt6.QtWidgets import QCheckBox
"""Common UI elements for the AudibleZenBot application.

Place shared widgets here (ToggleSwitch, future shared controls).
"""
from PyQt6.QtWidgets import QCheckBox, QLayout, QWidgetItem
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, pyqtProperty, QSize, QPoint
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen


class ToggleSwitch(QCheckBox):
    """A small animated toggle switch.

    Public API:
    - Use `setChecked(bool)` to change state (animation will run).
    - `offset` property is exposed as a `pyqtProperty(float)` for the animation.
    - Do not access internal attributes (prefixed with `_`) from outside.
    """

    def mousePressEvent(self, event):
        # Accept the press so we get the release event; do not toggle here
        # to avoid double-toggle when the base class also changes state.
        if self.isEnabled():
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        # Toggle on release to make clicking anywhere on the widget reliable
        # and avoid invoking the base class mouse handling which can cause
        # duplicate state changes depending on click position.
        if self.isEnabled():
            try:
                self.toggle()
            except Exception:
                try:
                    self.setChecked(not self.isChecked())
                except Exception:
                    pass
        # Do not call super() to prevent the QCheckBox default handler from
        # toggling a second time.

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


class FlowLayout(QLayout):
    """Flow layout that arranges child widgets horizontally and wraps them.

    Adapted for reuse in the project's UI. Keeps visual behavior minimal and
    acts like a wrapping HBoxLayout.
    """

    def __init__(self, parent=None, margin=0, spacing=5):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self.item_list = []

    def addItem(self, item):
        self.item_list.append(item)

    def addWidget(self, w):
        self.addItem(QWidgetItem(w))

    def count(self):
        return len(self.item_list)

    def itemAt(self, idx):
        if 0 <= idx < len(self.item_list):
            return self.item_list[idx]
        return None

    def takeAt(self, idx):
        if 0 <= idx < len(self.item_list):
            return self.item_list.pop(idx)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.sizeHint())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        effectiveRect = rect.adjusted(self.contentsMargins().left(), self.contentsMargins().top(), -self.contentsMargins().right(), -self.contentsMargins().bottom())
        x = effectiveRect.x()
        y = effectiveRect.y()

        for item in self.item_list:
            widgetSize = item.sizeHint()
            spaceX = self._spacing
            spaceY = self._spacing
            nextX = x + widgetSize.width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + widgetSize.width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), widgetSize))

            x = nextX
            lineHeight = max(lineHeight, widgetSize.height())

        return y + lineHeight - rect.y() + self.contentsMargins().bottom()
