from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QSizePolicy

from src.frontend.widgets.section_card import SectionCard

STATUS_COLORS = {
    "pending": "#64748B",
    "enabled": "#00968F",   # accent teal: plan habilitado pero sin correr aún
    "running": "#F59E0B",   # amarillo: aplicando
    "success": "#22C55E",   # verde: éxito
    "warning": "#F59E0B",
    "error": "#EF4444",     # rojo: error
    "skipped": "#94A3B8",
}

CONNECTOR_COLORS = {
    "default": "#334155",
    "running": "#F59E0B",   # amarillo: aplicando el plan del círculo siguiente
    "success": "#22C55E",   # verde: éxito en plan del círculo derecho
    "error": "#EF4444",     # rojo: error en plan del círculo derecho
}


class StepIndicator(QWidget):
    def __init__(self, label_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignHCenter)

        self.circle = QLabel()
        self.circle.setFixedSize(24, 24)
        self.circle.setStyleSheet("background: #64748B; border-radius: 12px;")

        self.label = QLabel(label_text)
        self.label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.circle, alignment=Qt.AlignHCenter)
        layout.addWidget(self.label)

    def set_status(self, status: str) -> None:
        color = STATUS_COLORS.get(status, "#64748B")
        self.circle.setStyleSheet(f"background: {color}; border-radius: 12px;")


class Connector(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(4)
        self.set_status("default")

    def set_status(self, status: str) -> None:
        color = CONNECTOR_COLORS.get(status, "#334155")
        self.setStyleSheet(f"background: {color}; border-radius: 2px;")


class StatusStepper(SectionCard):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Progreso",
            subtitle="Estado general de las etapas",
            parent=parent,
        )

        root_layout = self.layout()
        if root_layout is not None:
            root_layout.setSpacing(4)

        self.body_layout.setContentsMargins(0, 2, 0, 0)
        self.body_layout.setSpacing(12)

        self.steps: dict[str, StepIndicator] = {}
        self.connectors: list[Connector] = []

        self.info_widget = QWidget()
        self.info_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.info_layout = QGridLayout(self.info_widget)
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_layout.setHorizontalSpacing(16)
        self.info_layout.setVerticalSpacing(8)
        self.info_layout.setAlignment(Qt.AlignCenter)

        self.info_layout.setColumnStretch(0, 1)
        self.info_layout.setColumnStretch(1, 1)
        self.info_layout.setColumnStretch(2, 1)

        self.ip_title = QLabel("IP actual")
        self.ip_title.setProperty("muted", True)
        self.ip_title.setAlignment(Qt.AlignCenter)
        self.ip_value = QLabel("--")
        self.ip_value.setAlignment(Qt.AlignCenter)

        self.vendor_title = QLabel("Marca")
        self.vendor_title.setProperty("muted", True)
        self.vendor_title.setAlignment(Qt.AlignCenter)
        self.vendor_value = QLabel("--")
        self.vendor_value.setAlignment(Qt.AlignCenter)

        self.model_title = QLabel("Modelo")
        self.model_title.setProperty("muted", True)
        self.model_title.setAlignment(Qt.AlignCenter)
        self.model_value = QLabel("--")
        self.model_value.setAlignment(Qt.AlignCenter)

        self.info_layout.addWidget(self.ip_title, 0, 1)
        self.info_layout.addWidget(self.vendor_title, 0, 0)
        self.info_layout.addWidget(self.model_title, 0, 2)

        self.info_layout.addWidget(self.ip_value, 1, 1)
        self.info_layout.addWidget(self.vendor_value, 1, 0)
        self.info_layout.addWidget(self.model_value, 1, 2)

        self.body_layout.addWidget(self.info_widget, 1)

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        ordered_steps = [
            ("login", "Login"),
            ("wifi", "WiFi"),
            ("web_credentials", "Credenciales web"),
            ("ip", "IP"),
        ]

        for index, (step_key, step_label) in enumerate(ordered_steps):
            step_widget = StepIndicator(step_label)
            self.steps[step_key] = step_widget
            layout.addWidget(step_widget, 1)

            if index < len(ordered_steps) - 1:
                connector = Connector()
                self.connectors.append(connector)
                layout.addWidget(connector, 1)

        self.body_layout.addWidget(container, 1)

    def set_step_status(self, step_key: str, status: str) -> None:
        if step_key not in self.steps:
            return
        self.steps[step_key].set_status(status)

    def set_connector_status(self, index: int, status: str) -> None:
        if 0 <= index < len(self.connectors):
            self.connectors[index].set_status(status)

    def set_device_info(self, vendor: str = "--", current_ip: str = "--", model: str = "--") -> None:
        self.ip_value.setText(current_ip or "--")
        self.vendor_value.setText(vendor or "--")
        self.model_value.setText(model or "--")

    def reset(self) -> None:
        self.set_device_info("--", "--", "--")
        for step_key in self.steps:
            self.steps[step_key].set_status("pending")
        for connector in self.connectors:
            connector.set_status("default")
