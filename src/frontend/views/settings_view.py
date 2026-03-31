from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.frontend.state.app_state import AppState
from src.frontend.widgets.labeled_entry import LabeledEntry
from src.frontend.widgets.section_card import SectionCard
from src.frontend.widgets.view_header import ViewHeader


class SettingsView(QWidget):
    def __init__(
        self,
        app_state: AppState,
        on_theme_changed: Callable[[], None] | None = None,
        on_save_settings: Callable[[], None] | None = None,
        on_restore_defaults: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.on_theme_changed = on_theme_changed
        self.on_save_settings = on_save_settings
        self.on_restore_defaults = on_restore_defaults

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(0)

        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(12)

        self.header = ViewHeader(
            app_state=self.app_state,
            section_title="Configuración",
            section_subtitle="El usuario podrá estandarizar valores base de acceso.",
            on_theme_changed=self.on_theme_changed,
        )

        body = QWidget()
        body_layout = QGridLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setHorizontalSpacing(12)
        body_layout.setVerticalSpacing(12)
        body_layout.setColumnStretch(0, 1)
        body_layout.setColumnStretch(1, 1)

        self.access_card = SectionCard(
            title="Acceso base por marca",
            subtitle="Valores base para flujos de acceso y plan IP por marca.",
        )
        self.web_card = SectionCard(
            title="Estándar credenciales web",
            subtitle="Valores base para acceso web actual.",
        )

        self.access_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.web_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        body_layout.addWidget(self.access_card, 0, 0)
        body_layout.addWidget(self.web_card, 0, 1)

        self.brand_ip_huawei_fiber = LabeledEntry("IP base Huawei / FiberHome")
        self.brand_ip_zte = LabeledEntry("IP base ZTE")

        self.access_card.body_layout.addWidget(self.brand_ip_huawei_fiber)
        self.access_card.body_layout.addWidget(self.brand_ip_zte)
        self.access_card.body_layout.addStretch(1)

        self.web_actual_user = LabeledEntry("Username", readonly=True)
        # self.web_actual_user.set_readonly(True)
        self.web_actual_user_note = QLabel("Este valor esta bloqueado por firmware y no puede modificarse.")
        self.web_actual_user_note.setStyleSheet("color: #D9534F; font-size: 11px; font-weight: 600;")
        self.web_actual_user_note.setWordWrap(True)
        self.web_actual_password = LabeledEntry("Password actual")

        self.web_card.body_layout.addWidget(self.web_actual_user)
        self.web_card.body_layout.addWidget(self.web_actual_user_note)
        self.web_card.body_layout.addWidget(self.web_actual_password)
        self.web_card.body_layout.addStretch(1)

        self.actions_card = SectionCard(
            title="Acciones",
            subtitle="Persistencia de configuración base.",
        )

        actions_row = QWidget()
        actions_layout = QHBoxLayout(actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(12)

        self.restore_defaults_button = QPushButton("Regresar defaults")
        self.restore_defaults_button.clicked.connect(self._on_restore_defaults_clicked)

        self.save_button = QPushButton("Guardar")
        self.save_button.clicked.connect(self._on_save_clicked)

        actions_layout.addWidget(self.restore_defaults_button, 1)
        actions_layout.addWidget(self.save_button, 1)

        self.actions_card.body_layout.addWidget(actions_row)

        self.note = QLabel(
            "Estos valores quedan persistidos como base para la aplicación."
        )
        self.note.setProperty("muted", True)
        self.note.setWordWrap(True)

        center_layout.addStretch(1)
        center_layout.addWidget(self.header)
        center_layout.addWidget(body)
        center_layout.addWidget(self.actions_card)
        center_layout.addWidget(self.note)
        center_layout.addStretch(1)

        root.addWidget(center_container, 1)

        self.load_from_state()
        self._sync_card_heights()
        self.refresh_from_state()

    def _sync_card_heights(self) -> None:
        target_height = max(
            self.access_card.sizeHint().height(),
            self.web_card.sizeHint().height(),
        )
        self.access_card.setMinimumHeight(target_height)
        self.web_card.setMinimumHeight(target_height)

    def load_from_state(self) -> None:
        self.brand_ip_huawei_fiber.set(self.app_state.standard_settings.brand_ip_huawei_fiber)
        self.brand_ip_zte.set(self.app_state.standard_settings.brand_ip_zte)
        self.web_actual_user.set(self.app_state.standard_settings.web_actual_user)
        self.web_actual_password.set(self.app_state.standard_settings.web_actual_password)

    def sync_to_state(self) -> None:
        self.app_state.standard_settings.brand_ip_huawei_fiber = self.brand_ip_huawei_fiber.get()
        self.app_state.standard_settings.brand_ip_zte = self.brand_ip_zte.get()
        self.app_state.standard_settings.web_actual_user = self.web_actual_user.get()
        self.app_state.standard_settings.web_actual_password = self.web_actual_password.get()

    def _on_save_clicked(self) -> None:
        self.sync_to_state()
        if self.on_save_settings is not None:
            self.on_save_settings()
        self.refresh_from_state()

    def _on_restore_defaults_clicked(self) -> None:
        if self.on_restore_defaults is not None:
            self.on_restore_defaults()
        self.load_from_state()
        self.refresh_from_state()

    def refresh_from_state(self) -> None:
        self.load_from_state()
        self.header.refresh_from_state()
        self._sync_card_heights()