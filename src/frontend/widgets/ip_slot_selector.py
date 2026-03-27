from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget

# Clase que representa un selector de ranuras de ONT, que muestra una cuadrícula de botones para seleccionar un equipo en específico
class IPSlotSelector(QWidget):
    # El constructor recibe una función de callback que se ejecutará cuando se seleccione una ranura, el número de filas y columnas para la cuadrícula de botones, y opcionalmente un widget padre
    def __init__(
        self,
        on_selected: Callable[[Optional[int]], None],
        rows: int = 4,
        columns: int = 6,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._on_selected = on_selected # Se guarda la función de callback para que se pueda llamar cuando se seleccione una ranura
        self._selected_slot: Optional[int] = None # Se crea una variable para almacenar el número de ranura seleccionado
        self._buttons: dict[int, QPushButton] = {} # Se crea un diccionario para almacenar los botones de cada ranura, para poder actualizar su estado visual según la selección
        self._enabled = False

        self.layout = QGridLayout(self) # Se crea un layout de cuadrícula para organizar los botones de las ranuras
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

        slot_number = 1
        for row in range(rows):
            for column in range(columns):
                button = QPushButton(f"ONT {slot_number:02d}") # Se crea un botón para cada ranura, con un texto que indica el número de ranura
                button.setEnabled(False)
                button.setProperty("slotSelected", False)
                button.clicked.connect(lambda checked=False, value=slot_number: self.select_slot(value)) # Se conecta la señal de clic del botón a un método que seleccionará la ranura correspondiente, pasando el número de ranura como argumento
                self.layout.addWidget(button, row, column)
                self._buttons[slot_number] = button
                slot_number += 1

    # Método para seleccionar una ranura
    def select_slot(self, slot_number: int) -> None:
        if not self._enabled:
            return

        self._selected_slot = slot_number
        self._refresh_visual_state()
        self._on_selected(slot_number)

    # Método para deseleccionar la ranura actual (establecer la selección en None)
    def clear_selection(self) -> None:
        self._selected_slot = None
        self._refresh_visual_state()
        self._on_selected(None)

    # Método getter para obtener el número de ranura actual
    def get_selected_slot(self) -> Optional[int]:
        return self._selected_slot

    # Método setter para habilitar o deshabilitar el selector de ranuras
    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

        for button in self._buttons.values(): # Se habilitan o deshabilitan los botones según el estado del selector
            button.setEnabled(enabled)

        if not enabled:
            self._selected_slot = None

        self._refresh_visual_state() # Se actualiza el estado visual de los botones para reflejar la selección actual

    # Método para actualizar el estado visual de los botones según la ranura seleccionada
    def _refresh_visual_state(self) -> None:
        for slot_number, button in self._buttons.items():
            is_selected = slot_number == self._selected_slot
            button.setProperty("slotSelected", is_selected)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()