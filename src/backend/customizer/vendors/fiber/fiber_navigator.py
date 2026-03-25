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

    # Helper para asegurarse de estar en la página de login (login_inter.html)
    def _ensure_login_page(self) -> None:
        self._switch_to_default()

        try:
            current_url = (self.driver.current_url or "").lower()
            if "login_inter.html" in current_url:
                return
        except Exception:
            pass

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

    # Método para hacer reboot para aplicar cambios
    def reboot(self) -> None:
        # Desde donde quiera que estemos, será visible el menú Management
        self.click_anywhere( # 1) Menú Management
            selectors=self._manage_menu_selectors(),
            desc="menú Management FiberHome",
            timeout_s=8,
        )

        self.click_anywhere( # 2) Menú Device Management
            selectors=self._dev_man_selectors(),
            desc="Device Management",
            timeout_s=8,
        )

        self.click_anywhere( # 3) Menú Device Reboot
            selectors=self._dev_reboot_selectors(),
            desc="Device Reboot",
            timeout_s=8,
        )

        reboot_btn = self.find_element_anywhere( # 4) Botón Reboot
            selectors=self._reboot_btn_selectors(),
            desc="Reboot button"
        )
        
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                reboot_btn,
            )
        except Exception:
            pass

        try:
            reboot_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", reboot_btn)

        try:
            alert = WebDriverWait(self.driver, 2).until(EC.alert_is_present())
            alert.accept()
            time.sleep(0.2)
        except Exception as exc:
            raise RuntimeError(
                f"Se hizo click en Reboot FiberHome pero no apareció la alerta de confirmación: {exc}"
            )

    # ==========================================================
    # Helpers específicos FiberHome
    # ==========================================================
    # Helper para asegurarse de estar en la página principal (main_inter.html)
    def _ensure_main_page(self) -> None:
        self._switch_to_default()

        try:
            current_url = (self.driver.current_url or "").lower()
            if "main_inter.html" in current_url:
                return
        except Exception:
            pass

        try:
            self.driver.get(f"{self.base_url}/html/main_inter.html")
            time.sleep(0.5)
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

    # Helper para obtener los selectores del submenú Device Management dentro de Management
    def _dev_man_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "span_device_admin"),
            (By.ID, "device"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Device Management')]"),
        ]

    # Helper para obtener los selectores del submenú Device Reboot dentro de Management
    def _dev_reboot_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "thr_reboot"),
            (By.ID, "reboot"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Device Reboot')]"),
        ]
    
    # Helper para obtener los selectores del botón Reboot dentro de Device Reboot
    def _reboot_btn_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "Restart_button"),
            (By.CSS_SELECTOR, "input#Restart_button"),
            (By.CSS_SELECTOR, "input[type='button'][id='Restart_button']"),
            (By.XPATH, "//input[@id='Restart_button']"),
            (By.XPATH, "//input[@type='button' and @id='Restart_button']"),
        ]

    # Helper para retirar la seguridad de la clase de los campos PreShraredKey y dejarlos visibles para poder leer su valor
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
            self.driver.execute_script(
                """
                arguments[0].removeAttribute('class');
                arguments[0].removeAttribute('readonly');
                arguments[0].removeAttribute('disabled');
                """,
                password_field,
            )
        except Exception:
            pass

        try:
            self.driver.execute_script("arguments[0].type = 'text';", password_field)
        except Exception:
            pass

        try:
            _ = password_field.get_attribute("value")
        except Exception as exc:
            raise RuntimeError(
                f"No fue posible dejar visible el campo password FiberHome {band.name}: {exc}"
            )

    # ==========================================================
    # Login
    # ==========================================================
    # Método para hacer login en la GUI de FiberHome
    def login(self, username: str, password: str) -> None:
        self._ensure_login_page()

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

        self._maybe_accept_alert(timeout_s=1)
        self.wait_session_ready()

    # Método específico para login de verificación de credenciales web
    def login_for_verification(self, username: str, password: str) -> None:
        self._ensure_login_page()

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

        self._maybe_accept_alert(timeout_s=1)
        self.wait_session_ready()

        self.find_element_anywhere(
            selectors=self._logout_button_selectors(),
            desc="botón Logout FiberHome después de login de verificación",
            timeout_s=6,
            must_be_displayed=False,
        )

    # Helper para abrir una nueva pestaña en blanco
    def open_blank_verification_tab(
        self,
        timeout_s: float = 5.0,
        max_attempts: int = 2,
    ) -> str:
        previous_handle = self.driver.current_window_handle
        last_error: Optional[Exception] = None

        for _ in range(max_attempts):
            existing_handles = list(self.driver.window_handles)

            try:
                self.driver.switch_to.new_window("tab")
            except Exception as exc:
                last_error = exc
            else:
                try:
                    WebDriverWait(self.driver, timeout_s).until(
                        lambda d: len(d.window_handles) > len(existing_handles)
                    )
                except Exception as exc:
                    last_error = exc

                try:
                    new_handles = [h for h in self.driver.window_handles if h not in existing_handles]
                    if not new_handles:
                        raise RuntimeError("No se detectó el handle de la nueva pestaña")

                    self.driver.switch_to.window(new_handles[-1])
                    self._switch_to_default()

                    WebDriverWait(self.driver, timeout_s).until(
                        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
                    )

                    return previous_handle
                except Exception as exc:
                    last_error = exc

            try:
                self.driver.switch_to.window(previous_handle)
                self._switch_to_default()
            except Exception:
                pass

            try:
                self.driver.execute_script("window.open('about:blank', '_blank');")

                WebDriverWait(self.driver, timeout_s).until(
                    lambda d: len(d.window_handles) > len(existing_handles)
                )

                new_handles = [h for h in self.driver.window_handles if h not in existing_handles]
                if not new_handles:
                    raise RuntimeError("No se detectó el handle de la nueva pestaña")

                self.driver.switch_to.window(new_handles[-1])
                self._switch_to_default()

                WebDriverWait(self.driver, timeout_s).until(
                    lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
                )

                return previous_handle

            except Exception as exc:
                last_error = exc
                time.sleep(0.25)

            try:
                self.driver.switch_to.window(previous_handle)
                self._switch_to_default()
            except Exception:
                pass

        raise RuntimeError(f"No fue posible abrir una nueva pestaña de verificación: {last_error}")

    # Helper para cambiar entre pestañas del driver
    def switch_to_window(self, handle: str) -> None:
        self.driver.switch_to.window(handle)
        self._switch_to_default()

    # Helper para cerrar pestaña actual y volver a la pestaña anterior
    def close_current_tab_and_switch_back(self, previous_handle: str) -> None:
        self.driver.close()
        self.driver.switch_to.window(previous_handle)
        self._switch_to_default()

    # Helper para esperar hasta que la GUI de login quede accesible en la nueva IP después de un cambio de IP
    def wait_until_login_accessible_on_new_ip(
        self,
        new_ip: str,
        timeout_s: int = 90,
        retry_every_s: float = 5.0,
        per_attempt_wait_s: float = 1.5,
    ) -> None:
        target_url = f"http://{str(new_ip).strip()}/html/login_inter.html"
        end_time = time.time() + timeout_s
        last_error: Optional[Exception] = None

        login_selectors = [
            (By.ID, "user_name"),
            (By.NAME, "user_name"),
            (By.ID, "loginpp"),
            (By.NAME, "loginpp"),
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.ID, "login_btn"),
            (By.ID, "login"),
            (By.ID, "LoginId"),
        ]

        while time.time() < end_time:
            attempt_start = time.time()

            try:
                self._switch_to_default()

                try:
                    self.driver.execute_script("window.stop();")
                except Exception:
                    pass

                try:
                    self.driver.execute_script(
                        "window.location.replace(arguments[0]);",
                        target_url,
                    )
                except Exception as exc:
                    last_error = exc

                time.sleep(per_attempt_wait_s)

                try:
                    current_url = (self.driver.current_url or "").strip().lower()
                except Exception:
                    current_url = ""

                if "login_inter.html" in current_url or str(new_ip).strip().lower() in current_url:
                    try:
                        self.find_element_anywhere(
                            selectors=login_selectors,
                            desc="pantalla de login FiberHome en nueva IP",
                            timeout_s=1,
                            must_be_displayed=False,
                        )
                        return
                    except Exception as exc:
                        last_error = exc
                else:
                    try:
                        self.find_element_anywhere(
                            selectors=login_selectors,
                            desc="pantalla de login FiberHome en nueva IP",
                            timeout_s=1,
                            must_be_displayed=False,
                        )
                        return
                    except Exception as exc:
                        last_error = exc

                try:
                    self.driver.set_page_load_timeout(2)
                except Exception:
                    pass

                try:
                    self.driver.get(target_url)
                except Exception as exc:
                    last_error = exc
                finally:
                    try:
                        self.driver.set_page_load_timeout(30)
                    except Exception:
                        pass

                try:
                    self.find_element_anywhere(
                        selectors=login_selectors,
                        desc="pantalla de login FiberHome en nueva IP",
                        timeout_s=1,
                        must_be_displayed=False,
                    )
                    return
                except Exception as exc:
                    last_error = exc

            except Exception as exc:
                last_error = exc

            elapsed = time.time() - attempt_start
            remaining = retry_every_s - elapsed
            if remaining > 0:
                time.sleep(remaining)

        raise RuntimeError(
            f"No fue posible acceder al login FiberHome en la nueva IP '{new_ip}': {last_error}"
        )

    # Método para asegurar que etamos logueados, esperando a que la sesión esté lista
    def ensure_logged_in(self) -> None:
        self.wait_session_ready()

    # Método para esperar a que la sesión esté lista después del login, verificando la presencia de elementos clave o posibles mensajes de sesión ocupada
    def wait_session_ready(self, timeout_s: Optional[int] = None) -> None:
        timeout = timeout_s or 4
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
                time.sleep(0.15)
                continue

            try:
                marker = self.find_element_anywhere(
                    selectors=ready_markers,
                    desc="marker de sesión lista FiberHome",
                    timeout_s=0.5,
                    must_be_displayed=False,
                )
                if marker is not None:
                    return
            except Exception:
                pass

            time.sleep(0.15)

        raise RuntimeError("No fue posible confirmar sesión activa en FiberHome")

    # Helper para aceptar posibles alertas de Chrome al cambiar el SSID o password WiFi
    def _maybe_accept_alert(self, timeout_s: int = 1) -> None:
        try:
            alert = WebDriverWait(self.driver, timeout_s).until(EC.alert_is_present())
            alert.accept()
            time.sleep(0.2)
        except Exception:
            pass
    
    # Método para hacer logout con el botón
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

        self._maybe_accept_alert(timeout_s=1)

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
            timeout_s=2,
            must_be_displayed=False,
        )

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
        
        self.find_element_anywhere(
            selectors=self._password_field_selectors(band),
            desc=f"campo password FiberHome {band.name}",
            timeout_s=6,
            must_be_displayed=False,
        )

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
        self._go_to_wifi_advanced(band)
        self._ensure_wifi_password_visible(band)

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

        self._maybe_accept_alert(timeout_s=0.5)
        time.sleep(0.2)

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
        try: # Verificación por si ya estamos en la sección de credenciales web
            self.find_element_anywhere(
                selectors=[
                    (By.ID, "lan_old_password"), # Contraseña actual
                    (By.ID, "lan_new_password"), # Contraseña nueva
                    (By.ID, "lan_confirm_password"), # Confirmación contraseña nueva
                ],
                desc="pantalla credenciales web FiberHome ya cargada",
                timeout_s=1,
                must_be_displayed=False,
            )
            return
        except Exception: # Se ejecutó WifiPlan o estamos en la página principal
            pass

        self._ensure_main_page()

        self.click_anywhere(
            selectors=self._manage_menu_selectors(),
            desc="menú Management FiberHome",
            timeout_s=8,
        )

        self.find_element_anywhere(
            selectors=[
                (By.ID, "lan_old_password"), # Contraseña actual
                (By.ID, "lan_new_password"), # Contraseña nueva
                (By.ID, "lan_confirm_password"), # Confirmación contraseña nueva
            ],
            desc="pantalla credenciales web FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )

    def read_web_credentials(self) -> dict:
        self._go_to_web_credentials()

        return {
            "username": "root",
        }

    def update_web_credentials(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict:
        self._go_to_web_credentials()

        before = self.read_web_credentials()

        old_password_field = None
        for selectors in [
            [(By.ID, "lan_old_password"), (By.NAME, "lan_old_password")],
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

        new_password_field = None
        for selectors in [
            [(By.ID, "lan_new_password"), (By.NAME, "lan_new_password")],
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
            [(By.ID, "lan_confirm_password"), (By.NAME, "lan_confirm_password")],
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

        self._maybe_accept_alert(timeout_s=0.5)

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
        self.logout()

        try:
            self.login_for_verification(username=username, password=password)
            return True
        except Exception:
            return False
        
    # ==========================================================
    # IP (Gateway)
    # ==========================================================
    # Helper para obtener los selectores del menú LAN Settings
    def _lan_settings_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "span_lan_settings"),
            (By.ID, "sec_lan_settings"),
            (By.CSS_SELECTOR, "li#sec_lan_settings > span#span_lan_settings"),
            (By.CSS_SELECTOR, "#span_lan_settings"),
            (By.XPATH, "//li[@id='sec_lan_settings']//span[@id='span_lan_settings']"),
            (By.XPATH, "//span[@id='span_lan_settings' and normalize-space()='LAN Settings']"),
        ]

    # Helper para obtener los selectores del campo LAN Interface
    def _ip_field_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "LanIP_Address_text"),
            (By.NAME, "IP_Address_text"),
            (By.CSS_SELECTOR, "input#LanIP_Address_text"),
            (By.CSS_SELECTOR, "input[name='IP_Address_text']"),
            (By.XPATH, "//input[@id='LanIP_Address_text']"),
            (By.XPATH, "//input[@name='IP_Address_text']"),
        ]

    # Helper para obtener los selectores del botón Apply/Save en la sección IP
    def _apply_ip_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "inet_apply"),
            (By.CSS_SELECTOR, "input#inet_apply"),
            (By.CSS_SELECTOR, "input[type='button'][id='inet_apply'][value='Apply']"),
            (By.XPATH, "//input[@id='inet_apply']"),
            (By.XPATH, "//input[@type='button' and @id='inet_apply' and @value='Apply']"),
        ]

    # Método para ir a la sección de configuración IP/LAN del equipo
    def _go_to_ip_configuration(self) -> None:
        try: # Verificación por si ya estamos en la sección de configuración LAN
            self.find_element_anywhere(
                selectors=self._ip_field_selectors(),
                desc="pantalla IP/LAN FiberHome ya cargada",
                timeout_s=1,
                must_be_displayed=False,
            )
            return
        except Exception: # No estamos aún en la sección de configuración LAN
            pass

        self._ensure_main_page()

        self.click_anywhere( # 1) Menú Network
            selectors=self._network_menu_selectors(),
            desc="menú Network FiberHome",
            timeout_s=8,
        )

        self.click_anywhere( # 2) LAN Settings
            selectors=self._lan_settings_selectors(),
            desc="menú LAN Settings FiberHome",
            timeout_s=8,
        )

        self.find_element_anywhere( # 3) Verificar encontrando el input con la IP actual
            selectors=self._ip_field_selectors(),
            desc=f"campo IP FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )

    # Método para leer la configuración actual de IP/LAN
    def read_ip_configuration(self) -> dict:
        self._go_to_ip_configuration()

        ip_field = self.find_element_anywhere(
            selectors=self._ip_field_selectors(),
            desc="campo IP FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )

        return {
            "ip": self._get_input_value(ip_field),
        }

    # Método para actualizar la IP/LAN del equipo
    def update_ip_configuration(self, new_ip: str) -> dict:
        self._go_to_ip_configuration() # 1) Ir a la sección de LAN Settings

        if not new_ip or not str(new_ip).strip():
            raise RuntimeError("No se recibió nueva IP para FiberHome")

        new_ip = str(new_ip).strip()

        ip_field = self.find_element_anywhere( # 2) Buscar campo IP
            selectors=self._ip_field_selectors(),
            desc="campo IP FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )

        before = { # 2a) Guardar valor de IP antes de modificar para devolver al final
            "ip": self._get_input_value(ip_field),
        }

        self._set_input_value(ip_field, new_ip) # 2b) Actualizar campo IP con nueva IP

        apply_btn = self.find_element_anywhere( # 3) Buscar botón Apply y hacer click para guardar cambios
            selectors=self._apply_ip_button_selectors(),
            desc="botón Apply IP FiberHome",
            timeout_s=6,
            must_be_displayed=False,
        )
        try:
            apply_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", apply_btn)

        self._maybe_accept_alert(timeout_s=2)

        return { # 4) Devolver valores antes y después del cambio
            "before": before,
            "after": {
                "ip": new_ip,
            },
        }
    