from __future__ import annotations

from typing import Callable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QSizePolicy, QVBoxLayout, QWidget

from src.frontend.animations import animate_collapsible
from src.frontend.widgets.section_card import SectionCard

# Clase que representa una tarjeta con un interruptor para activar o desactivar una sección de opciones, y que permite habilitar o deshabilitar los campos de entrada relacionados con esa sección
class PlanToggleCard(SectionCard):
    # El constructor recibe el título y el subtítulo de la tarjeta, el texto para el interruptor, una función de callback que se ejecutará cuando se active o desactive el interruptor, y opcionalmente un widget padre
    def __init__(
        self,
        title: str,
        subtitle: str,
        switch_text: str,
        on_toggle: Callable[[bool], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title=title, subtitle=subtitle, parent=parent)

        # Se guarda la función de callback para que se pueda llamar cuando se active o desactive el interruptor
        self._on_toggle = on_toggle
        self._field_widgets: List[object] = [] # Se crea una lista para almacenar los widgets de los campos de entrada relacionados con esta sección, para poder habilitarlos o deshabilitarlos según el estado del interruptor

        self.toggle = QCheckBox(switch_text) # Se crea un interruptor (checkbox) con el texto recibido
        self.toggle.toggled.connect(self._handle_toggle) # Se conecta la señal de cambio de estado del interruptor a un método que manejará el evento, y que llamará a la función de callback con el nuevo estado del interruptor

        self.fields_container = QWidget() # Se crea un contenedor para los campos de entrada relacionados, que se habilitarán o deshabilitarán según el estado del interruptor
        self.fields_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.fields_layout = QVBoxLayout(self.fields_container) # Se crea un layout vertical para organizar los campos de entrada dentro del contenedor
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(10)

        self._collapsed = False # Se inicializa el estado de colapsado como falso, lo que significa que la sección de campos de entrada estará visible inicialmente

        # Se agregan el interruptor y el contenedor de campos al cuerpo de la tarjeta
        self.body_layout.addWidget(self.toggle)
        self.body_layout.addWidget(self.fields_container)

        # Se establece el estado inicial del interruptor como desactivado, se colapsa la sección de campos de entrada, y se asegura de que los campos de entrada estén deshabilitados
        self.set_value(False, animate=False)

    # Método que maneja el evento de cambio de estado del interruptor (llama a la función de callback con el nuevo estado)
    def _handle_toggle(self, enabled: bool) -> None:
        self._on_toggle(enabled)

    # Método para agregar un widget de campo de entrada al contenedor
    def add_field_widget(self, widget: object) -> None:
        self._field_widgets.append(widget)

    # Método setter para establecer el estado del interruptor (activado o desactivado) sin emitir la señal de cambio de estado
    def set_value(self, value: bool, animate: bool = True) -> None:
        self.toggle.blockSignals(True)
        self.toggle.setChecked(value)
        self.toggle.blockSignals(False)
        self.set_collapsed(not value, animate=animate)

    # Método getter para obtener el estado actual del interruptor (activado o desactivado)
    def get_value(self) -> bool:
        return self.toggle.isChecked()

    # Método setter para colapsar o expandir la sección de campos de entrada dependiendo del estado del interruptor
    def set_collapsed(self, collapsed: bool, animate: bool = True) -> None:
        collapsed = bool(collapsed)

        if self._collapsed == collapsed:
            return

        self._collapsed = collapsed

        if animate:
            animate_collapsible(self.fields_container, collapsed)
        else:
            self.fields_container.setVisible(not collapsed)
            self.fields_container.setMaximumHeight(0 if collapsed else 16777215)

        self.fields_container.updateGeometry()
        self.body.updateGeometry()
        self.updateGeometry()
        self.adjustSize()

        parent = self.parentWidget()
        while parent is not None:
            parent.updateGeometry()

            if parent.layout() is not None:
                parent.layout().activate()

            parent = parent.parentWidget()

    # Método setter para habilitar o deshabilitar los campos de entrada relacionados
    def set_fields_enabled(self, enabled: bool) -> None:
        for widget in self._field_widgets:
            if hasattr(widget, "set_enabled"):
                widget.set_enabled(enabled)
            elif hasattr(widget, "setEnabled"):
                widget.setEnabled(enabled)