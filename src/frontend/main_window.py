from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QMainWindow,
)

from src.frontend.state.app_state import AppState, StandardSettingsState
from src.frontend.theme.colors import get_app_style
from src.frontend.views.main_view import MainView
from src.frontend.views.settings_view import SettingsView
from src.frontend.animations import (
    DURATION_FAST,
    DURATION_STANDARD,
    animate_opacity,
    animate_width,
)

# Clase principal de la aplicación, que representa la ventana principal. Contiene la barra lateral y el área de contenido principal, que se alterna entre la vista de ejecución y la vista de configuración.
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Customizador ONT")
        self.resize(1440, 900)
        self.setMinimumSize(1200, 760)

        self.app_state = AppState() # Se crea una instancia del estado de la aplicación, que se compartirá entre las diferentes vistas
        self.settings = QSettings("CustomizadorONT", "CustomizadorONT")
        self._load_persisted_theme() # Cargar el tema persistente
        self._load_persisted_standard_settings() # Cargar los valores de configuración estándar
        self.sidebar_expanded = True # Se establece el estado inicial de la barra lateral como expandida
        self._current_view_name: str | None = None # Se inicializa el nombre de la vista actual como None, para poder trackear cambios de vista y evitar recargar la misma vista innecesariamente

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

        # self.sidebar_logo = QLabel("LOGO")
        # self.sidebar_logo.setFixedSize(92, 92)
        # self.sidebar_logo.setAlignment(Qt.AlignCenter)
        # self.sidebar_logo.setStyleSheet(
        #     "background: #243041; border-radius: 46px; font-weight: 700;"
        # )
        self.sidebar_logo = QLabel()
        self.sidebar_logo.setFixedSize(92, 92)
        self.sidebar_logo.setAlignment(Qt.AlignCenter)
        self.sidebar_logo.setStyleSheet(
            "background: #243041; border-radius: 46px;"
        )

        logo_path = Path(__file__).resolve().parent / "assets" / "logo_RAM_ONT.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    72,
                    72,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.sidebar_logo.setPixmap(scaled)
        else:
            self.sidebar_logo.setText("LOGO")

        self.customization_button = QPushButton("Customización") # Botón para mostrar la vista de ejecución, que es la vista principal de la aplicación
        self.customization_button.clicked.connect(lambda: self.show_view("execution"))

        self.descustomization_button = QPushButton("Descustomización") # Botón para mostrar la vista de ejecución, que es la vista principal de la aplicación
        self.descustomization_button.clicked.connect(lambda: self.show_view("dexecution"))

        self.settings_button = QPushButton("Configuración") # Botón para mostrar la vista de configuración, que permite al usuario modificar las opciones de la aplicación
        self.settings_button.clicked.connect(lambda: self.show_view("settings"))

        # Se agregan los elementos a la barra lateral
        sidebar_layout.addWidget(self.sidebar_top)
        sidebar_layout.addWidget(self.sidebar_logo, 0, Qt.AlignHCenter)
        sidebar_layout.addSpacing(10)
        sidebar_layout.addWidget(self.customization_button)
        sidebar_layout.addWidget(self.descustomization_button)
        sidebar_layout.addWidget(self.settings_button)
        sidebar_layout.addStretch(1)

        self.stack = QStackedWidget() # Se crea un widget para alternar entre las diferentes vistas
        self.main_view = MainView( # Se crea la vista de ejecución. Se le pasa el estado de la aplicación
            app_state=self.app_state,
            on_theme_changed = self._apply_theme_from_state,
        )
        self.settings_view = SettingsView( # Se crea la vista de configuración. Se le pasa el estado de la aplicación
            app_state=self.app_state,
            on_theme_changed = self._apply_theme_from_state,
            on_save_settings=self._save_persisted_standard_settings,
            on_restore_defaults=self._restore_default_standard_settings,
        )

        # Se agregan las vistas al stack, para poder alternar entre ellas
        self.stack.addWidget(self.main_view)
        self.stack.addWidget(self.settings_view)

        # Se agregan la barra lateral y el área de contenido principal al layout raíz de la ventana principal
        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.stack, 1)

        # Se aplica el estilo a la ventana principal, y se muestra la vista de ejecución por defecto
        self._apply_theme_from_state()
        self.show_view("execution", animate=False)

    # Método para cargar el tema persistido en la configuración de la aplicación, y actualizar el estado de la aplicación con el tema cargado
    def _load_persisted_theme(self) -> None:
        stored_theme = str(self.settings.value("ui/theme_mode", "light"))
        self.app_state.set_theme_mode(stored_theme)

    # Método para cargar los valores de configuración estándar
    def _load_persisted_standard_settings(self) -> None:
        std = self.app_state.standard_settings

        std.brand_ip_huawei_fiber = str(
            self.settings.value("config/brand_ip_huawei_fiber", std.brand_ip_huawei_fiber)
        )
        std.brand_ip_zte = str(
            self.settings.value("config/brand_ip_zte", std.brand_ip_zte)
        )
        std.web_actual_user = str(
            self.settings.value("config/web_actual_user", std.web_actual_user)
        )
        std.web_actual_password = str(
            self.settings.value("config/web_actual_password", std.web_actual_password)
        )

    # Método para guardar los valores de configuración estándar en la configuración de la aplicación
    def _save_persisted_standard_settings(self) -> None:
        std = self.app_state.standard_settings

        self.settings.setValue("config/brand_ip_huawei_fiber", std.brand_ip_huawei_fiber)
        self.settings.setValue("config/brand_ip_zte", std.brand_ip_zte)
        self.settings.setValue("config/web_actual_user", std.web_actual_user)
        self.settings.setValue("config/web_actual_password", std.web_actual_password)

        self.main_view.refresh_from_state()
        self.settings_view.refresh_from_state()

    # Método para regresar los valores de configuración estándar a sus valores por defecto
    def _restore_default_standard_settings(self) -> None:
        self.app_state.standard_settings = StandardSettingsState()
        self._save_persisted_standard_settings()

    # Método para aplicar el tema actual desde el estado de la aplicación, actualizando la hoja de estilos y refrescando el estilo de los botones de navegación
    def _apply_theme_from_state(self) -> None:
        self.app_state.set_theme_mode(self.app_state.theme_mode)
        self.settings.setValue("ui/theme_mode", self.app_state.theme_mode)
        self.setStyleSheet(get_app_style(self.app_state.theme_mode))
        self._refresh_button_style(self.customization_button)
        self._refresh_button_style(self.descustomization_button)
        self._refresh_button_style(self.settings_button)

    # Método para mostrar una vista específica en el área de contenido principal
    def _apply_view_state(self, view_name: str) -> None:
        self._current_view_name = view_name

        if view_name == "execution":
            self.stack.setCurrentWidget(self.main_view)

            self.customization_button.setProperty("active", True)
            self.descustomization_button.setProperty("active", False)
            self.settings_button.setProperty("active", False)

            self.main_view.refresh_from_state()

        elif view_name == "dexecution":
            self.stack.setCurrentWidget(self.main_view)

            self.customization_button.setProperty("active", False)
            self.descustomization_button.setProperty("active", True)
            self.settings_button.setProperty("active", False)

            self.main_view.refresh_from_state()

        else:
            self.stack.setCurrentWidget(self.settings_view)

            self.customization_button.setProperty("active", False)
            self.descustomization_button.setProperty("active", False)
            self.settings_button.setProperty("active", True)

            self.settings_view.refresh_from_state()

        self._refresh_button_style(self.customization_button)
        self._refresh_button_style(self.descustomization_button)
        self._refresh_button_style(self.settings_button)

    # Método para mostrar una vista específica en el área de contenido principal, y actualizar el estado de los botones de navegación en la barra lateral
    def show_view(self, view_name: str, animate: bool = True) -> None:
        if view_name == self._current_view_name:
            return

        self._apply_view_state(view_name)

        current_widget = self.stack.currentWidget()
        if current_widget is None:
            return

        target = getattr(current_widget, "animation_target", current_widget)

        target.setGraphicsEffect(None)
        target.update()
        target.repaint()

        current_widget.update()
        current_widget.repaint()
        self.stack.update()
        self.stack.repaint()

        if animate:
            animate_opacity(
                target,
                start_value=0.0,
                end_value=1.0,
                duration=DURATION_STANDARD,
                key="view_opacity",
            )

    # Método para actualizar los textos de los botones de navegación en la barra lateral, dependiendo de si la barra lateral está expandida o colapsada
    def _apply_sidebar_texts(self, expanded: bool) -> None:
        if expanded:
            self.customization_button.setText("Customizacion")
            self.descustomization_button.setText("Descustomizacion")
            self.settings_button.setText("Configuracion")
            self.collapse_button.setText("<<")
        else:
            self.customization_button.setText("CC")
            self.descustomization_button.setText("DC")
            self.settings_button.setText("C")
            self.collapse_button.setText(">>")

    # Método para alternar entre la barra lateral expandida y colapsada
    def toggle_sidebar(self) -> None:
        self.sidebar_expanded = not self.sidebar_expanded

        current_width = self.sidebar.width()
        target_width = 240 if self.sidebar_expanded else 84

        if self.sidebar_expanded:
            self._apply_sidebar_texts(True)

            self.brand_label.setVisible(True)
            self.sidebar_logo.setVisible(True)

            animate_opacity(
                self.brand_label,
                start_value=0.0,
                end_value=1.0,
                duration=DURATION_FAST,
                key="sidebar_brand_opacity",
            )
            animate_opacity(
                self.sidebar_logo,
                start_value=0.0,
                end_value=1.0,
                duration=DURATION_FAST,
                key="sidebar_logo_opacity",
            )
        else:
            self._apply_sidebar_texts(False)

            brand_anim = animate_opacity(
                self.brand_label,
                start_value=1.0,
                end_value=0.0,
                duration=DURATION_FAST,
                key="sidebar_brand_opacity",
            )
            logo_anim = animate_opacity(
                self.sidebar_logo,
                start_value=1.0,
                end_value=0.0,
                duration=DURATION_FAST,
                key="sidebar_logo_opacity",
            )

            brand_anim.finished.connect(lambda: self.brand_label.setVisible(False))
            logo_anim.finished.connect(lambda: self.sidebar_logo.setVisible(False))

        animate_width(
            self.sidebar,
            start_width=current_width,
            end_width=target_width,
            duration=DURATION_STANDARD,
            key="sidebar_width",
        )

    # Método para forzar la actualización del estilo de un botón, después de cambiar su propiedad "active"
    def _refresh_button_style(self, button: QPushButton) -> None:
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
