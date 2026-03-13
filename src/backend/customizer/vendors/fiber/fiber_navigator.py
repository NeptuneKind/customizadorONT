from __future__ import annotations

import time
from typing import Optional, Sequence, Tuple, List

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from src.backend.customizer.models import WifiBand


Locator = Tuple[str, str]


class FiberhomeNavigator:
    """
    Navegador Selenium para GUI FiberHome.
    Mantiene la misma estructura base que HuaweiNavigator/ZTENavigator.
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
        self.driver.get(f"{self.base_url}/html/login_inter.html")

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
                elements = self.driver.find_elements(by, value)
                for el in elements:
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
        max_depth: int = 8,
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

            frames: List[WebElement] = []
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

    # Helper para hacer click en un elemento identificado por sus selectores buscando en todo el documento (incluyendo frames/iframes) y esperar a que se haga efectivo el cambio
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
    # Helpers específicos FiberHome
    # ==========================================================
    # Helper para asegurarse de estar en la página principal (main_inter.html)
    def _ensure_main_page(self) -> None:
        self._switch_to_default()
        try:
            self.driver.get(f"{self.base_url}/html/main_inter.html")
            time.sleep(1.0)
        except Exception:
            pass

    # Helper para obtener los selectores del menú Network
    def _network_menu_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "first_menu_network"),
            (By.ID, "network"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Network')]"),
        ]

    # Helper para obtener los selectores del menú Management
    def _manage_menu_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "first_menu_manage"),
            (By.ID, "manage"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Management')]"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Manage')]"),
        ]

    # Helper para obtener los selectores de 2.4G Advanced
    def _wifi_security_menu_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "thr_security"),
            (By.ID, "security"),
            (By.ID, "wlan_security"),
            (By.XPATH, "//*[contains(normalize-space(.), 'WLAN Security')]"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Wireless Security')]"),
        ]
    
    # Helper para obtener los selectores de 5G Advanced
    def _wifi_5Gsecurity_menu_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "thr_5Gsecurity"),
            (By.ID, "security"),
            (By.ID, "wlan_security"),
            (By.XPATH, "//*[contains(normalize-space(.), 'WLAN Security')]"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Wireless Security')]"),
        ]

    # Helper para obtener los selectores de los campos SSID según la banda
    def _ssid_field_selectors(self, band: WifiBand) -> Sequence[Locator]:
        if band in (WifiBand.B24, WifiBand.B5):
            return [
                #(By.ID, "ESSID"),
                (By.ID, "SSID"),
                (By.ID, "Ssid"),
                (By.ID, "wifi_ssid"),
                (By.ID, "WlanSsid"),
                (By.CSS_SELECTOR, "input[id*='ssid' i]"),
                (By.CSS_SELECTOR, "input[name*='ssid' i]"),
            ]

        raise RuntimeError(f"Banda WiFi no soportada en FiberHome: {band}")

    # Helper para obtener los selectores de los campos password según la banda
    def _password_field_selectors(self, band: WifiBand) -> Sequence[Locator]:
        if band in (WifiBand.B24, WifiBand.B5):
            return [
                (By.ID, "PreSharedKey"),
                (By.NAME, "PreSharedKey"),
                (By.CSS_SELECTOR, "input[id*='PreSharedKey' i]"),
                (By.CSS_SELECTOR, "input[name*='PreSharedKey' i]"),
            ]

        raise RuntimeError(f"Banda WiFi no soportada en FiberHome: {band}")

    # Helper para obtener los selectores del botón Apply en la sección WiFi
    def _apply_wifi_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "wireless_apply"),
            (By.CSS_SELECTOR, "input[type='button'][value*='Apply']"),
            (By.CSS_SELECTOR, "input[type='button'][value*='Save']"),
            (By.XPATH, "//button[contains(normalize-space(.), 'Apply')]"),
            (By.XPATH, "//button[contains(normalize-space(.), 'Save')]"),
        ]

    # Helper para obtener los selectores del botón Apply en la sección de credenciales web
    def _apply_web_credentials_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "apply"),
            (By.ID, "Apply_button"),
            (By.ID, "save"),
            (By.ID, "Save_button"),
            (By.CSS_SELECTOR, "input[type='button'][value*='Apply']"),
            (By.CSS_SELECTOR, "input[type='button'][value*='Save']"),
            (By.XPATH, "//button[contains(normalize-space(.), 'Apply')]"),
            (By.XPATH, "//button[contains(normalize-space(.), 'Save')]"),
        ]

    # Helper para obtener los selectores del botón Logout
    def _logout_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "logout"),
            (By.ID, "headerLogoutText"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Logout')]"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Log out')]"),
        ]

    # TODO: Cambiar por método de fiber_mixin para retirar la seguridad de la clase
    def _ensure_wifi_password_visible(self, band: WifiBand) -> None:
        if band not in (WifiBand.B24, WifiBand.B5):
            raise RuntimeError(f"Banda WiFi no soportada en FiberHome: {band}")

        password_field = self.find_element_anywhere(
            selectors=self._password_field_selectors(band),
            desc=f"campo password FiberHome {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        try:
            self.driver.execute_script("arguments[0].removeAttribute('class');", password_field)
        except Exception:
            pass

        try:
            self.driver.execute_script("arguments[0].type = 'text';", password_field)
        except Exception:
            pass

    # ==========================================================
    # Login
    # ==========================================================
    # Método para hacer login en la GUI de FiberHome
    def login(self, username: str, password: str) -> None:
        self._open_root()

        username_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "user_name"),
                (By.NAME, "user_name"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ],
            desc="campo username FiberHome",
            timeout_s=self.timeout_s,
        )

        password_field = None
        last_error: Optional[Exception] = None
        for selectors in [
            [(By.ID, "loginpp"), (By.NAME, "loginpp")],
            [(By.ID, "password"), (By.NAME, "password")],
            [(By.CSS_SELECTOR, "input[type='password']")],
        ]:
            try:
                password_field = self.find_element_anywhere(
                    selectors=selectors,
                    desc="campo password FiberHome",
                    timeout_s=2,
                    must_be_displayed=False,
                )
                break
            except Exception as exc:
                last_error = exc

        if password_field is None:
            raise RuntimeError(f"No se encontró campo password FiberHome. Último error: {last_error}")

        login_button = self.find_element_anywhere(
            selectors=[
                (By.ID, "login_btn"),
                (By.ID, "login"),
                (By.ID, "LoginId"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
            ],
            desc="botón login FiberHome",
            timeout_s=self.timeout_s,
            must_be_displayed=False,
        )

        self._set_input_value(username_field, username)
        self._set_input_value(password_field, password)

        try:
            self.driver.execute_script("arguments[0].click();", login_button)
        except Exception:
            login_button.click()

        self._maybe_accept_alert(timeout_s=2)
        time.sleep(1.5)
        self.fh_maybe_skip_initial_guide(timeout_s=1)
        self.wait_session_ready()

    # Método específico para login de verificación de credenciales web
    def login_for_verification(self, username: str, password: str) -> None:
        self._open_root()

        username_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "user_name"),
                (By.NAME, "user_name"),
            ],
            desc="campo username FiberHome",
            timeout_s=6,
        )

        password_field = None
        for selectors in [
            [(By.ID, "loginpp"), (By.NAME, "loginpp")],
            [(By.ID, "password"), (By.NAME, "password")],
        ]:
            try:
                password_field = self.find_element_anywhere(
                    selectors=selectors,
                    desc="campo password FiberHome",
                    timeout_s=2,
                    must_be_displayed=False,
                )
                break
            except Exception:
                continue

        if password_field is None:
            raise RuntimeError("No se encontró campo password FiberHome en login de verificación")

        login_button = self.find_element_anywhere(
            selectors=[
                (By.ID, "login_btn"),
                (By.ID, "login"),
                (By.ID, "LoginId"),
            ],
            desc="botón login FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )

        self._set_input_value(username_field, username)
        self._set_input_value(password_field, password)

        try:
            self.driver.execute_script("arguments[0].click();", login_button)
        except Exception:
            login_button.click()

        self._maybe_accept_alert(timeout_s=2)
        time.sleep(1.5)

        self.find_element_anywhere(
            selectors=self._logout_button_selectors(),
            desc="botón Logout FiberHome después de login de verificación",
            timeout_s=6,
            must_be_displayed=False,
        )

    # Método para esperar a que la sesión esté lista después del login, verificando la presencia de elementos clave o posibles mensajes de sesión ocupada
    def wait_session_ready(self, timeout_s: Optional[int] = None) -> None:
        timeout = timeout_s or self.timeout_s
        end_time = time.time() + timeout

        ready_markers = [
            (By.ID, "first_menu_network"),
            (By.ID, "first_menu_manage"),
            (By.ID, "thr_security"),
        ]

        while time.time() < end_time:
            self._switch_to_default()

            current_url = (self.driver.current_url or "").lower()
            if "login_inter.html" in current_url:
                page_source = (self.driver.page_source or "").lower()
                if "already" in page_source or "logged" in page_source:
                    raise RuntimeError("Sesión FiberHome ocupada: ya existe una sesión activa")
                time.sleep(0.25)
                continue

            for by, sel in ready_markers:
                try:
                    el = self.find_element_anywhere(
                        selectors=[(by, sel)],
                        desc=f"marker sesión FiberHome {sel}",
                        timeout_s=1,
                        must_be_displayed=False,
                    )
                    if el is not None:
                        return
                except Exception:
                    continue

            time.sleep(0.25)

        raise RuntimeError("No fue posible confirmar sesión activa en FiberHome")

    # ==========================================================
    # Navegación WiFi
    # ==========================================================
    # Método para ir a la sección avanzada de la banda WiFi indicada (2.4 o 5 GHz)
    def _go_to_wifi_advanced(self, band: WifiBand) -> None:
        try:
            already_here = self.find_element_anywhere(
                selectors=self._password_field_selectors(band),
                desc="campo password WiFi ya cargado",
                timeout_s=1,
                must_be_displayed=False,
            )
            if already_here is not None:
                # TODO: VER SI AQUI VA ALGO
                return
        except Exception:
            pass

        self._ensure_main_page()

        self.click_anywhere( # 1) Menú Network
            selectors=self._network_menu_selectors(),
            desc="menú Network FiberHome",
            timeout_s=8,
        )

        if band == WifiBand.B24:
            self.click_anywhere( # 2a) 2.4G Advanced
                selectors=self._wifi_security_menu_selectors(),
                desc="menú WLAN Security FiberHome",
                timeout_s=8,
            )
        else:
            self.click_anywhere( # 2b) 5G Advanced
                selectors=self._wifi_5Gsecurity_menu_selectors(),
                desc="menú WLAN Security FiberHome",
                timeout_s=8,
            )

        time.sleep(1.0)
        
        # self.find_element_anywhere(
        #     selectors=self._password_field_selectors(band),
        #     desc=f"campo password FiberHome {band.name}",
        #     timeout_s=6,
        #     must_be_displayed=False,
        # )

    # Helper para leer el SSID y password de la banda WiFi indicada
    def read_wifi_band(self, band: WifiBand) -> dict:
        self._go_to_wifi_advanced(band) # Ir a la sección avanzada de la banda WiFi
        self._ensure_wifi_password_visible(band)

        ssid_field = self.find_element_anywhere(
            selectors=self._ssid_field_selectors(band),
            desc=f"campo SSID FiberHome {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        password_field = self.find_element_anywhere(
            selectors=self._password_field_selectors(band),
            desc=f"campo password FiberHome {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        return {
            "ssid": self._get_input_value(ssid_field),
            "password": self._get_input_value(password_field),
        } # TODO: Asegurarse que el de password regrese; sino, metodo fiber_mixin

    #  Helper para actualizar el SSID y/o password de la banda WiFi indicada y devolver los valores antes y después del cambio
    def update_wifi_band(
        self,
        band: WifiBand,
        ssid: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict:
        # Ya no es necesario ir a Advanced, ya que el método read_wifi_band lo hace ya
        # Tampoco es necesario asegurar visibilidad de password, porque el método read_wifi_band ya lo hace también

        ssid_field = self.find_element_anywhere( # 1) Buscar campo SSID
            selectors=self._ssid_field_selectors(band),
            desc=f"campo SSID FiberHome {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        password_field = self.find_element_anywhere( # 2) Buscar campo password
            selectors=self._password_field_selectors(band),
            desc=f"campo password FiberHome {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )
    
        before = { # 3) Guardar valores antes de modificar para devolver al final
            "ssid": self._get_input_value(ssid_field),
            "password": self._get_input_value(password_field),
        }

        if ssid is not None: # 4a) Actualizar SSID si se recibió nuevo valor
            self._set_input_value(ssid_field, ssid)

        if password is not None: # 4b) Actualizar password si se recibió nuevo valor
            self._set_input_value(password_field, password)

        apply_btn = self.find_element_anywhere( # 5) Buscar botón Apply y hacer click para guardar cambios
            selectors=self._apply_wifi_button_selectors(),
            desc=f"botón Apply WiFi FiberHome {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

        try:
            apply_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", apply_btn)

        self._maybe_accept_alert(timeout_s=2)
        time.sleep(1.0)

        # No hace falta volver a cargar Advanced de la banda WiFi porque ya está ahí

        # ssid_field_after = self.find_element_anywhere( # 
        #     selectors=self._ssid_field_selectors(band),
        #     desc=f"campo SSID FiberHome {band.name} después de aplicar",
        #     timeout_s=6,
        #     must_be_displayed=False,
        # )

        # password_field_after = self.find_element_anywhere(
        #     selectors=self._password_field_selectors(band),
        #     desc=f"campo password FiberHome {band.name} después de aplicar",
        #     timeout_s=6,
        #     must_be_displayed=False,
        # )

        after = { # 6) Volver a leer valores después de aplicar cambios para devolver al final
            "ssid": self._get_input_value(ssid_field),
            "password": self._get_input_value(password_field),
        }

        return {
            "before": before,
            "after": after,
        } # TODO: ASEGURAR DE NUEVO SI AL CAMBIAR SSID Y/O PASSWORDS SALE ALERTA DE CHROME

    # ==========================================================
    # Credenciales web
    # ==========================================================
    def _go_to_web_credentials(self) -> None:
        try:
            self.find_element_anywhere(
                selectors=[
                    (By.ID, "oldPassword"),
                    (By.ID, "newPassword"),
                    (By.ID, "cfmPassword"),
                    (By.ID, "user_name_new"),
                    (By.ID, "new_user_name"),
                ],
                desc="pantalla credenciales web FiberHome ya cargada",
                timeout_s=1,
                must_be_displayed=False,
            )
            return
        except Exception:
            pass

        self._ensure_main_page()

        self.click_anywhere(
            selectors=self._manage_menu_selectors(),
            desc="menú Management FiberHome",
            timeout_s=8,
        )

        # Esta parte queda abierta a ajuste fino cuando tengamos la ruta exacta validada en Fiber.
        # Se dejan varios candidatos razonables para no romper la interfaz del adapter.
        self.click_anywhere(
            selectors=[
                (By.ID, "account_management"),
                (By.ID, "user_management"),
                (By.ID, "password_cfg"),
                (By.ID, "manage_password"),
                (By.XPATH, "//*[contains(normalize-space(.), 'Account')]"),
                (By.XPATH, "//*[contains(normalize-space(.), 'User')]"),
                (By.XPATH, "//*[contains(normalize-space(.), 'Password')]"),
            ],
            desc="sección credenciales web FiberHome",
            timeout_s=8,
        )

        time.sleep(1.0)

        self.find_element_anywhere(
            selectors=[
                (By.ID, "oldPassword"),
                (By.ID, "newPassword"),
                (By.ID, "cfmPassword"),
                (By.ID, "new_user_name"),
                (By.ID, "user_name_new"),
            ],
            desc="pantalla credenciales web FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )

    def read_web_credentials(self) -> dict:
        self._go_to_web_credentials()

        username_value = None
        for selectors in [
            [(By.ID, "user_name"), (By.NAME, "user_name")],
            [(By.ID, "new_user_name"), (By.NAME, "new_user_name")],
            [(By.ID, "user_name_new"), (By.NAME, "user_name_new")],
        ]:
            try:
                username_field = self.find_element_anywhere(
                    selectors=selectors,
                    desc="campo username web FiberHome",
                    timeout_s=1,
                    must_be_displayed=False,
                )
                username_value = self._get_input_value(username_field)
                if username_value:
                    break
            except Exception:
                continue

        return {
            "username": username_value or "root",
        }

    def logout(self) -> None:
        logout_btn = self.find_element_anywhere(
            selectors=self._logout_button_selectors(),
            desc="botón Logout FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )

        try:
            logout_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", logout_btn)

        self._maybe_accept_alert(timeout_s=2)
        time.sleep(1.5)

        self.find_element_anywhere(
            selectors=[
                (By.ID, "user_name"),
                (By.ID, "loginpp"),
                (By.ID, "password"),
                (By.ID, "login_btn"),
                (By.ID, "login"),
                (By.ID, "LoginId"),
            ],
            desc="pantalla de login FiberHome después de logout",
            timeout_s=6,
            must_be_displayed=False,
        )

    def update_web_credentials(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict:
        self._go_to_web_credentials()

        before = self.read_web_credentials()

        old_password_field = None
        for selectors in [
            [(By.ID, "oldPassword"), (By.NAME, "oldPassword")],
            [(By.ID, "old_password"), (By.NAME, "old_password")],
            [(By.ID, "password_old"), (By.NAME, "password_old")],
        ]:
            try:
                old_password_field = self.find_element_anywhere(
                    selectors=selectors,
                    desc="campo old password FiberHome",
                    timeout_s=2,
                    must_be_displayed=False,
                )
                break
            except Exception:
                continue

        new_username_field = None
        for selectors in [
            [(By.ID, "new_user_name"), (By.NAME, "new_user_name")],
            [(By.ID, "user_name_new"), (By.NAME, "user_name_new")],
            [(By.ID, "username"), (By.NAME, "username")],
        ]:
            try:
                new_username_field = self.find_element_anywhere(
                    selectors=selectors,
                    desc="campo new username FiberHome",
                    timeout_s=1,
                    must_be_displayed=False,
                )
                break
            except Exception:
                continue

        new_password_field = None
        for selectors in [
            [(By.ID, "newPassword"), (By.NAME, "newPassword")],
            [(By.ID, "new_password"), (By.NAME, "new_password")],
            [(By.ID, "password_new"), (By.NAME, "password_new")],
        ]:
            try:
                new_password_field = self.find_element_anywhere(
                    selectors=selectors,
                    desc="campo new password FiberHome",
                    timeout_s=2,
                    must_be_displayed=False,
                )
                break
            except Exception:
                continue

        confirm_password_field = None
        for selectors in [
            [(By.ID, "cfmPassword"), (By.NAME, "cfmPassword")],
            [(By.ID, "confirmPassword"), (By.NAME, "confirmPassword")],
            [(By.ID, "confirm_password"), (By.NAME, "confirm_password")],
        ]:
            try:
                confirm_password_field = self.find_element_anywhere(
                    selectors=selectors,
                    desc="campo confirm password FiberHome",
                    timeout_s=2,
                    must_be_displayed=False,
                )
                break
            except Exception:
                continue

        if old_password_field is None:
            raise RuntimeError("No se encontró campo old password FiberHome")

        if new_password_field is None:
            raise RuntimeError("No se encontró campo new password FiberHome")

        if confirm_password_field is None:
            raise RuntimeError("No se encontró campo confirm password FiberHome")

        self._set_input_value(old_password_field, "admin")

        if username is not None and new_username_field is not None:
            self._set_input_value(new_username_field, username)

        if password is None:
            raise RuntimeError("No se recibió nueva contraseña para credenciales web FiberHome")

        self._set_input_value(new_password_field, password)
        self._set_input_value(confirm_password_field, password)

        apply_btn = self.find_element_anywhere(
            selectors=self._apply_web_credentials_button_selectors(),
            desc="botón Apply web credentials FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )

        try:
            apply_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", apply_btn)

        self._maybe_accept_alert(timeout_s=2)
        time.sleep(1.0)

        return {
            "before": before,
            "after": {
                "username": username or before.get("username") or "root",
            },
        }

    def verify_web_credentials_login(
        self,
        username: str,
        password: str,
    ) -> bool:
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