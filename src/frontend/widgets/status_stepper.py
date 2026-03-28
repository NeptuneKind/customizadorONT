from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QSizePolicy

from src.frontend.widgets.section_card import SectionCard

# Diccionario que asigna un color a cada estado posible de una etapa del proceso
STATUS_COLORS = {
    "pending": "#64748B",
    "running": "#38BDF8",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "skipped": "#94A3B8",
}

# Clase que representa un componente de interfaz para mostrar el progreso de varias etapas de un proceso, utilizando indicadores visuales para cada etapa y conectores entre ellos
class StepIndicator(QWidget):
    # El constructor recibe el texto de la etiqueta para la etapa, y opcionalmente un widget padre
    # Se crea un indicador circular para mostrar el estado de la etapa, y una etiqueta debajo del indicador para mostrar el texto de la etapa
    def __init__(self, label_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self) # Se crea un layout vertical para organizar el indicador y la etiqueta
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignHCenter)

        self.circle = QLabel() # Se crea un QLabel para representar el indicador circular, y se le asigna un estilo para que tenga forma de círculo y un color de fondo inicial
        self.circle.setFixedSize(24, 24)
        self.circle.setStyleSheet("background: #64748B; border-radius: 12px;")

        self.label = QLabel(label_text) # Se crea una etiqueta para mostrar el texto de la etapa
        self.label.setAlignment(Qt.AlignCenter)

        # Se agregan el indicador circular y la etiqueta al layout
        layout.addWidget(self.circle, alignment=Qt.AlignHCenter)
        layout.addWidget(self.label)

    # Método setter para actualizar el estado del indicador circular, cambiando su color de fondo
    def set_status(self, status: str) -> None:
        color = STATUS_COLORS.get(status, "#64748B")
        self.circle.setStyleSheet(f"background: {color}; border-radius: 12px;")

# Clase que representa un componente de interfaz para mostrar el progreso general de varias etapas de un proceso, utilizando varios indicadores de etapa y conectores entre ellos, y que hereda de SectionCard para tener un diseño consistente con otras secciones de la aplicación
class Connector(QFrame):
    # El constructor crea un conector visual entre los indicadores de etapa, que es una línea horizontal con un estilo específico
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(4)
        self.setStyleSheet("background: #334155; border-radius: 2px;")

# Clase que representa un componente de interfaz para mostrar el progreso general de varias etapas de un proceso, utilizando varios indicadores de etapa y conectores entre ellos
class StatusStepper(SectionCard):
    # El constructor recibe opcionalmente un widget padre, y crea varios indicadores de etapa para mostrar el progreso de cada etapa del proceso
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

        self.steps: dict[str, StepIndicator] = {} # Se crea un diccionario para almacenar los indicadores de etapa

        # Se crea un widget para mostrar información del equipo detectado por el customizador
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

        container = QWidget() # Se crea un contenedor para organizar los indicadores de etapa y los conectores entre ellos
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QHBoxLayout(container) # Metemos el contenedor en un layout horizontal
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        ordered_steps = [ # Se define una lista con el orden de las etapas del proceso, cada una con una clave y un texto para mostrar en la etiqueta
            ("login", "Login"),
            ("wifi", "WiFi"),
            ("web_credentials", "Credenciales web"),
            ("ip", "IP"),
        ]

        for index, (step_key, step_label) in enumerate(ordered_steps): # Por cada etapa en la lista, se crea un indicador de etapa y se agrega al layout, y si no es la última etapa, se agrega un conector después del indicador
            step_widget = StepIndicator(step_label)
            self.steps[step_key] = step_widget
            layout.addWidget(step_widget, 1)

            if index < len(ordered_steps) - 1:
                connector = Connector()
                layout.addWidget(connector, 1)

        self.body_layout.addWidget(container, 1)

    # Método setter para actualizar el estado de una etapa específica, cambiando el color del indicador correspondiente
    def set_step_status(self, step_key: str, status: str) -> None:
        if step_key not in self.steps:
            return
        self.steps[step_key].set_status(status)

    # Método setter para actualizar la información del equipo detectado por el customizador
    def set_device_info(self, vendor: str = "--", current_ip: str = "--", model: str = "--") -> None:
        self.ip_value.setText(current_ip or "--")
        self.vendor_value.setText(vendor or "--")
        self.model_value.setText(model or "--")
    
    # Método para reiniciar el estado de todas las etapas a "pending"
    def reset(self) -> None:
        self.set_device_info("--", "--", "--")
        for step_key in self.steps:
            self.steps[step_key].set_status("pending")