from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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

# Mapa: fase backend → clave de step en stepper
_STEP_FOR_PHASE = {
    "LOGIN": "login",
    "WIFI": "wifi",
    "WEB": "web_credentials",
    "IP": "ip",
}

# Mapa: step → índice de conector a su izquierda (0=login-wifi, 1=wifi-web, 2=web-ip)
_CONNECTOR_FOR_STEP = {
    "wifi": 0,
    "web_credentials": 1,
    "ip": 2,
}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _format_progress_log(phase: str, message: str, data: dict) -> Optional[str]:
    """Convierte un ProgressEvent a una línea de log amigable para el usuario.
    Retorna None si el evento es interno y no debe mostrarse."""
    msg_lower = message.lower()

    if phase == "DETECT":
        if data.get("vendor"):
            vendor = data["vendor"].capitalize()
            product = data.get("product") or data.get("model", "")
            return f"[DETECTION] ONT {vendor} detectado — {product}"
        return "[DETECTION] Buscando ONT en la red..."

    if phase == "LOGIN":
        if "abriendo" in msg_lower:
            return "[LOGIN] Conectando a la interfaz web del ONT"
        if "iniciada" in msg_lower:
            return "[LOGIN] Sesión iniciada correctamente"
        # No mostrar intentos internos de credenciales
        return None

    if phase == "WIFI":
        band = "2.4GHz" if "2.4" in message else "5GHz"
        if "navegando" in msg_lower:
            return f"[WIFI] Navegando a configuración WiFi {band}"
        if "leyendo" in msg_lower:
            return f"[WIFI] Leyendo información actual WiFi {band}"
        if "aplicando" in msg_lower:
            ssid = data.get("ssid")
            pwd_set = data.get("password_set", False)
            if ssid and pwd_set:
                return f"[WIFI] Aplicando SSID y Password WiFi {band} — SSID: {ssid}"
            if ssid:
                return f"[WIFI] Aplicando SSID WiFi {band}: {ssid}"
            if pwd_set:
                return f"[WIFI] Aplicando Password WiFi {band}"
            return f"[WIFI] Aplicando cambios WiFi {band}"
        if "validando" in msg_lower:
            return f"[WIFI] Validando cambios WiFi {band}"
        return None

    if phase == "WEB":
        if "leyendo" in msg_lower:
            return "[WEB CRED] Navegando a configuración de credenciales"
        if "aplicando" in msg_lower:
            return "[WEB CRED] Aplicando nuevo password"
        if "verificando" in msg_lower:
            return "[WEB CRED] Verificando acceso con nuevo password"
        return None

    if phase == "IP":
        if "leyendo" in msg_lower:
            return "[IP] Leyendo configuración actual de IP"
        if "aplicando nueva ip" in msg_lower:
            new_ip = data.get("new_ip", "")
            return f"[IP] Aplicando nueva IP: {new_ip}" if new_ip else "[IP] Aplicando nueva IP"
        if "estabilización" in msg_lower or "estabilizaci" in msg_lower:
            return "[IP] Esperando estabilización del equipo"
        if "verificando acceso" in msg_lower or "pestaña" in msg_lower:
            new_ip = data.get("new_ip", "")
            return f"[IP] Verificando acceso en la nueva IP{': ' + new_ip if new_ip else ''}"
        if "esperando acceso" in msg_lower:
            new_ip = data.get("new_ip", "")
            return f"[IP] Aguardando respuesta del ONT{' en ' + new_ip if new_ip else ''}"
        # Cerrar sesión de verificación es detalle interno
        return None

    if phase == "LOGOUT":
        return "[LOGIN] Cerrando sesión"

    if phase == "ERROR":
        return f"[ERROR] {message}"

    return None


def _badge_for_event(phase: str, message: str) -> Optional[str]:
    """Retorna el badge kind correspondiente al evento, o None si no cambia."""
    msg_lower = message.lower()

    if phase == "DETECT":
        return "detectando"

    if phase == "LOGIN":
        return "customizando"

    if phase == "WIFI":
        if "validando" in msg_lower:
            return "validando"
        return "customizando"

    if phase == "WEB":
        if "verificando" in msg_lower:
            return "validando"
        return "customizando"

    if phase == "IP":
        if any(kw in msg_lower for kw in ("verificando acceso", "esperando acceso", "cerrando sesión")):
            return "validando"
        return "customizando"

    return None


class MainView(QWidget):
    def __init__(
        self,
        app_state: AppState,
        on_theme_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.on_theme_changed = on_theme_changed

        self._current_phase: Optional[str] = None
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        self.header = ViewHeader(
            app_state=self.app_state,
            section_title="Ejecución de planes",
            section_subtitle="El sistema mostrará aquí el flujo general de customización.",
            on_theme_changed=self.on_theme_changed,
            on_action_clicked=self._on_start_customization,
        )
        root.addWidget(self.header)

        content = QWidget()
        self.animation_target = content
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self.left_scroll = self._build_left_panel()
        self.right_panel = self._build_right_panel()

        content_layout.addWidget(self.left_scroll, 3)
        content_layout.addWidget(self.right_panel, 2)

        root.addWidget(content, 1)

        self._connect_readiness_signals()
        self.refresh_from_state()

    # ─── Panel izquierdo ────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setObjectName("leftPlansScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            """
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; border: none; }
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

    # ─── Panel derecho ──────────────────────────────────────────────

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.stepper = StatusStepper()

        self.log_card = SectionCard(
            title="Logs del sistema",
            subtitle="Mensajes de backend y eventos de ejecución",
        )

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_card.body_layout.addWidget(self.log_box)

        layout.addWidget(self.stepper, 1)
        layout.addWidget(self.log_card, 1)

        return panel

    # ─── Campos WiFi ────────────────────────────────────────────────

    def _build_wifi_fields(self) -> None:
        note = QLabel("Valores contemplados desde configuración.")
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

    # ─── Campos Web Credentials ─────────────────────────────────────

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

    # ─── Campos IP ──────────────────────────────────────────────────

    def _build_ip_fields(self) -> None:
        self.ip_custom_check = QCheckBox("IP custom")
        self.ip_custom_check.setObjectName("subCheck")
        self.ip_custom_check.toggled.connect(self._on_ip_custom_toggled)

        self.ip_matrix_container = QWidget()
        matrix_layout = QVBoxLayout(self.ip_matrix_container)
        matrix_layout.setContentsMargins(0, 0, 0, 0)
        matrix_layout.setSpacing(8)

        note = QLabel("Selecciona solo un equipo. La IP a aplicar se calculará automáticamente.")
        note.setProperty("muted", True)
        note.setWordWrap(True)

        self.ip_selector = IPSlotSelector(
            on_selected=self._on_ip_slot_selected,
            rows=4,
            columns=6,
        )

        matrix_layout.addWidget(note)
        matrix_layout.addWidget(self.ip_selector)

        self.calculated_ip_entry = LabeledEntry("IP a aplicar", readonly=True, validator=validate_ipv4)
        self.calculated_ip_entry.set_validation_enabled(False)
        self.calculated_ip_entry.entry.textChanged.connect(self._on_custom_ip_text_changed)

        self.ip_card.fields_layout.addWidget(self.ip_custom_check)
        self.ip_card.fields_layout.addWidget(self.ip_matrix_container)
        self.ip_card.fields_layout.addWidget(self.calculated_ip_entry)

        self.ip_card.add_field_widget(self.ip_selector)
        self.ip_card.add_field_widget(self.calculated_ip_entry)

    # ─── Señales de readiness ───────────────────────────────────────

    def _connect_readiness_signals(self) -> None:
        for entry in (
            self.wifi_ssid_24, self.wifi_password_24,
            self.wifi_ssid_5, self.wifi_password_5,
            self.web_new_password,
        ):
            entry.entry.textChanged.connect(self._update_badge_state)

    # ─── Handlers de toggles ────────────────────────────────────────

    def _on_wifi_toggle(self, enabled: bool) -> None:
        self.app_state.execution.wifi.enabled = enabled
        if enabled:
            self.app_state.execution.ip_plan.enabled = False
            self._clear_ip_selection_log()
            self._clear_formulario_limpiado_log()

        self._apply_plan_rules()
        self.app_state.rebuild_plan_logs()
        self._sync_stepper_enabled_states()
        self.refresh_from_state()

    def _on_web_toggle(self, enabled: bool) -> None:
        self.app_state.execution.web_credentials.enabled = enabled
        if enabled:
            self.app_state.execution.ip_plan.enabled = False
            self._clear_ip_selection_log()
            self._clear_formulario_limpiado_log()

        self._apply_plan_rules()
        self.app_state.rebuild_plan_logs()
        self._sync_stepper_enabled_states()
        self.refresh_from_state()

    def _on_ip_toggle(self, enabled: bool) -> None:
        self.app_state.execution.ip_plan.enabled = enabled
        if enabled:
            self.app_state.execution.wifi.enabled = False
            self.app_state.execution.web_credentials.enabled = False
            self._clear_formulario_limpiado_log()
        else:
            self._clear_ip_selection_log()
            self._clear_ip_custom_logs()
            self.app_state.execution.ip_custom = False

        self._apply_plan_rules()
        self.app_state.rebuild_plan_logs()
        self._sync_stepper_enabled_states()
        self.refresh_from_state()

    def _on_ip_custom_toggled(self, custom: bool) -> None:
        self.app_state.execution.ip_custom = custom

        if custom:
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
            self.app_state.execution.calculated_ip = ""
            self.calculated_ip_entry.set("")
            self.calculated_ip_entry.set_readonly(True)
            self.calculated_ip_entry.set_validation_enabled(False)
            self._clear_ip_custom_logs()

        animate_collapsible(self.ip_matrix_container, collapsed=custom, duration=DURATION_STANDARD)
        self._update_badge_state()

    def _on_custom_ip_text_changed(self, text: str) -> None:
        if self.app_state.execution.ip_custom:
            self.app_state.execution.calculated_ip = text
            self._set_custom_ip_log(text)
            self._render_logs()
        self._update_badge_state()

    def _on_ip_slot_selected(self, slot_number: int | None) -> None:
        self.app_state.execution.selected_slot = slot_number

        if slot_number is None:
            self.app_state.execution.calculated_ip = ""
            self.calculated_ip_entry.set("")
            self.calculated_ip_entry.set_readonly(True)
            self._clear_ip_selection_log()
            self._update_badge_state()
            return

        placeholder_ip = f"192.168.50.{int(slot_number)}"
        self.app_state.execution.calculated_ip = placeholder_ip
        self.calculated_ip_entry.set(placeholder_ip)
        self.calculated_ip_entry.set_readonly(True)
        self._set_ip_selection_log(slot_number)
        self._update_badge_state()

    def _apply_plan_rules(self) -> None:
        self.app_state.sync_plan_rules()

    # ─── Refresh ────────────────────────────────────────────────────

    def refresh_from_state(self) -> None:
        execution = self.app_state.execution
        self.web_old_password.set(self.app_state.standard_settings.web_actual_password)

        if not self.app_state.is_running:
            self._update_badge_state()

        self.header.refresh_from_state()

        self.wifi_card.set_value(execution.wifi.enabled)
        self.web_card.set_value(execution.web_credentials.enabled)
        self.ip_card.set_value(execution.ip_plan.enabled)

        self.wifi_card.set_fields_enabled(execution.wifi.fields_enabled)
        self.web_card.set_fields_enabled(execution.web_credentials.fields_enabled)
        self.ip_card.set_fields_enabled(execution.ip_plan.fields_enabled)
        self.ip_selector.set_enabled(execution.ip_plan.fields_enabled and not execution.ip_custom)

        self.ip_custom_check.blockSignals(True)
        self.ip_custom_check.setChecked(execution.ip_custom)
        self.ip_custom_check.blockSignals(False)
        self.ip_custom_check.setEnabled(execution.ip_plan.fields_enabled)

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

        self._render_logs()

    # ─── Badge / readiness ──────────────────────────────────────────

    def _compute_readiness(self) -> Tuple[str, str]:
        ex = self.app_state.execution
        wifi_en = ex.wifi.enabled
        web_en = ex.web_credentials.enabled
        ip_en = ex.ip_plan.enabled

        if not (wifi_en or web_en or ip_en):
            return "idle", "Listo"

        if wifi_en:
            for entry in (self.wifi_ssid_24, self.wifi_password_24, self.wifi_ssid_5, self.wifi_password_5):
                if not entry.is_valid():
                    return "idle", "Listo"

        if web_en:
            if not self.web_new_password.get():
                return "idle", "Listo"
            if not self.web_new_password.is_valid():
                return "idle", "Listo"

        if ip_en:
            if ex.ip_custom:
                if not ex.calculated_ip or not self.calculated_ip_entry.is_valid():
                    return "idle", "Listo"
            else:
                if ex.selected_slot is None:
                    return "idle", "Listo"

        return "preparado", "Preparado"

    def _update_badge_state(self) -> None:
        if self.app_state.is_running:
            return
        kind, text = self._compute_readiness()
        self.app_state.set_global_status(text, kind)
        self.header.refresh_from_state()

    # ─── Stepper circles ────────────────────────────────────────────

    def _sync_stepper_enabled_states(self) -> None:
        if self.app_state.is_running:
            return
        ex = self.app_state.execution
        any_plan = ex.wifi.enabled or ex.web_credentials.enabled or ex.ip_plan.enabled

        self.stepper.set_step_status("login", "enabled" if any_plan else "pending")
        self.stepper.set_step_status("wifi", "enabled" if ex.wifi.enabled else "pending")
        self.stepper.set_step_status("web_credentials", "enabled" if ex.web_credentials.enabled else "pending")
        self.stepper.set_step_status("ip", "enabled" if ex.ip_plan.enabled else "pending")

        # Conectores en gris hasta que empiece la ejecución
        for i in range(3):
            self.stepper.set_connector_status(i, "default")

    # ─── Inicio de customización ────────────────────────────────────

    def _on_start_customization(self) -> None:
        if self.app_state.is_running:
            return

        kind, _ = self._compute_readiness()
        if kind != "preparado":
            return

        self._start_new_customization_run()

    def _start_new_customization_run(self) -> None:
        from config.settings import load_or_init_settings
        from src.backend.customizer.models import CustomizationPlan, WifiPlan, WebCredentialsPlan, IPPlan
        from src.frontend.worker import CustomizationWorker

        # Limpiar logs del run anterior (sólo process_logs; plan_logs se conservan)
        self.app_state.execution.process_logs.clear()
        self._append_log("[CUSTOM] Se inició la customización")

        # Reset stepper
        ex = self.app_state.execution
        any_plan = ex.wifi.enabled or ex.web_credentials.enabled or ex.ip_plan.enabled
        self.stepper.set_step_status("login", "enabled" if any_plan else "pending")
        self.stepper.set_step_status("wifi", "enabled" if ex.wifi.enabled else "pending")
        self.stepper.set_step_status("web_credentials", "enabled" if ex.web_credentials.enabled else "pending")
        self.stepper.set_step_status("ip", "enabled" if ex.ip_plan.enabled else "pending")
        for i in range(3):
            self.stepper.set_connector_status(i, "default")

        # Reset device info en stepper
        self.app_state.execution.vendor = "--"
        self.app_state.execution.current_ip = "--"
        self.app_state.execution.model_code = "--"
        self.stepper.set_device_info("--", "--", "--")

        # Marcar como corriendo
        self.app_state.is_running = True
        self._current_phase = None
        self.app_state.set_global_status("Detectando", "detectando")
        self.header.refresh_from_state()

        # Construir plan
        plan = CustomizationPlan(
            wifi=WifiPlan(
                enabled=ex.wifi.enabled,
                ssid_24=self.wifi_ssid_24.get() or None,
                pass_24=self.wifi_password_24.get() or None,
                ssid_5=self.wifi_ssid_5.get() or None,
                pass_5=self.wifi_password_5.get() or None,
            ),
            web_credentials=WebCredentialsPlan(
                enabled=ex.web_credentials.enabled,
                old_password=self.web_old_password.get() or "admin",
                new_password=self.web_new_password.get(),
            ),
            ip=IPPlan(
                enabled=ex.ip_plan.enabled,
                new_ip=ex.calculated_ip,
            ),
        )

        # Cargar settings y agregar contraseña actual como candidato de login
        CONFIG_DIR = _PROJECT_ROOT / "config"
        settings = load_or_init_settings(PROJECT_ROOT=_PROJECT_ROOT, CONFIG_DIR=CONFIG_DIR)

        current_pwd = self.app_state.standard_settings.web_actual_password
        if current_pwd:
            for vendor_key in ("huawei", "zte", "fiber"):
                candidates = list(settings.get("login_candidates", {}).get(vendor_key, []))
                new_cand = {"user": "root", "pass": current_pwd}
                if new_cand not in candidates:
                    candidates.insert(0, new_cand)
                settings.setdefault("login_candidates", {})[vendor_key] = candidates

        ips = [
            self.app_state.standard_settings.brand_ip_huawei_fiber,
            self.app_state.standard_settings.brand_ip_zte,
        ]

        self._worker = CustomizationWorker(
            plan=plan,
            settings=settings,
            ips=ips,
            project_root=_PROJECT_ROOT,
            parent=self,
        )
        self._worker.event_received.connect(self._on_progress_event)
        self._worker.run_finished.connect(self._on_run_finished)
        self._worker.start()

    # ─── Progress events ────────────────────────────────────────────

    def _on_progress_event(self, evt) -> None:
        phase = evt.phase
        message = evt.message
        data = evt.data or {}

        # Log amigable
        log_msg = _format_progress_log(phase, message, data)
        if log_msg:
            self._append_log(log_msg)

        # Actualizar device info si llega la detección
        if phase == "DETECT" and data.get("vendor"):
            self.app_state.execution.vendor = data["vendor"].capitalize()
            self.app_state.execution.current_ip = data.get("ip", "--")
            self.app_state.execution.model_code = data.get("product") or data.get("model", "--")
            self.stepper.set_device_info(
                vendor=self.app_state.execution.vendor,
                current_ip=self.app_state.execution.current_ip,
                model=self.app_state.execution.model_code,
            )

        # Badge
        new_badge = _badge_for_event(phase, message)
        if new_badge:
            badge_texts = {
                "detectando": "Detectando",
                "customizando": "Customizando",
                "validando": "Validando",
            }
            self.app_state.set_global_status(badge_texts.get(new_badge, new_badge.capitalize()), new_badge)
            self.header.refresh_from_state()

        # Stepper: completar fase previa y activar la nueva
        new_step = _STEP_FOR_PHASE.get(phase)
        prev_step = _STEP_FOR_PHASE.get(self._current_phase) if self._current_phase else None

        if new_step and new_step != prev_step:
            # Completar el step anterior
            if prev_step and prev_step != "login":
                self.stepper.set_step_status(prev_step, "success")
                conn_idx = _CONNECTOR_FOR_STEP.get(prev_step)
                if conn_idx is not None:
                    self.stepper.set_connector_status(conn_idx, "success")
            elif prev_step == "login":
                self.stepper.set_step_status("login", "success")

            # Activar step nuevo
            self.stepper.set_step_status(new_step, "running")
            conn_idx = _CONNECTOR_FOR_STEP.get(new_step)
            if conn_idx is not None:
                self.stepper.set_connector_status(conn_idx, "running")

            self._current_phase = phase

        self._render_logs()

    def _on_run_finished(self, ok: bool, errors: list) -> None:
        self.app_state.is_running = False

        ex = self.app_state.execution
        wifi_en = ex.wifi.enabled
        web_en = ex.web_credentials.enabled
        ip_en = ex.ip_plan.enabled

        # Finalizar el step activo
        active_step = _STEP_FOR_PHASE.get(self._current_phase) if self._current_phase else None
        if active_step:
            final_step_status = "success" if ok else "error"
            self.stepper.set_step_status(active_step, final_step_status)
            conn_idx = _CONNECTOR_FOR_STEP.get(active_step)
            if conn_idx is not None:
                self.stepper.set_connector_status(conn_idx, final_step_status)

        # Login siempre termina (si llegamos hasta aquí)
        if ok:
            self.stepper.set_step_status("login", "success")

        # Determinar badge final
        if ok:
            badge_kind = "finalizado"
            badge_text = "Finalizado"
            self._append_log("[CUSTOM] Customización completada con éxito")
        elif wifi_en and web_en and not ip_en:
            # Único caso multi-plan: incompleto si solo uno falló
            badge_kind = "incompleto"
            badge_text = "Incompleto"
            self._append_log("[CUSTOM] Customización completada parcialmente")
        else:
            badge_kind = "error"
            badge_text = "Error"
            self._append_log("[CUSTOM] La customización encontró errores")
            if errors:
                self._append_log(f"[ERROR] {errors[0]}")

        self.app_state.set_global_status(badge_text, badge_kind)
        self.header.refresh_from_state()
        self._current_phase = None
        self._render_logs()

    # ─── Clear ──────────────────────────────────────────────────────

    def _on_clear_clicked(self) -> None:
        if self.app_state.is_running:
            return

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

    def set_logo_path(self, logo_path: str | Path) -> None:
        return

    # ─── Logs helpers ───────────────────────────────────────────────

    def _append_log(self, message: str) -> None:
        self.app_state.append_log(message)
        self._render_logs()

    def _render_logs(self) -> None:
        self.log_box.setPlainText("\n".join(self.app_state.get_visible_logs()))
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _clear_ip_selection_log(self) -> None:
        prefix = "[UI] Equipo IP seleccionado:"
        self.app_state.execution.process_logs = [
            log for log in self.app_state.execution.process_logs
            if not log.startswith(prefix)
        ]
        self._render_logs()

    def _set_ip_selection_log(self, slot_number: int) -> None:
        prefix = "[UI] Equipo IP seleccionado:"
        self.app_state.execution.process_logs = [
            log for log in self.app_state.execution.process_logs
            if not log.startswith(prefix)
        ]
        self.app_state.execution.process_logs.append(f"{prefix} ONT {slot_number:02d}")
        self._render_logs()

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

    def _clear_formulario_limpiado_log(self) -> None:
        prefix = "[UI] Formulario limpiado"
        self.app_state.execution.process_logs = [
            log for log in self.app_state.execution.process_logs if not log.startswith(prefix)
        ]
        self._render_logs()
