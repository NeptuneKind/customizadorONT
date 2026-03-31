from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.frontend.state.app_state import AppState
from src.frontend.widgets.section_card import SectionCard
from src.frontend.widgets.theme_slider import ThemeSlider


class ViewHeader(QWidget):
    def __init__(
        self,
        app_state: AppState,
        section_title: str,
        section_subtitle: str,
        on_theme_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.on_theme_changed = on_theme_changed

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = SectionCard(
            title="",
            subtitle="",
        )
        card.title_label.setVisible(False)
        card.subtitle_label.setVisible(False)
        card.body_layout.setContentsMargins(0, 0, 0, 0)
        card.body_layout.setSpacing(0)

        container = QWidget()
        outer_layout = QVBoxLayout(container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(10)

        self.app_title_label = QLabel("Customizador ONT")
        self.app_title_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.app_title_label.setStyleSheet("font-size: 30px; font-weight: 800;")
        outer_layout.addWidget(self.app_title_label, 0, Qt.AlignTop)

        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)

        text_col = QWidget()
        text_layout = QVBoxLayout(text_col)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.system_label = QLabel(section_title)
        self.system_label.setStyleSheet("font-size: 24px; font-weight: 700;")

        self.help_label = QLabel(section_subtitle)
        self.help_label.setProperty("muted", True)
        self.help_label.setWordWrap(False)
        self.help_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        text_layout.addWidget(self.system_label, 0, Qt.AlignLeft | Qt.AlignBottom)
        text_layout.addWidget(self.help_label, 0, Qt.AlignLeft | Qt.AlignBottom)

        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)

        self.theme_title = QLabel("Tema")
        self.theme_title.setStyleSheet("font-size: 18px; font-weight: 500;")
        self.theme_title.setProperty("muted", True)
        self.theme_title.setAlignment(Qt.AlignRight)

        self.theme_row = QWidget()
        theme_row_layout = QHBoxLayout(self.theme_row)
        theme_row_layout.setContentsMargins(0, 0, 0, 0)
        theme_row_layout.setSpacing(8)

        self.theme_light_label = QLabel("Claro")
        self.theme_light_label.setProperty("muted", True)

        self.theme_slider = ThemeSlider(
            checked=self.app_state.theme_mode == "dark",
            on_toggled=self._on_theme_toggled,
        )

        self.theme_dark_label = QLabel("Oscuro")
        self.theme_dark_label.setProperty("muted", True)

        theme_row_layout.addWidget(self.theme_light_label)
        theme_row_layout.addWidget(self.theme_slider)
        theme_row_layout.addWidget(self.theme_dark_label)

        self.status_badge = QLabel()
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setMinimumSize(88, 42)

        right_layout.addWidget(self.theme_title, 0, Qt.AlignRight | Qt.AlignTop)
        right_layout.addWidget(self.theme_row, 0, Qt.AlignRight | Qt.AlignTop)
        right_layout.addWidget(self.status_badge, 0, Qt.AlignRight)

        bottom_layout.addWidget(text_col, 1, Qt.AlignLeft | Qt.AlignBottom)
        bottom_layout.addWidget(right_col, 0, Qt.AlignRight | Qt.AlignTop)

        outer_layout.addWidget(bottom_row, 1)

        card.body_layout.addWidget(container)
        root.addWidget(card)

        self.refresh_from_state()

    def _on_theme_toggled(self, checked: bool) -> None:
        self.app_state.set_theme_mode("dark" if checked else "light")

        if self.on_theme_changed is not None:
            self.on_theme_changed()

    def refresh_from_state(self) -> None:
        self.theme_slider.set_checked(self.app_state.theme_mode == "dark")
        self.status_badge.setText(self.app_state.global_status_text)
        self.status_badge.setProperty("badge", self.app_state.global_status_kind)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.status_badge.update()