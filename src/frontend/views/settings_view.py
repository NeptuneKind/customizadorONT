from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from src.frontend.state.app_state import AppState
from src.frontend.widgets.labeled_entry import LabeledEntry
from src.frontend.widgets.section_card import SectionCard

# Clase que representa la vista de configuración, que permite al usuario modificar las opciones de la aplicación
class SettingsView(QWidget):
    # El constructor recibe el estado de la aplicación, que se utilizará para cargar y guardar las opciones de configuración, y opcionalmente un widget padre
    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state # Se guarda el estado de la aplicación para poder acceder a él en otros métodos de la clase

        root = QVBoxLayout(self) # Layout vertical
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        self.header = SectionCard( # Se crea una tarjeta de sección para el encabezado de la vista, con un título y un subtítulo que describen la función de esta vista
            title="Configuracion",
            subtitle="Vista reservada para la estandarizacion futura de valores.",
        )
        root.addWidget(self.header)

        body = QWidget() # Se crea un widget para el cuerpo de la vista, que contendrá las opciones de configuración organizadas en tarjetas de sección
        body_layout = QGridLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setHorizontalSpacing(12)
        body_layout.setVerticalSpacing(12)

        self.wifi_card = SectionCard( # Se crea una tarjeta de sección para el área de configuración de WiFi
            title="Estandar WiFi",
            subtitle="Campos contemplados para SSID y passwords.",
        )
        self.web_card = SectionCard( # Se crea una tarjeta de sección para el área de configuración de credenciales web
            title="Estandar credenciales web",
            subtitle="Campos contemplados para la configuracion futura.",
        )

        body_layout.addWidget(self.wifi_card, 0, 0)
        body_layout.addWidget(self.web_card, 0, 1)

        self.wifi_ssid_24 = LabeledEntry("SSID 2.4 GHz") # SSID 2.4 GHz
        self.wifi_password_24 = LabeledEntry("Password 2.4 GHz", password=True) # Password 2.4 GHz
        self.wifi_ssid_5 = LabeledEntry("SSID 5 GHz") # SSID 5 GHz
        self.wifi_password_5 = LabeledEntry("Password 5 GHz", password=True) # Password 5 GHz

        self.wifi_card.body_layout.addWidget(self.wifi_ssid_24)
        self.wifi_card.body_layout.addWidget(self.wifi_password_24)
        self.wifi_card.body_layout.addWidget(self.wifi_ssid_5)
        self.wifi_card.body_layout.addWidget(self.wifi_password_5)

        self.web_old_password = LabeledEntry("Password actual", password=True) # Password actual
        self.web_new_password = LabeledEntry("Password nueva", password=True) # Password nueva

        self.web_card.body_layout.addWidget(self.web_old_password)
        self.web_card.body_layout.addWidget(self.web_new_password)

        self.note = QLabel( # Nota informativa para el usuario
            "Estos valores solo quedan contemplados en memoria para la siguiente fase. "
            "La persistencia y logica de aplicacion se conectaran despues."
        )
        self.note.setProperty("muted", True) # Muted para estilo más discreto
        self.note.setWordWrap(True) # Permitir que el texto se divida en varias líneas si es necesario

        root.addWidget(body, 1)
        root.addWidget(self.note)

        self.load_from_state() # Cargar los valores de configuración

    # Método para cargar los valores de configuración
    def load_from_state(self) -> None:
        self.wifi_ssid_24.set(self.app_state.standard_settings.wifi_ssid_24)
        self.wifi_password_24.set(self.app_state.standard_settings.wifi_password_24)
        self.wifi_ssid_5.set(self.app_state.standard_settings.wifi_ssid_5)
        self.wifi_password_5.set(self.app_state.standard_settings.wifi_password_5)
        self.web_old_password.set(self.app_state.standard_settings.web_old_password)
        self.web_new_password.set(self.app_state.standard_settings.web_new_password)

    # Método para sincronizar los valores de configuración ingresados por el usuario
    def sync_to_state(self) -> None:
        self.app_state.standard_settings.wifi_ssid_24 = self.wifi_ssid_24.get()
        self.app_state.standard_settings.wifi_password_24 = self.wifi_password_24.get()
        self.app_state.standard_settings.wifi_ssid_5 = self.wifi_ssid_5.get()
        self.app_state.standard_settings.wifi_password_5 = self.wifi_password_5.get()
        self.app_state.standard_settings.web_old_password = self.web_old_password.get()
        self.app_state.standard_settings.web_new_password = self.web_new_password.get()