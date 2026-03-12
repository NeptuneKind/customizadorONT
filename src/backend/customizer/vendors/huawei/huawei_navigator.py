from __future__ import annotations

import time
from typing import Optional, Sequence, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from src.backend.customizer.models import WifiBand


Locator = Tuple[str, str]


class HuaweiNavigator:
    """
    Navegador Selenium para GUI Huawei.
    Mantiene la misma estructura base que ZTENavigator
    """

    def __init__(self, driver: WebDriver, base_url: str, timeout_s: int = 10) -> None:
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    # ==========================================================
    # Helpers base
    # ==========================================================
    # Helper para abrir la raíz del router y resetear el contexto de navegación
    def _open_root(self) -> None:
        self._switch_to_default()
        self.driver.get(self.base_url)

    # Helper para resetear el contexto de navegación al documento principal (fuera de frames/iframes)
    def _switch_to_default(self) -> None:
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

    # Helper para buscar un elemento por sus selectores en el contexto actual (sin cambiar de frame) y devolverlo o None si no se encuentra
    def _find_in_current_context(
        self,
        selectors: Sequence[Locator],
        must_be_displayed: bool = True,
    ) -> Optional[WebElement]:
        for by, value in selectors:
            try:
                el = self.driver.find_element(by, value)
                if must_be_displayed and not el.is_displayed():
                    continue
                return el
            except Exception:
                continue
        return None

    # Helper para buscar un elemento por sus selectores en todo el documento (incluyendo frames/iframes) y devolverlo o lanzar error si no se encuentra en el tiempo indicado
    def find_element_anywhere(
        self,
        selectors: Sequence[Locator],
        desc: str,
        timeout_s: Optional[int] = None,
        must_be_displayed: bool = True,
        max_depth: int = 5,
    ) -> WebElement:
        timeout = timeout_s or self.timeout_s
        end_time = time.time() + timeout
        last_error: Optional[Exception] = None

        def _search_recursively(depth: int = 0) -> Optional[WebElement]:
            nonlocal last_error

            el = self._find_in_current_context(
                selectors=selectors,
                must_be_displayed=must_be_displayed,
            )
            if el is not None:
                return el

            if depth >= max_depth:
                return None

            frames = []
            try:
                frames.extend(self.driver.find_elements(By.TAG_NAME, "iframe"))
            except Exception:
                pass

            try:
                frames.extend(self.driver.find_elements(By.TAG_NAME, "frame"))
            except Exception:
                pass

            for frame in frames:
                try:
                    self.driver.switch_to.frame(frame)
                    found = _search_recursively(depth + 1)
                    if found is not None:
                        return found
                    self.driver.switch_to.parent_frame()
                except Exception as exc:
                    last_error = exc
                    try:
                        self.driver.switch_to.parent_frame()
                    except Exception:
                        try:
                            self.driver.switch_to.default_content()
                        except Exception:
                            pass
            return None

        while time.time() < end_time:
            try:
                self._switch_to_default()
                found = _search_recursively(0)
                if found is not None:
                    return found
            except (NoSuchElementException, StaleElementReferenceException) as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc

            time.sleep(0.25)

        if last_error is not None:
            raise RuntimeError(f"No se encontró {desc}. Último error: {last_error}")
        raise RuntimeError(f"No se encontró {desc} en {timeout}s")

    def click_anywhere(
        self,
        selectors: Sequence[Locator],
        desc: str,
        timeout_s: Optional[int] = None,
    ) -> WebElement:
        el = self.find_element_anywhere(
            selectors=selectors,
            desc=desc,
            timeout_s=timeout_s,
            must_be_displayed=False,
        )

        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                el,
            )
        except Exception:
            pass

        try:
            el.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", el)

        return el

    def _set_input_value(self, el: WebElement, value: str) -> None:
        desired = "" if value is None else str(value)

        try:
            self.driver.execute_script(
                """
                arguments[0].scrollIntoView({block:'center', inline:'center'});
                arguments[0].removeAttribute('readonly');
                arguments[0].removeAttribute('disabled');
                arguments[0].focus();
                """,
                el,
            )
        except Exception:
            pass

        try:
            el.clear()
        except Exception:
            pass

        try:
            self.driver.execute_script(
                """
                arguments[0].value = '';
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """,
                el,
            )
        except Exception:
            pass

        try:
            el.send_keys(desired)
        except Exception:
            pass

        current = self._get_input_value(el)
        if current == desired:
            return

        self.driver.execute_script(
            """
            arguments[0].removeAttribute('readonly');
            arguments[0].removeAttribute('disabled');
            arguments[0].focus();
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
            """,
            el,
            desired,
        )

        current = self._get_input_value(el)
        if current != desired:
            raise RuntimeError(
                f"No fue posible establecer el valor del input. Esperado='{desired}' obtenido='{current}'"
            )

    # Helper para hacer click en un elemento identificado por sus selectores buscando en todo el documento (incluyendo frames/iframes) y esperar a que se haga efectivo el cambio
    def click_anywhere(
        self,
        selectors: Sequence[Locator],
        desc: str,
        timeout_s: Optional[int] = None,
    ) -> WebElement:
        el = self.find_element_anywhere(selectors=selectors, desc=desc, timeout_s=timeout_s)
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                el,
            )
        except Exception:
            pass

        try:
            el.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", el)

        return el

    # Helper para establecer el valor de un campo input de forma robusta intentando varios métodos (send_keys, value+eventos, etc.)
    def _set_input_value(self, el: WebElement, value: str) -> None:
        desired = "" if value is None else str(value)

        try:
            self.driver.execute_script(
                """
                arguments[0].scrollIntoView({block:'center', inline:'center'});
                arguments[0].removeAttribute('readonly');
                arguments[0].removeAttribute('disabled');
                arguments[0].focus();
                """,
                el,
            )
        except Exception:
            pass

        try:
            el.clear()
        except Exception:
            pass

        try:
            self.driver.execute_script(
                """
                arguments[0].value = '';
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """,
                el,
            )
        except Exception:
            pass

        try:
            el.send_keys(desired)
        except Exception:
            pass

        current = self._get_input_value(el)
        if current == desired:
            return

        self.driver.execute_script(
            """
            arguments[0].removeAttribute('readonly');
            arguments[0].removeAttribute('disabled');
            arguments[0].focus();
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
            """,
            el,
            desired,
        )

        current = self._get_input_value(el)
        if current != desired:
            raise RuntimeError(
                f"No fue posible establecer el valor del input. Esperado='{desired}' obtenido='{current}'"
            )

    # Helper para obtener el valor de un campo input de forma robusta intentando varios métodos (value, get_attribute, etc.)
    def _get_input_value(self, el: WebElement) -> str:
        try:
            value = el.get_attribute("value")
            return (value or "").strip()
        except Exception:
            return ""

    # ==========================================================
    # Helpers específicos Huawei
    # ==========================================================
    # Método para detectar y saltar el asistente inicial de Huawei si aparece, haciendo click en los botones correspondientes. Devuelve True si se detectó y saltó el asistente, False si no se detectó.
    def hw_maybe_skip_initial_guide(self, timeout_s: Optional[int] = None) -> bool:
        timeout = timeout_s or self.timeout_s

        wizard_steps = [
            [("id", "guideinternet")],
            [("id", "guidesyscfg")],
            [("id", "guideskip")],
            [("id", "nextpage")],
        ]

        clicked_any = False

        for selectors_raw in wizard_steps:
            selectors = []
            for kind, value in selectors_raw:
                if kind == "id":
                    selectors.append((By.ID, value))

            try:
                el = self.find_element_anywhere(
                    selectors=selectors,
                    desc=f"wizard step {selectors_raw[0][1]}",
                    timeout_s=2 if timeout > 2 else timeout,
                    must_be_displayed=False,
                )
                try:
                    el.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", el)
                clicked_any = True
                time.sleep(1.0)
            except Exception:
                continue

        return clicked_any

    # ==========================================================
    # Login
    # ==========================================================
    def login(self, username: str, password: str) -> None:
        self._open_root()

        username_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "txt_Username"),
                (By.NAME, "txt_Username"),
                (By.ID, "Username"),
                (By.NAME, "Username"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ],
            desc="campo username Huawei",
            timeout_s=self.timeout_s,
        )

        password_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "txt_Password"),
                (By.NAME, "txt_Password"),
                (By.ID, "Password"),
                (By.NAME, "Password"),
                (By.CSS_SELECTOR, "input[type='password']"),
            ],
            desc="campo password Huawei",
            timeout_s=self.timeout_s,
        )

        self._set_input_value(username_field, username)
        self._set_input_value(password_field, password)

        login_button = self.find_element_anywhere(
            selectors=[
                (By.ID, "loginbutton"),
                (By.NAME, "loginbutton"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
            ],
            desc="botón login Huawei",
            timeout_s=self.timeout_s,
            must_be_displayed=False,
        )

        try:
            self.driver.execute_script("arguments[0].click();", login_button)
        except Exception:
            login_button.click()

        time.sleep(1.5)
        self.hw_maybe_skip_initial_guide(timeout_s=1)
        self.wait_session_ready()

    def login_for_verification(self, username: str, password: str) -> None:
        self._open_root()

        username_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "txt_Username"),
                (By.NAME, "txt_Username"),
            ],
            desc="campo username Huawei",
            timeout_s=6,
        )

        password_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "txt_Password"),
                (By.NAME, "txt_Password"),
            ],
            desc="campo password Huawei",
            timeout_s=6,
        )

        login_button = self.find_element_anywhere(
            selectors=[
                (By.ID, "loginbutton"),
                (By.NAME, "loginbutton"),
            ],
            desc="botón login Huawei",
            timeout_s=6,
            must_be_displayed=False,
        )

        self._set_input_value(username_field, username)
        self._set_input_value(password_field, password)

        try:
            self.driver.execute_script("arguments[0].click();", login_button)
        except Exception:
            login_button.click()

        time.sleep(1.5)

        # En verificación solo confirmamos que ya entró y que el logout existe.
        self.find_element_anywhere(
            selectors=[
                (By.ID, "headerLogoutText"),
            ],
            desc="botón Logout Huawei después de login de verificación",
            timeout_s=6,
            must_be_displayed=False,
        )
    
    def wait_session_ready(self, timeout_s: Optional[int] = None) -> None:
        timeout = timeout_s or self.timeout_s
        end_time = time.time() + timeout

        ready_markers = [
            (By.ID, "name_addconfig"),
            (By.ID, "name_wlanconfig"),
            (By.ID, "name_systemtools"),
            (By.ID, "name_securityconfig"),
            (By.ID, "name_userconfig"),
        ]

        while time.time() < end_time:
            self._switch_to_default()

            for by, sel in ready_markers:
                try:
                    el = self.find_element_anywhere(
                        selectors=[(by, sel)],
                        desc=f"marker sesión Huawei {sel}",
                        timeout_s=1,
                        must_be_displayed=False,
                    )
                    if el is not None:
                        return
                except Exception:
                    continue

            time.sleep(0.25)

        raise RuntimeError("No fue posible confirmar sesión activa en Huawei")

    # ==========================================================
    # Navegación WiFi
    # ==========================================================
    def _go_to_wifi_basic(self, band: WifiBand) -> None:
        # Si ya hay un campo wlSsid cargado, no fuerces de nuevo la navegación.
        # En este Huawei los IDs del formulario son iguales para 2.4G y 5G.
        try:
            already_here = self.find_element_anywhere(
                selectors=[(By.ID, "wlSsid")],
                desc="campo SSID WiFi ya cargado",
                timeout_s=1,
                must_be_displayed=False,
            )
            if already_here is not None:
                return
        except Exception:
            pass

        self.click_anywhere(
            selectors=[
                (By.ID, "name_addconfig"),
            ],
            desc="menú Advanced Configuration",
            timeout_s=8,
        )

        self.click_anywhere(
            selectors=[
                (By.ID, "name_wlanconfig"),
            ],
            desc="menú WLAN",
            timeout_s=8,
        )

        if band == WifiBand.B24:
            self.click_anywhere(
                selectors=[
                    (By.ID, "wlan2basic"),
                ],
                desc="WLAN 2.4G Basic Network Settings",
                timeout_s=8,
            )
        elif band == WifiBand.B5:
            self.click_anywhere(
                selectors=[
                    (By.ID, "wlan5basic"),
                ],
                desc="WLAN 5G Basic Network Settings",
                timeout_s=8,
            )
        else:
            raise RuntimeError(f"Banda WiFi no soportada en Huawei: {band}")

        time.sleep(1.0)

        # Valida que realmente quedó cargado el formulario
        self.find_element_anywhere(
            selectors=[(By.ID, "wlSsid")],
            desc=f"campo SSID después de navegar a {band.name}",
            timeout_s=5,
            must_be_displayed=False,
        )

    def _ssid_field_selectors(self, band: WifiBand) -> Sequence[Locator]:
        if band in (WifiBand.B24, WifiBand.B5):
            return [
                (By.ID, "wlSsid"),
                (By.NAME, "wlSsid"),
            ]

        raise RuntimeError(f"Banda WiFi no soportada en Huawei: {band}")

    def _password_field_selectors(self, band: WifiBand) -> Sequence[Locator]:
        if band in (WifiBand.B24, WifiBand.B5):
            return [
                (By.ID, "wlWpaPsk"),
                (By.NAME, "wlWpaPsk"),
            ]

        raise RuntimeError(f"Banda WiFi no soportada en Huawei: {band}")

    def _apply_wifi_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "btnApplySubmit"),
            (By.NAME, "btnApplySubmit"),
            (By.XPATH, "//button[@id='btnApplySubmit']"),
            (By.XPATH, "//button[@name='btnApplySubmit']"),
            (By.XPATH, "//button[contains(@onclick,'ApplySubmit')]"),
            (By.XPATH, "//button[contains(normalize-space(.), 'Apply')]"),
        ]

    def _ensure_wifi_password_visible(self, band: WifiBand) -> None:
        if band not in (WifiBand.B24, WifiBand.B5):
            raise RuntimeError(f"Banda WiFi no soportada en Huawei: {band}")

        try:
            hide_checkbox = self.find_element_anywhere(
                selectors=[
                    (By.ID, "hidewlWpaPsk"),
                    (By.NAME, "hidewlWpaPsk"),
                ],
                desc=f"toggle Hide password Huawei {band.name}",
                timeout_s=3,
                must_be_displayed=False,
            )
        except Exception:
            return

        try:
            checked = hide_checkbox.is_selected()
        except Exception:
            checked = hide_checkbox.get_attribute("checked") is not None

        if checked:
            try:
                hide_checkbox.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", hide_checkbox)
            time.sleep(0.3)

    def read_wifi_band(self, band: WifiBand) -> dict:
        self._go_to_wifi_basic(band)
        self._ensure_wifi_password_visible(band)

        ssid_field = self.find_element_anywhere(
            selectors=self._ssid_field_selectors(band),
            desc=f"campo SSID Huawei {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        password_field = self.find_element_anywhere(
            selectors=self._password_field_selectors(band),
            desc=f"campo password Huawei {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        return {
            "ssid": self._get_input_value(ssid_field),
            "password": self._get_input_value(password_field),
        }

    def update_wifi_band(
        self,
        band: WifiBand,
        ssid: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict:
        self._go_to_wifi_basic(band)
        self._ensure_wifi_password_visible(band)

        ssid_field = self.find_element_anywhere(
            selectors=self._ssid_field_selectors(band),
            desc=f"campo SSID Huawei {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        password_field = self.find_element_anywhere(
            selectors=self._password_field_selectors(band),
            desc=f"campo password Huawei {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        before = {
            "ssid": self._get_input_value(ssid_field),
            "password": self._get_input_value(password_field),
        }

        if ssid is not None:
            self._set_input_value(ssid_field, ssid)

        if password is not None:
            self._set_input_value(password_field, password)

        apply_btn = self.find_element_anywhere(
            selectors=self._apply_wifi_button_selectors(),
            desc=f"botón Apply WiFi Huawei {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        try:
            apply_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", apply_btn)

        time.sleep(1.0)

        self._go_to_wifi_basic(band)
        self._ensure_wifi_password_visible(band)

        ssid_field_after = self.find_element_anywhere(
            selectors=self._ssid_field_selectors(band),
            desc=f"campo SSID Huawei {band.name} después de aplicar",
            timeout_s=6,
            must_be_displayed=False,
        )

        password_field_after = self.find_element_anywhere(
            selectors=self._password_field_selectors(band),
            desc=f"campo password Huawei {band.name} después de aplicar",
            timeout_s=6,
            must_be_displayed=False,
        )

        after = {
            "ssid": self._get_input_value(ssid_field_after),
            "password": self._get_input_value(password_field_after),
        }

        return {
            "before": before,
            "after": after,
        }

    # ==========================================================
    # Credenciales web
    # ==========================================================
    def _go_to_web_credentials(self) -> None:
        # Si ya estamos en Account Management, no navegar otra vez
        try:
            self.find_element_anywhere(
                selectors=[(By.ID, "oldPassword")],
                desc="campo Old Password ya cargado",
                timeout_s=1,
                must_be_displayed=False,
            )
            return
        except Exception:
            pass

        # Asegurar que estamos en Advanced
        try:
            advanced_selected = self.find_element_anywhere(
                selectors=[
                    (By.ID, "name_addconfig"),
                    (By.XPATH, "//div[@id='name_addconfig' and contains(@class,'menuContTitleActive')]"),
                ],
                desc="sección Advanced activa",
                timeout_s=1,
                must_be_displayed=False,
            )
            if advanced_selected is None:
                raise RuntimeError("Advanced no activo")
        except Exception:
            self.click_anywhere(
                selectors=[
                    (By.ID, "addconfig"),
                    (By.ID, "name_addconfig"),
                ],
                desc="menú Advanced Huawei",
                timeout_s=8,
            )
            time.sleep(0.5)

        # Click en System Management
        self.click_anywhere(
            selectors=[
                (By.ID, "systool"),
                (By.ID, "name_systool"),
                (By.XPATH, "//div[@id='systool']"),
                (By.XPATH, "//div[@id='name_systool' and contains(normalize-space(.), 'System Management')]"),
            ],
            desc="menú System Management Huawei",
            timeout_s=8,
        )

        time.sleep(1.0)

        # Validar que ya quedó cargado Account Management
        self.find_element_anywhere(
            selectors=[
                (By.ID, "oldPassword"),
                (By.ID, "newPassword"),
                (By.ID, "cfmPassword"),
            ],
            desc="pantalla Account Management Huawei",
            timeout_s=6,
            must_be_displayed=False,
        )

    def read_web_credentials(self) -> dict:
        self._go_to_web_credentials()

        # En esta GUI el username no es editable; aparece fijo como root
        return {
            "username": "root",
        }

    def _apply_web_credentials_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.CSS_SELECTOR, "input#MdyPwdApply"),
            (By.ID, "MdyPwdApply"),
            (By.NAME, "MdyPwdApply"),
            (By.XPATH, "//input[@id='MdyPwdApply' and @type='button']"),
            (By.XPATH, "//input[@name='MdyPwdApply' and @type='button']"),
            (By.XPATH, "//input[@id='MdyPwdApply' and contains(@onclick,'SubmitPwd')]"),
            (By.XPATH, "//input[@type='button' and @value='Apply' and @id='MdyPwdApply']"),
        ]
    
    def _logout_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "headerLogoutText"),
            (By.XPATH, "//span[@id='headerLogoutText']"),
            (By.XPATH, "//span[contains(@onclick,'logoutfunc')]"),
            (By.XPATH, "//*[normalize-space(.)='Logout' and @id='headerLogoutText']"),
        ]
    
    def logout(self) -> None:
        logout_btn = self.find_element_anywhere(
            selectors=self._logout_button_selectors(),
            desc="botón Logout Huawei",
            timeout_s=6,
            must_be_displayed=False,
        )

        try:
            logout_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", logout_btn)

        time.sleep(1.5)

        # Validar que ya volvió la pantalla de login
        self.find_element_anywhere(
            selectors=[
                (By.ID, "txt_Username"),
                (By.ID, "txt_Password"),
                (By.ID, "loginbutton"),
            ],
            desc="pantalla de login Huawei después de logout",
            timeout_s=6,
            must_be_displayed=False,
        )

    def update_web_credentials(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict:
        self._go_to_web_credentials()

        old_password_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "oldPassword"),
                (By.NAME, "oldPassword"),
            ],
            desc="campo Old Password Huawei",
            timeout_s=6,
            must_be_displayed=False,
        )

        new_password_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "newPassword"),
                (By.NAME, "newPassword"),
            ],
            desc="campo New Password Huawei",
            timeout_s=6,
            must_be_displayed=False,
        )

        confirm_password_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "cfmPassword"),
                (By.NAME, "cfmPassword"),
            ],
            desc="campo Confirm Password Huawei",
            timeout_s=6,
            must_be_displayed=False,
        )

        before = {
            "username": "root",
        }

        # root no es editable en esta GUI, solo se cambia password
        self._set_input_value(old_password_field, "admin")

        if password is not None:
            self._set_input_value(new_password_field, password)
            self._set_input_value(confirm_password_field, password)
        else:
            raise RuntimeError("No se recibió nueva contraseña para credenciales web Huawei")

        apply_btn = self.find_element_anywhere(
            selectors=self._apply_web_credentials_button_selectors(),
            desc="botón Apply web credentials Huawei",
            timeout_s=6,
            must_be_displayed=True,
        )

        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                apply_btn,
            )
        except Exception:
            pass

        clicked = False

        try:
            apply_btn.click()
            clicked = True
        except Exception:
            pass

        if not clicked:
            try:
                self.driver.execute_script("arguments[0].click();", apply_btn)
                clicked = True
            except Exception:
                pass

        if not clicked:
            try:
                self.driver.execute_script(
                    """
                    if (typeof SubmitPwd === 'function') {
                        SubmitPwd();
                        return true;
                    }
                    return false;
                    """
                )
                clicked = True
            except Exception:
                pass

        if not clicked:
            raise RuntimeError("No fue posible ejecutar Apply en credenciales web Huawei")

        time.sleep(1.0)

        return {
            "before": before,
            "after": {
                "username": "root",
            },
        }

    def verify_web_credentials_login(
        self,
        username: str,
        password: str,
    ) -> bool:
        # Logout del usuario actual
        self.logout()

        try:
            self.login_for_verification(username=username, password=password)
        except Exception:
            return False

        try:
            self.logout()
        except Exception:
            pass

        return True