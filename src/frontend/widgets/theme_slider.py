from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from src.frontend.animations import DURATION_FAST


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
        self._thumb_position = 1.0 if checked else 0.0

        self._thumb_animation = QPropertyAnimation(self, b"thumb_position", self)
        self._thumb_animation.setDuration(DURATION_FAST)
        self._thumb_animation.setEasingCurve(QEasingCurve.InOutCubic)

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(58, 30)

    def sizeHint(self) -> QSize:
        return QSize(58, 30)

    def is_checked(self) -> bool:
        return self._checked

    def _get_thumb_position(self) -> float:
        return self._thumb_position

    def _set_thumb_position(self, value: float) -> None:
        self._thumb_position = max(0.0, min(1.0, float(value)))
        self.update()

    thumb_position = Property(float, _get_thumb_position, _set_thumb_position)

    def set_checked(self, checked: bool, emit: bool = False, animate: bool = True) -> None:
        checked = bool(checked)

        if self._checked == checked:
            return

        self._checked = checked
        target = 1.0 if self._checked else 0.0

        if animate:
            self._thumb_animation.stop()
            self._thumb_animation.setStartValue(self._thumb_position)
            self._thumb_animation.setEndValue(target)
            self._thumb_animation.start()
        else:
            self._set_thumb_position(target)

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
        thumb_range = self.width() - thumb_diameter - 8
        thumb_x = 4 + (thumb_range * self._thumb_position)

        thumb_rect = QRectF(thumb_x, 4, thumb_diameter, thumb_diameter)

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(track_color)
        painter.drawRoundedRect(
            track_rect,
            track_rect.height() / 2,
            track_rect.height() / 2,
        )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(thumb_rect)

        painter.end()