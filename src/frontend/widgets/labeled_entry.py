from __future__ import annotations

from typing import Callable, Optional, Tuple

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

Validator = Callable[[str], Tuple[bool, str]]


# Clase que representa un campo de entrada con una etiqueta
class LabeledEntry(QWidget):
    # El constructor recibe el texto de la etiqueta, un texto de marcador de posición para el campo de entrada, y opciones para configurar el campo como de solo lectura o para contraseñas
    def __init__(
        self,
        label: str,
        placeholder: str = "",
        readonly: bool = False,
        password: bool = False,
        validator: Optional[Validator] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.label = QLabel(label)
        self.label.setProperty("muted", True)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText(placeholder)
        self.entry.setReadOnly(readonly)

        if password:
            self.entry.setEchoMode(QLineEdit.Password)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #D9534F; font-size: 11px; font-weight: 600;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)

        layout.addWidget(self.label)
        layout.addWidget(self.entry)
        layout.addWidget(self.error_label)

        self._validator: Optional[Validator] = None
        self._validation_enabled: bool = True
        if validator is not None:
            self.set_validator(validator)

    def set_validator(self, validator: Optional[Validator]) -> None:
        # Solo desconectar si el validator anterior existe (signal fue conectado)
        if self._validator is not None:
            try:
                self.entry.textChanged.disconnect(self._run_validation)
            except (RuntimeError, TypeError):
                pass
        self._validator = validator
        if validator is not None:
            self.entry.textChanged.connect(self._run_validation)
            self._run_validation(self.entry.text())
        else:
            self._set_error("")

    def set_validation_enabled(self, enabled: bool) -> None:
        self._validation_enabled = bool(enabled)
        if not self._validation_enabled:
            self._set_error("")
        else:
            self._run_validation(self.entry.text())

    def _run_validation(self, text: str) -> None:
        if not self._validation_enabled or self._validator is None:
            self._set_error("")
            return
        valid, msg = self._validator(text)
        self._set_error("" if valid else msg)

    def _set_error(self, msg: str) -> None:
        if msg:
            self.error_label.setText(msg)
            self.error_label.setVisible(True)
        else:
            self.error_label.clear()
            self.error_label.setVisible(False)

    def is_valid(self) -> bool:
        if not self._validation_enabled or self._validator is None:
            return True
        return self._validator(self.entry.text())[0]

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
