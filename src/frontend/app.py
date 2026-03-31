from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.frontend.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv) # Con esto se crea la aplicación Qt

    window = MainWindow() # Se crea la ventana principal de la aplicación
    window.show() # Se muestra la ventana principal

    return app.exec() # Se inicia el loop de eventos de la aplicación, y se devuelve el código de salida cuando se cierra la aplicación


if __name__ == "__main__":
    raise SystemExit(main())