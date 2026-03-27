from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QMainWindow,
)

from src.frontend.state.app_state import AppState
from src.frontend.theme.colors import APP_STYLE
from src.frontend.views.main_view import MainView
from src.frontend.views.settings_view import SettingsView

# Clase principal de la aplicación, que representa la ventana principal. Contiene la barra lateral y el área de contenido principal, que se alterna entre la vista de ejecución y la vista de configuración.
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Customizador ONT")
        self.resize(1440, 900)
        self.setMinimumSize(1200, 760)

        self.app_state = AppState() # Se crea una instancia del estado de la aplicación, que se compartirá entre las diferentes vistas
        self.sidebar_expanded = True # Se establece el estado inicial de la barra lateral como expandida

        central = QWidget() # Se crea un widget central para la ventana principal, que contendrá la barra lateral y el área de contenido principal
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central) # Se crea un layout horizontal para organizar la barra lateral y el área de contenido principal
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = QWidget() # Se crea un widget para la barra lateral, que contendrá los botones de navegación y el título de la aplicación
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout(self.sidebar) # Se crea un layout vertical para organizar los elementos dentro de la barra lateral
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        self.sidebar_top = QWidget() # Se crea un widget para el área superior de la barra lateral
        self.sidebar_top_layout = QHBoxLayout(self.sidebar_top)
        self.sidebar_top_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_top_layout.setSpacing(8)

        self.brand_label = QLabel("Bienvenido")
        self.brand_label.setObjectName("sidebarTitle")

        self.collapse_button = QPushButton("<<")
        self.collapse_button.setFixedWidth(44)
        self.collapse_button.clicked.connect(self.toggle_sidebar)

        self.sidebar_top_layout.addWidget(self.brand_label, 1)
        self.sidebar_top_layout.addWidget(self.collapse_button, 0)

        self.subtitle_label = QLabel("Frontend base en PySide6")
        self.subtitle_label.setObjectName("sidebarSubtitle")
        self.subtitle_label.setWordWrap(True)

        self.execution_button = QPushButton("Ejecución") # Botón para mostrar la vista de ejecución, que es la vista principal de la aplicación
        self.execution_button.clicked.connect(lambda: self.show_view("execution"))

        self.settings_button = QPushButton("Configuración") # Botón para mostrar la vista de configuración, que permite al usuario modificar las opciones de la aplicación
        self.settings_button.clicked.connect(lambda: self.show_view("settings"))

        # Se agregan los elementos a la barra lateral
        sidebar_layout.addWidget(self.sidebar_top)
        sidebar_layout.addWidget(self.subtitle_label)
        sidebar_layout.addSpacing(10)
        sidebar_layout.addWidget(self.execution_button)
        sidebar_layout.addWidget(self.settings_button)
        sidebar_layout.addStretch(1)

        self.stack = QStackedWidget() # Se crea un widget para alternar entre las diferentes vistas
        self.main_view = MainView(app_state=self.app_state) # Se crea la vista de ejecución. Se le pasa el estado de la aplicación
        self.settings_view = SettingsView(app_state=self.app_state) # Se crea la vista de configuración. Se le pasa el estado de la aplicación

        # Se agregan las vistas al stack, para poder alternar entre ellas
        self.stack.addWidget(self.main_view)
        self.stack.addWidget(self.settings_view)

        # Se agregan la barra lateral y el área de contenido principal al layout raíz de la ventana principal
        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.stack, 1)

        # Se aplica el estilo a la ventana principal, y se muestra la vista de ejecución por defecto
        self.setStyleSheet(APP_STYLE)
        self.show_view("execution")

    # Método para mostrar una vista específica en el área de contenido principal, y actualizar el estado de los botones de navegación en la barra lateral
    def show_view(self, view_name: str) -> None:
        if view_name == "execution":
            self.settings_view.sync_to_state()
            self.stack.setCurrentWidget(self.main_view)
            self.execution_button.setProperty("active", True)
            self.settings_button.setProperty("active", False)
        else:
            self.stack.setCurrentWidget(self.settings_view)
            self.execution_button.setProperty("active", False)
            self.settings_button.setProperty("active", True)

        self._refresh_button_style(self.execution_button)
        self._refresh_button_style(self.settings_button)

    # Método para alternar entre la barra lateral expandida y colapsada
    def toggle_sidebar(self) -> None:
        self.sidebar_expanded = not self.sidebar_expanded

        if self.sidebar_expanded:
            self.sidebar.setFixedWidth(240)
            self.brand_label.setVisible(True)
            self.subtitle_label.setVisible(True)
            self.execution_button.setText("Ejecución")
            self.settings_button.setText("Configuración")
            self.collapse_button.setText("<<")
        else:
            self.sidebar.setFixedWidth(84)
            self.brand_label.setVisible(False)
            self.subtitle_label.setVisible(False)
            self.execution_button.setText("E")
            self.settings_button.setText("C")
            self.collapse_button.setText(">>")

    # Método para forzar la actualización del estilo de un botón, después de cambiar su propiedad "active"
    def _refresh_button_style(self, button: QPushButton) -> None:
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()