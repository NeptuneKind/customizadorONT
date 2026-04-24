from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.frontend.animations import animate_collapsible, DURATION_STANDARD
from src.frontend.state.app_state import AppState
from src.frontend.validators import (
    validate_alphanumeric,
    validate_huawei_password,
    validate_ipv4,
    validate_wifi_password_zte,
)
from src.frontend.widgets.theme_slider import ThemeSlider
from src.frontend.widgets.view_header import ViewHeader
from src.frontend.widgets.ip_slot_selector import IPSlotSelector
from src.frontend.widgets.labeled_entry import LabeledEntry
from src.frontend.widgets.plan_toggle_card import PlanToggleCard
from src.frontend.widgets.section_card import SectionCard
from src.frontend.widgets.status_stepper import StatusStepper

# Clase que representa la vista principal de la aplicación. Muestra el formulario de ejecución y el estado actual del proceso
class MainView(QWidget):
    # El constructor recibe el estado de la aplicación, que se utilizará para cargar y guardar los valores del formulario y el estado del proceso, y opcionalmente un widget padre
    def __init__(
        self,
        app_state: AppState,
        on_theme_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.on_theme_changed = on_theme_changed

        root = QVBoxLayout(self) # Layout vertical
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        #self.header = self._build_header() # Encabezado de la vista, con el título, el logo y el estado general del proceso 
        self.header = ViewHeader(
            app_state=self.app_state,
            section_title="Ejecución de planes",
            section_subtitle="El sistema mostrará aquí el flujo general de customización.",
            on_theme_changed=self.on_theme_changed,
        )
        root.addWidget(self.header)

        content = QWidget() # Contenedor para el contenido
        self.animation_target = content
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self.left_scroll = self._build_left_panel() # Panel izquierdo con el formulario de ejecución
        self.right_panel = self._build_right_panel() # Panel derecho con el stepper de estado, las reglas activas y el log visual

        content_layout.addWidget(self.left_scroll, 3)
        content_layout.addWidget(self.right_panel, 2)

        root.addWidget(content, 1)
        self.refresh_from_state() # Cargar los valores iniciales

    # Método para construir el panel izquierdo de la vista
    def _build_left_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setObjectName("leftPlansScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
                border: none;
            }
            """
        )

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(12)

        self.wifi_card = PlanToggleCard(
            title="Plan WiFi",
            subtitle="Compatible con credenciales web. Incompatible con IP.",
            switch_text="Habilitar customización de WiFi",
            on_toggle=self._on_wifi_toggle,
        )
        self._build_wifi_fields()

        self.web_card = PlanToggleCard(
            title="Plan credenciales web",
            subtitle="Compatible con WiFi. Incompatible con IP.",
            switch_text="Habilitar customización de credenciales web",
            on_toggle=self._on_web_toggle,
        )
        self._build_web_fields()

        self.ip_card = PlanToggleCard(
            title="Plan IP",
            subtitle="Plan exclusivo. Selección única de equipo.",
            switch_text="Habilitar customización de IP",
            on_toggle=self._on_ip_toggle,
        )
        self._build_ip_fields()

        self.actions_card = SectionCard(
            title="Acciones",
            subtitle="Controles listos para enlazar con backend",
        )

        actions_row = QWidget()
        actions_layout = QHBoxLayout(actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(12)

        self.clear_button = QPushButton("Limpiar")
        self.clear_button.clicked.connect(self._on_clear_clicked)

        actions_layout.addStretch(1)
        actions_layout.addWidget(self.clear_button)

        self.actions_card.body_layout.addWidget(actions_row)

        layout.addWidget(self.wifi_card)
        layout.addWidget(self.web_card)
        layout.addWidget(self.ip_card)
        layout.addWidget(self.actions_card)

        layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

    # Método para construir el panel derecho de la vista
    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # CAMBIO NO OPCIONAL: EL STEPPER SE CREA AQUI
        self.stepper = StatusStepper()

        # Card para mostrar el log visual de mensajes del sistema
        self.log_card = SectionCard(
            title="Logs del sistema",
            subtitle="Mensajes de backend y eventos de ejecución",
        )

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_card.body_layout.addWidget(self.log_box)

        # CAMBIO NO OPCIONAL: EL PANEL DERECHO SOLO CONTIENE STEPPER Y LOGS
        layout.addWidget(self.stepper, 1)
        layout.addWidget(self.log_card, 1)

        return panel

    # Método para construir los campos específicos del plan WiFi dentro de su tarjeta de sección, y agregarlos al layout correspondiente
    def _build_wifi_fields(self) -> None:
        note = QLabel(
            "Valores contemplados desde configuración."
        )
        note.setProperty("muted", True)
        note.setWordWrap(True)

        username_for_wifi = lambda: self.app_state.standard_settings.web_actual_user
        wifi_pwd_validator = lambda v: validate_wifi_password_zte(v, username_for_wifi())

        self.wifi_ssid_24 = LabeledEntry("SSID 2.4 GHz", validator=validate_alphanumeric)
        self.wifi_password_24 = LabeledEntry("Password 2.4 GHz", validator=wifi_pwd_validator)
        self.wifi_ssid_5 = LabeledEntry("SSID 5 GHz", validator=validate_alphanumeric)
        self.wifi_password_5 = LabeledEntry("Password 5 GHz", validator=wifi_pwd_validator)

        self.wifi_card.fields_layout.addWidget(note)
        self.wifi_card.fields_layout.addWidget(self.wifi_ssid_24)
        self.wifi_card.fields_layout.addWidget(self.wifi_password_24)
        self.wifi_card.fields_layout.addWidget(self.wifi_ssid_5)
        self.wifi_card.fields_layout.addWidget(self.wifi_password_5)

        self.wifi_card.add_field_widget(self.wifi_ssid_24)
        self.wifi_card.add_field_widget(self.wifi_password_24)
        self.wifi_card.add_field_widget(self.wifi_ssid_5)
        self.wifi_card.add_field_widget(self.wifi_password_5)

    # Método para construir los campos específicos del plan de credenciales web dentro de su tarjeta de sección, y agregarlos al layout correspondiente
    def _build_web_fields(self) -> None:
        note = QLabel("Credenciales contempladas desde la vista de configuración.")
        note.setProperty("muted", True)
        note.setWordWrap(True)

        web_pwd_validator = lambda v: validate_huawei_password(
            v, self.app_state.standard_settings.web_actual_user
        )

        self.web_old_password = LabeledEntry("Password actual")
        self.web_new_password = LabeledEntry("Password nueva", validator=web_pwd_validator)

        self.web_card.fields_layout.addWidget(note)
        self.web_card.fields_layout.addWidget(self.web_old_password)
        self.web_card.fields_layout.addWidget(self.web_new_password)

        self.web_card.add_field_widget(self.web_old_password)
        self.web_card.add_field_widget(self.web_new_password)

    # Método para construir los campos específicos del plan IP dentro de su tarjeta de sección, y agregarlos al layout correspondiente
    def _build_ip_fields(self) -> None:
        self.ip_custom_check = QCheckBox("IP custom")
        self.ip_custom_check.setObjectName("subCheck")
        self.ip_custom_check.toggled.connect(self._on_ip_custom_toggled)

        # Contenedor colapsable: nota + selector de ONTs (visible cuando ip_custom=False)
        self.ip_matrix_container = QWidget()
        matrix_layout = QVBoxLayout(self.ip_matrix_container)
        matrix_layout.setContentsMargins(0, 0, 0, 0)
        matrix_layout.setSpacing(8)

        note = QLabel(
            "Selecciona solo un equipo. La IP a aplicar se calculará automáticamente."
        )
        note.setProperty("muted", True)
        note.setWordWrap(True)

        self.ip_selector = IPSlotSelector(
            on_selected=self._on_ip_slot_selected,
            rows=4,
            columns=6,
        )

        matrix_layout.addWidget(note)
        matrix_layout.addWidget(self.ip_selector)

        self.calculated_ip_entry = LabeledEntry(
            "IP a aplicar", readonly=True, validator=validate_ipv4
        )
        self.calculated_ip_entry.set_validation_enabled(False)
        self.calculated_ip_entry.entry.textChanged.connect(self._on_custom_ip_text_changed)

        self.ip_card.fields_layout.addWidget(self.ip_custom_check)
        self.ip_card.fields_layout.addWidget(self.ip_matrix_container)
        self.ip_card.fields_layout.addWidget(self.calculated_ip_entry)

        self.ip_card.add_field_widget(self.ip_selector)
        self.ip_card.add_field_widget(self.calculated_ip_entry)

    # Handler para el toggle del plan WiFi, que actualiza el estado de la aplicación, aplica las reglas de exclusividad entre planes, y agrega un mensaje al log visual
    def _on_wifi_toggle(self, enabled: bool) -> None:
        self.app_state.execution.wifi.enabled = enabled
        if enabled:
            self.app_state.execution.ip_plan.enabled = False
            self._clear_ip_selection_log()

        self._apply_plan_rules()
        self.app_state.rebuild_plan_logs()
        self.refresh_from_state()

    # Handler para el toggle del plan de credenciales web, que actualiza el estado de la aplicación, aplica las reglas de exclusividad entre planes, y agrega un mensaje al log visual
    def _on_web_toggle(self, enabled: bool) -> None:
        self.app_state.execution.web_credentials.enabled = enabled
        if enabled:
            self.app_state.execution.ip_plan.enabled = False
            self._clear_ip_selection_log()

        self._apply_plan_rules()
        self.app_state.rebuild_plan_logs()
        self.refresh_from_state()

    # Handler para el toggle del plan IP, que actualiza el estado de la aplicación, aplica las reglas de exclusividad entre planes, y agrega un mensaje al log visual
    def _on_ip_toggle(self, enabled: bool) -> None:
        self.app_state.execution.ip_plan.enabled = enabled
        if enabled:
            self.app_state.execution.wifi.enabled = False
            self.app_state.execution.web_credentials.enabled = False
        else:
            self._clear_ip_selection_log()
            self.app_state.execution.ip_custom = False

        self._apply_plan_rules()
        self.app_state.rebuild_plan_logs()
        self.refresh_from_state()

    # Handler para el checkbox "IP custom": oculta/muestra la matriz de ONTs y cambia el modo del campo IP
    def _on_ip_custom_toggled(self, custom: bool) -> None:
        self.app_state.execution.ip_custom = custom

        if custom:
            # Limpiar selección de slot y habilitar el campo IP para escritura libre
            self.app_state.execution.selected_slot = None
            self.app_state.execution.calculated_ip = ""
            self.ip_selector.clear_selection()
            self.calculated_ip_entry.set("")
            self.calculated_ip_entry.set_readonly(False)
            self.calculated_ip_entry.set_validation_enabled(True)
            self._clear_ip_selection_log()
            self._set_ip_custom_mode_log()
            self._set_custom_ip_log("")
        else:
            # Volver a modo matriz: campo IP readonly hasta que se seleccione un slot
            self.app_state.execution.calculated_ip = ""
            self.calculated_ip_entry.set("")
            self.calculated_ip_entry.set_readonly(True)
            self.calculated_ip_entry.set_validation_enabled(False)
            self._clear_ip_custom_logs()

        animate_collapsible(self.ip_matrix_container, collapsed=custom, duration=DURATION_STANDARD)

    # Handler para el cambio de texto en el campo IP custom: actualiza el log dinámicamente
    def _on_custom_ip_text_changed(self, text: str) -> None:
        if self.app_state.execution.ip_custom:
            self.app_state.execution.calculated_ip = text
            self._set_custom_ip_log(text)
            self._render_logs()

    # Handler para la selección de una ranura de ONT en el plan IP, que actualiza el estado de la aplicación con la ranura seleccionada, calcula un valor de IP placeholder basado en la ranura seleccionada, actualiza el campo de IP calculada con ese valor, y agrega un mensaje al log visual
    def _on_ip_slot_selected(self, slot_number: int | None) -> None:
        self.app_state.execution.selected_slot = slot_number

        if slot_number is None:
            self.app_state.execution.calculated_ip = ""
            self.calculated_ip_entry.set("")
            self.calculated_ip_entry.set_readonly(True)
            self._clear_ip_selection_log()
            return
        
        placeholder_ip = f"192.168.50.{int(slot_number)}" # Si el ID es 01, 02, ..., 09 lo convertimos a 1, 2, ..., 9 para calcular la IP placeholder

        self.app_state.execution.calculated_ip = placeholder_ip
        self.calculated_ip_entry.set(placeholder_ip)
        self.calculated_ip_entry.set_readonly(True)
        self._set_ip_selection_log(slot_number)

    # Método para aplicar las reglas de exclusividad entre planes, sincronizando el estado de la aplicación y refrescando la vista para reflejar los cambios
    def _apply_plan_rules(self) -> None:
        self.app_state.sync_plan_rules()

    # Método para refrescar la vista con los valores actuales del estado de la aplicación
    def refresh_from_state(self) -> None:
        execution = self.app_state.execution
        self.web_old_password.set(self.app_state.standard_settings.web_actual_password) # Cargamos el password actual del estado de configuración estándar
        self.header.refresh_from_state()

        if hasattr(self, "theme_slider"):
            self.theme_slider.set_checked(self.app_state.theme_mode == "dark")

        self.wifi_card.set_value(execution.wifi.enabled)
        self.web_card.set_value(execution.web_credentials.enabled)
        self.ip_card.set_value(execution.ip_plan.enabled)

        self.wifi_card.set_fields_enabled(execution.wifi.fields_enabled)
        self.web_card.set_fields_enabled(execution.web_credentials.fields_enabled)
        self.ip_card.set_fields_enabled(execution.ip_plan.fields_enabled)
        self.ip_selector.set_enabled(execution.ip_plan.fields_enabled and not execution.ip_custom)

        # Sync ip_custom checkbox sin disparar señales
        self.ip_custom_check.blockSignals(True)
        self.ip_custom_check.setChecked(execution.ip_custom)
        self.ip_custom_check.blockSignals(False)
        self.ip_custom_check.setEnabled(execution.ip_plan.fields_enabled)

        # Matrix container visible solo cuando ip_custom=False
        ip_custom = execution.ip_custom
        self.ip_matrix_container.setVisible(not ip_custom)
        if not ip_custom:
            self.ip_matrix_container.setMaximumHeight(16777215)

        self.calculated_ip_entry.set(execution.calculated_ip)
        self.calculated_ip_entry.set_readonly(not execution.ip_custom)

        self.stepper.set_device_info(
            vendor=execution.vendor,
            current_ip=execution.current_ip,
            model=execution.model_code,
        )

        for step_key, status in execution.progress.items():
            self.stepper.set_step_status(step_key, status)

        self._render_logs()

    # Método setter para establecer la ruta del logo en el encabezado, cargando la imagen desde el archivo y actualizando el widget
    def set_logo_path(self, logo_path: str | Path) -> None:
        # logo_path = Path(logo_path)
        # if not logo_path.exists():
        #     self._append_log(f"[UI] Logo no encontrado: {logo_path}")
        #     return

        # pixmap = QPixmap(str(logo_path))
        # if pixmap.isNull():
        #     self._append_log(f"[UI] No se pudo cargar el logo: {logo_path}")
        #     return

        # scaled = pixmap.scaled(
        #     64,
        #     64,
        #     Qt.KeepAspectRatioByExpanding,
        #     Qt.SmoothTransformation,
        # )
        # self.logo_container.setPixmap(scaled)
        # self.logo_container.setText("")
        return

    # Handler para el botón de inicio. TODO: En el futuro se conectará con la lógica de backend para iniciar el proceso de customización
    def _on_start_clicked(self) -> None:
        self.app_state.clear_process_logs()
        self._append_log("[UI] Inicio de customizacion solicitado")

    # Handler para el botón de limpiar, que restablece el estado de la aplicación a los valores iniciales
    def _on_clear_clicked(self) -> None:
        self.app_state.execution.current_ip = "--"
        self.app_state.execution.model_code = "--"
        self.app_state.execution.vendor = "--"
        self.app_state.execution.wifi.enabled = False
        self.app_state.execution.web_credentials.enabled = False
        self.app_state.execution.ip_plan.enabled = False
        self.app_state.execution.selected_slot = None
        self.app_state.execution.calculated_ip = ""
        self.app_state.execution.ip_custom = False

        self.app_state.sync_plan_rules()
        self.app_state.clear_all_logs()
        self.app_state.rebuild_plan_logs()

        self.wifi_ssid_24.clear()
        self.wifi_password_24.clear()
        self.wifi_ssid_5.clear()
        self.wifi_password_5.clear()
        self.web_old_password.clear()
        self.web_new_password.clear()
        self.ip_selector.clear_selection()
        self.ip_custom_check.blockSignals(True)
        self.ip_custom_check.setChecked(False)
        self.ip_custom_check.blockSignals(False)
        self.ip_matrix_container.setVisible(True)
        self.ip_matrix_container.setMaximumHeight(16777215)
        self.calculated_ip_entry.set_readonly(True)
        self.stepper.reset()

        self._append_log("[UI] Formulario limpiado")
        self.refresh_from_state()

    # Método para agregar un mensaje al log visual, y también guardarlo en el estado de la aplicación
    def _append_log(self, message: str) -> None:
        self.app_state.append_log(message)
        self._render_logs()

    # Método para renderizar el log visual
    def _render_logs(self) -> None:
        self.log_box.setPlainText("\n".join(self.app_state.get_visible_logs()))

    # Método para limpiar el mensaje de selección de equipo IP del log visual
    def _clear_ip_selection_log(self) -> None:
        prefix = "[UI] Equipo IP seleccionado:"
        self.app_state.execution.process_logs = [
            log
            for log in self.app_state.execution.process_logs
            if not log.startswith(prefix)
        ]
        self._render_logs()

    # Método para establecer un mensaje de selección de equipo IP en el log visual
    def _set_ip_selection_log(self, slot_number: int) -> None:
        prefix = "[UI] Equipo IP seleccionado:"
        self.app_state.execution.process_logs = [
            log
            for log in self.app_state.execution.process_logs
            if not log.startswith(prefix)
        ]
        self.app_state.execution.process_logs.append(
            f"{prefix} ONT {slot_number:02d}"
        )
        self._render_logs()

    # Método para limpiar el log visual, eliminando los mensajes del estado de la aplicación y del widget
    def _replace_logs_with(self, message: str) -> None:
        self.app_state.execution.logs.clear()
        self.log_box.clear()
        self._append_log(message)

    def _set_ip_custom_mode_log(self) -> None:
        prefix = "[UI] Modo IP custom:"
        self.app_state.execution.process_logs = [
            log for log in self.app_state.execution.process_logs if not log.startswith(prefix)
        ]
        self.app_state.execution.process_logs.append(f"{prefix} activado")
        self._render_logs()

    def _set_custom_ip_log(self, ip: str) -> None:
        prefix = "[UI] IP a aplicar:"
        self.app_state.execution.process_logs = [
            log for log in self.app_state.execution.process_logs if not log.startswith(prefix)
        ]
        self.app_state.execution.process_logs.append(
            f"{prefix} {ip}" if ip else f"{prefix} (pendiente)"
        )
        self._render_logs()

    def _clear_ip_custom_logs(self) -> None:
        for prefix in ("[UI] Modo IP custom:", "[UI] IP a aplicar:"):
            self.app_state.execution.process_logs = [
                log for log in self.app_state.execution.process_logs if not log.startswith(prefix)
            ]
        self._render_logs()
