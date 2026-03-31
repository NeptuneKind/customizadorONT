from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

# Clase que representa una tarjeta de sección, que se utiliza para organizar el contenido dentro de las vistas
class SectionCard(QFrame):
    # El constructor recibe el título y el subtítulo de la tarjeta, y opcionalmente un widget padre
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("card", True)

        root = QVBoxLayout(self) # Se crea un layout vertical para organizar los elementos dentro de la tarjeta
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setProperty("cardTitle", True)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setProperty("cardSubtitle", True)

        self.body = QWidget() # Se crea un widget para el cuerpo de la tarjeta, que contendrá el contenido específico de cada sección
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 8, 0, 0)
        self.body_layout.setSpacing(10)

    # Se agregan los elementos a la tarjeta
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)
        root.addWidget(self.body)