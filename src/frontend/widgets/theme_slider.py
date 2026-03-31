from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ThemeSlider(QWidget):
    def __init__(
        self,
        checked: bool = False,
        on_toggled: Optional[Callable[[bool], None]] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._checked = checked
        self._on_toggled = on_toggled

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(58, 30)

    def sizeHint(self) -> QSize:
        return QSize(58, 30)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool, emit: bool = False) -> None:
        checked = bool(checked)

        if self._checked == checked:
            return

        self._checked = checked
        self.update()

        if emit and self._on_toggled is not None:
            self._on_toggled(self._checked)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.set_checked(not self._checked, emit=True)
            event.accept()
            return

        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        track_rect = QRectF(1, 1, self.width() - 2, self.height() - 2)

        if self._checked:
            track_color = QColor("#2563EB")
            border_color = QColor("#1D4ED8")
        else:
            track_color = QColor("#CBD5E1")
            border_color = QColor("#94A3B8")

        thumb_diameter = self.height() - 8
        thumb_x = self.width() - thumb_diameter - 4 if self._checked else 4
        thumb_rect = QRectF(thumb_x, 4, thumb_diameter, thumb_diameter)

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, track_rect.height() / 2, track_rect.height() / 2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(thumb_rect)

        painter.end()