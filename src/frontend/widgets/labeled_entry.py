from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

# Clase que representa un campo de entrada con una etiqueta
class LabeledEntry(QWidget):
    # El constructor recibe el texto de la etiqueta, un texto de marcador de posición para el campo de entrada, y opciones para configurar el campo como de solo lectura o para contraseñas
    def __init__(
        self,
        label: str,
        placeholder: str = "",
        readonly: bool = False,
        password: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self) # Se crea un layout vertical para organizar la etiqueta y el campo de entrada
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.label = QLabel(label) # Se crea una etiqueta para el campo de entrada, y se le asigna la propiedad "muted" para que tenga un estilo más discreto
        self.label.setProperty("muted", True)

        self.entry = QLineEdit() # Se crea un campo de entrada de texto, y se configuran sus propiedades según los parámetros recibidos
        self.entry.setPlaceholderText(placeholder)
        self.entry.setReadOnly(readonly)

        if password: # Si el campo de entrada es para una contraseña, se configura para que oculte el texto ingresado
            self.entry.setEchoMode(QLineEdit.Password)

        # Se agregan la etiqueta y el campo de entrada al layout
        layout.addWidget(self.label)
        layout.addWidget(self.entry)

    # Método getter para obtener el texto ingresado en el campo de entrada
    def get(self) -> str:
        return self.entry.text()

    # Método setter para establecer el texto en el campo de entrada
    def set(self, value: str) -> None:
        self.entry.setReadOnly(False)
        self.entry.setText(value)

    # Método para limpiar el campo de entrada, y permitir que el usuario ingrese un nuevo valor
    def clear(self) -> None:
        self.entry.setReadOnly(False)
        self.entry.clear()

    # Método setter para habilitar o deshabilitar el campo de entrada, dependiendo del estado de la aplicación o de las acciones del usuario
    def set_enabled(self, enabled: bool) -> None:
        self.entry.setEnabled(enabled)

    # Método setter para establecer el campo de entrada como de solo lectura
    def set_readonly(self, readonly: bool) -> None:
        self.entry.setReadOnly(readonly)