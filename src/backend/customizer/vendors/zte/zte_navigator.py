from __future__ import annotations

import time
from typing import Optional, Sequence, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

Locator = Tuple[str, str]

class ZTENavigator:
    """
    Navegador Selenium para GUI ZTE.
    Basado en la lógica validada del tester, pero desacoplado de mixins.
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
        self.driver.switch_to.default_content()
        self.driver.get(f"{self.base_url}/")

    # Helper para asegurarse de estar en la página principal (IP default)
    def _ensure_main_page(self) -> None:
        self._switch_to_default()

        try:
            current_url = (self.driver.current_url or "").lower()
            if "192.168.1.1" in current_url:
                return
        except Exception:
            pass

        try:
            self.driver.get(f"{self.base_url}")
            time.sleep(0.5)
        except Exception:
            pass

    # Helper para resetear el contexto de navegación al documento principal (fuera de frames/iframes)
    def _switch_to_default(self) -> None:
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

    # Helper para buscar un elemento por sus selectores en el contexto actual (sin cambiar de frame) y devolverlo o None si no se encuentra
    def _find_in_current_context(self, by: str, value: str) -> Optional[WebElement]:
        try:
            el = self.driver.find_element(by, value)
            return el
        except NoSuchElementException:
            return None

    # Helper para buscar un elemento por sus selectores en todo el documento (incluyendo frames/iframes) y devolverlo o lanzar error si no se encuentra en el tiempo indicado
    def find_element_anywhere(
        self,
        selectors: Sequence[Locator],
        desc: str,
        timeout_s: Optional[int] = None,
        must_be_displayed: bool = True,
    ) -> Optional[WebElement]:
        """
        Busca un elemento en documento principal y en frames/iframes.
        """
        timeout = timeout_s or self.timeout_s
        end_time = time.time() + timeout
        last_error: Optional[Exception] = None

        while time.time() < end_time:
            self._switch_to_default()

            # Documento principal
            for by, sel in selectors:
                try:
                    el = self._find_in_current_context(by, sel)
                    if el is None:
                        continue
                    if must_be_displayed and not el.is_displayed():
                        continue
                    return el
                except StaleElementReferenceException as exc:
                    last_error = exc
                except Exception as exc:
                    last_error = exc

            # Frames / iframes
            try:
                frames = self.driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
            except Exception:
                frames = []

            for frame in frames:
                try:
                    self._switch_to_default()
                    self.driver.switch_to.frame(frame)
                except Exception:
                    continue

                for by, sel in selectors:
                    try:
                        el = self._find_in_current_context(by, sel)
                        if el is None:
                            continue
                        if must_be_displayed and not el.is_displayed():
                            continue
                        return el
                    except StaleElementReferenceException as exc:
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
    # Helpers de login
    # ==========================================================
    # Helper para hacer login con credenciales por defecto (root/admin)
    def _zte_login(self, username: str = "root", password: str = "admin") -> None:
        self._open_root()

        username_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "Frm_Username"),
                (By.NAME, "Frm_Username"),
                (By.ID, "username"),
                (By.NAME, "username"),
                (By.ID, "user"),
                (By.NAME, "user"),
                (By.ID, "user_name"),
                (By.NAME, "user_name"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ],
            desc="campo username ZTE",
            timeout_s=self.timeout_s,
        )

        password_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "Frm_Password"),
                (By.NAME, "Frm_Password"),
                (By.ID, "password"),
                (By.NAME, "password"),
                (By.ID, "pass"),
                (By.NAME, "pass"),
                (By.ID, "loginpp"),
                (By.NAME, "loginpp"),
                (By.CSS_SELECTOR, "input[type='password']"),
            ],
            desc="campo password ZTE",
            timeout_s=self.timeout_s,
        )

        self._set_input_value(username_field, username)
        self._set_input_value(password_field, password)

        login_button = self.find_element_anywhere(
            selectors=[
                (By.ID, "LoginId"),
                (By.ID, "login_btn"),
                (By.NAME, "login"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
            ],
            desc="botón login ZTE",
            timeout_s=self.timeout_s,
            must_be_displayed=False,
        )

        try:
            self.driver.execute_script("arguments[0].click();", login_button)
        except Exception:
            login_button.click()

        self.wait_session_ready()

    # Helper para hacer login con credenciales de superusuario
    def _zte_login_super(self, username: str = "admin", password: str = "Zgs12O5TSa2l3o9") -> None:
        self._open_root()

        username_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "Frm_Username"),
                (By.NAME, "Frm_Username"),
                (By.ID, "username"),
                (By.NAME, "username"),
                (By.ID, "user"),
                (By.NAME, "user"),
                (By.ID, "user_name"),
                (By.NAME, "user_name"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ],
            desc="campo username ZTE",
            timeout_s=self.timeout_s,
        )

        password_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "Frm_Password"),
                (By.NAME, "Frm_Password"),
                (By.ID, "password"),
                (By.NAME, "password"),
                (By.ID, "pass"),
                (By.NAME, "pass"),
                (By.ID, "loginpp"),
                (By.NAME, "loginpp"),
                (By.CSS_SELECTOR, "input[type='password']"),
            ],
            desc="campo password ZTE",
            timeout_s=self.timeout_s,
        )

        self._set_input_value(username_field, username)
        self._set_input_value(password_field, password)

        login_button = self.find_element_anywhere(
            selectors=[
                (By.ID, "LoginId"),
                (By.ID, "login_btn"),
                (By.NAME, "login"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
            ],
            desc="botón login ZTE",
            timeout_s=self.timeout_s,
            must_be_displayed=False,
        )

        try:
            self.driver.execute_script("arguments[0].click();", login_button)
        except Exception:
            login_button.click()

        self.wait_session_ready()

    # Método específico para login de verificación de credenciales web
    def login_for_verification(self, username: str, password: str) -> None:
        username_field = self.find_element_anywhere(
            selectors=[
                (By.ID, "Frm_Username"),
                (By.NAME, "Frm_Username"),
                (By.ID, "username"),
                (By.NAME, "username"),
                (By.ID, "user"),
                (By.NAME, "user"),
                (By.ID, "user_name"),
                (By.NAME, "user_name"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ],
            desc="campo username FiberHome",
            timeout_s=6,
        )

        password_field = None
        for selectors in [
            [(By.ID, "Frm_Password"), (By.NAME, "Frm_Password")],
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
        target_url = f"http://{str(new_ip).strip()}"
        end_time = time.time() + timeout_s
        last_error: Optional[Exception] = None

        login_selectors=[
            (By.ID, "Frm_Username"),
            (By.NAME, "Frm_Username"),
            (By.ID, "username"),
            (By.NAME, "username"),
            (By.ID, "user"),
            (By.NAME, "user"),
            (By.ID, "user_name"),
            (By.NAME, "user_name"),
            (By.CSS_SELECTOR, "input[type='text']"),
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

                if str(new_ip).strip().lower() in current_url:
                    try:
                        self.find_element_anywhere(
                            selectors=login_selectors,
                            desc="pantalla de login ZTE en nueva IP",
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
                            desc="pantalla de login ZTE en nueva IP",
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
                        desc="pantalla de login ZTE en nueva IP",
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
            f"No fue posible acceder al login ZTE en la nueva IP '{new_ip}': {last_error}"
        )

    # Método para asegurar que etamos logueados, esperando a que la sesión esté lista
    def ensure_logged_in(self) -> None:
        self.wait_session_ready()

    # Helper para esperar a que la sesión esté lista comprobando la aparición de elementos del menú principal o la ausencia del botón de login
    def wait_session_ready(self, timeout_s: Optional[int] = None) -> None:
        timeout = timeout_s or self.timeout_s
        end_time = time.time() + timeout

        while time.time() < end_time:
            self._switch_to_default()

            # Si ya aparece el menú principal, damos por válida la sesión
            menu_selectors = [
                (By.ID, "localnet"),
                (By.ID, "internet"),
                (By.ID, "homePage"),
                (By.ID, "statusMgr"),
                (By.ID, "wlanConfig"),
            ]

            for by, sel in menu_selectors:
                try:
                    el = self.driver.find_element(by, sel)
                    if el is not None:
                        return
                except Exception:
                    continue

            # Si seguimos viendo el botón de login, todavía no entra
            time.sleep(0.25)

        raise RuntimeError("No fue posible confirmar sesión activa en ZTE")

    # Helper para aceptar posibles alertas de Chrome al cambiar el SSID o password WiFi
    def _maybe_accept_alert(self, timeout_s: int = 1) -> None:
        try:
            alert = WebDriverWait(self.driver, timeout_s).until(EC.alert_is_present())
            alert.accept()
            time.sleep(0.2)
        except Exception:
            pass

            # Helper para obtener los selectores del botón Logout
    
    # Helper para obtener los selectores del botón Logout en la GUI de ZTE, usado para validar que el login de verificación fue exitoso
    def _logout_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "LogOffLnk"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Logout')]"),
            (By.XPATH, "//*[contains(normalize-space(.), 'Log out')]"),
        ]
    
    # Método para cerrar sesión y validar login con nuevas credenciales
    def logout(self) -> None:
        try:
            logout_btn = self.find_element_anywhere(
                selectors=[
                    (By.ID, "logOff"),
                    (By.XPATH, "//*[@id='logOff']"),
                    (By.ID, "LogOffLnk"),
                    (By.XPATH, "//*[@id='LogOffLnk']"),
                ],
                desc="Logout",
                timeout_s=5,
                must_be_displayed=False,
            )

            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                    logout_btn,
                )
            except Exception:
                pass

            try:
                logout_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", logout_btn)

            time.sleep(1.5)

        except Exception:
            # Si no aparece logout, intentamos volver a la raíz;
            # no levantamos excepción para no romper la validación.
            self._open_root()
            time.sleep(1.5)
    # ==========================================================
    # Helpers para configuración de SSID y password WiFi
    # ==========================================================
    # Helper para navegar a la configuración de los SSID y abrir la sección del SSID indicado para luego leer o modificar sus campos
    def _open_wifi_ssid(self, ssid_index: int) -> WebElement:
        """
        Navega a WLAN SSID Configuration y abre el SSID indicado.

        Ejemplos:
            _open_wifi_ssid(0) -> SSID1 (2.4GHz)
            _open_wifi_ssid(3) -> SSID5 (5GHz)
        """
        # Llamar al helper de navegación a la página de SSID si no parece que ya estemos ahí
        if not self._is_on_wifi_ssid_page():
            self._ensure_wifi_ssid_page()
        
        # Llamar al helper de apertura del toggle de la banda WiFi para asegurar que los campos estén accesibles
        self._ensure_ssid_section_open(ssid_index)

        # Verificar que el campo password de la banda ya exista en DOM
        password_el = self.find_element_anywhere(
            selectors=self._password_field_selectors(ssid_index),
            desc=f"campo password index={ssid_index}",
            timeout_s=5,
            must_be_displayed=False,
        )

        return password_el # Retornar el campo password como indicador de que ya estamos en la sección correcta y se hizo click para aplicar cambios

    # Helper para verificar si ya estamos en la página de configuración de SSID sin navegar desde la raíz
    def _is_on_wifi_ssid_page(self) -> bool:
        """
        Verifica si ya estamos en la pantalla WLAN SSID Configuration
        sin volver a navegar desde la raíz.
        """
        try:
            self._switch_to_default()

            markers = [
                (By.ID, "WLANSSIDConfBar"),
                (By.ID, "instName_WLANSSIDConf:0"),
            ]

            for by, value in markers:
                try:
                    el = self.driver.find_element(by, value)
                    if el is not None:
                        return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    # Helper para navegar a la configuración de los SSID y sus contraseñas
    def _ensure_wifi_ssid_page(self) -> None:
        """
        Navega hasta la página WLAN SSID Configuration.
        Se puede llamar varias veces sin problema.
        """

        #self._open_root()

        # 1) Menú superior: Local Network
        self.click_anywhere(
            selectors=[
                (By.ID, "localnet"),
                (By.XPATH, "//*[@id='localnet' or @menupage='localNetStatus']"),
            ],
            desc="Local Network",
            timeout_s=10,
        )

        # 2) Submenú: WLAN
        self.click_anywhere(
            selectors=[
                (By.ID, "wlanConfig"),
                (By.XPATH, "//*[@id='wlanConfig' or @menupage='wlanBasic']"),
            ],
            desc="WLAN",
            timeout_s=10,
        )

        # 3) H1 desplegable: WLAN SSID Configuration
        self.click_anywhere(
            selectors=[
                (By.ID, "WLANSSIDConfBar"),
                (By.XPATH, "//*[@id='WLANSSIDConfBar']"),
            ],
            desc="WLAN SSID Configuration",
        )

        # 4) Esperar primer SSID
        self.find_element_anywhere(
            selectors=[
                (By.ID, "instName_WLANSSIDConf:0"),
                (By.XPATH, "//*[@id='instName_WLANSSIDConf:0']"),
            ],
            desc="instancia SSID1 2.4GHz",
            timeout_s=8,
            must_be_displayed=False,
        )

    # Helper para expandir la sección de un SSID (2.4 o 5 GHz) para mostrar sus campos
    def _open_ssid_section(self, section_index: int) -> WebElement:
        """
        Expande la sección colapsable de un SSID en la vista WLAN SSID Configuration.

        Ejemplos:
        0 -> SSID1 (2.4GHz)
        3 -> SSID5 (5GHz)
        """
        return self.click_anywhere(
            selectors=[
                (By.ID, f"instName_WLANSSIDConf:{section_index}"),
                (By.XPATH, f"//*[@id='instName_WLANSSIDConf:{section_index}']"),
                (
                    By.XPATH,
                    f"//a[@id='instName_WLANSSIDConf:{section_index}' and contains(@class,'collapsibleInst')]",
                ),
            ],
            desc=f"sección SSID index={section_index}",
            timeout_s=8,
        )

    # Helper para asegurar que la sección de un SSID esté expandida para luego interactuar con sus campos. No vuelve a hacer click si ya parece que están accesibles
    def _ensure_ssid_section_open(self, section_index: int) -> WebElement:
        """
        Asegura que la sección del SSID esté expandida.
        Si ya está abierta, no vuelve a hacer click.
        """
        try:
            return self.find_element_anywhere(
                selectors=self._ssid_field_selectors(section_index),
                desc=f"campo SSID index={section_index} ya visible",
                timeout_s=1,
                must_be_displayed=True,
            )
        except Exception:
            pass

        self._open_ssid_section(section_index)

        return self.find_element_anywhere(
            selectors=self._ssid_field_selectors(section_index),
            desc=f"campo SSID index={section_index} después de expandir",
            timeout_s=5,
            must_be_displayed=True,
        )

    # Helper para aplicar cambios en un SSID (2.4 o 5 GHz) haciendo click en su botón Apply específico
    def _apply_wifi_band(self, index: int) -> WebElement:
        """
        Hace click en el botón Apply de la sección WiFi indicada.

        Ejemplos:
            0 -> Btn_apply_WLANSSIDConf:0
            3 -> Btn_apply_WLANSSIDConf:3
        """
        btn = self.find_element_anywhere(
            selectors=[
                (By.ID, f"Btn_apply_WLANSSIDConf:{index}"),
                (By.XPATH, f"//*[@id='Btn_apply_WLANSSIDConf:{index}']"),
                (By.XPATH, f"//input[@type='button' and @id='Btn_apply_WLANSSIDConf:{index}' and @value='Apply']"),
            ],
            desc=f"botón Apply WiFi index={index}",
            timeout_s=8,
            must_be_displayed=False,
        )

        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                btn,
            )
        except Exception:
            pass

        try:
            btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", btn)

        time.sleep(3) # Dejar tiempo a que la GUI aplique los cambios antes de seguir interactuando

        return btn

    # Helper principal para leer los campos SSID y devolver los valores
    def _ssid_field_selectors(self, index: int) -> Sequence[Locator]:
        return [
            (By.ID, f"ESSID:{index}"),
            (By.NAME, f"ESSID:{index}"),
            (By.CSS_SELECTOR, f"[id='ESSID:{index}']"),
            (By.XPATH, f"//*[@id='ESSID:{index}']"),
        ]

    # Helper para leer el campo de contraseña y devolver los valores
    def _password_field_selectors(self, index: int) -> Sequence[Locator]:
        return [
            (By.ID, f"KeyPassphrase:{index}"),
            (By.NAME, f"KeyPassphrase:{index}"),
            (By.CSS_SELECTOR, f"[id='KeyPassphrase:{index}']"),
            (By.XPATH, f"//*[@id='KeyPassphrase:{index}']"),
        ]

    # Helper para preparar el campo password
    def _get_password_input_ready(self, index: int) -> WebElement:
        try:
            password_el = self.find_element_anywhere(
                selectors=self._password_field_selectors(index),
                desc=f"campo password index={index}",
                timeout_s=3,
                must_be_displayed=True,
            )
        except Exception:
            self._open_ssid_section(index)
            password_el = self.find_element_anywhere(
                selectors=self._password_field_selectors(index),
                desc=f"campo password index={index}",
                timeout_s=8,
                must_be_displayed=True,
            )

        return password_el

    # ==========================================================
    # Helpers para credenciales web
    # ==========================================================
    # Método para validar que la nueva contraseña web realmente quedó aplicada
    def verify_web_password_login(self, username: str, password: str) -> None:
        self.logout()
        
        # Esperar a que cargue la pantalla de login
        time.sleep(1.5)

        # Intentar login una sola vez con las nuevas credenciales
        self._zte_login(username=username, password=password)
        self.wait_session_ready(timeout_s=10)

        # Si llegó aquí, el login fue correcto; cerrar sesión y terminar
        self.logout()
        time.sleep(1.5)

    # Helper para verificar si ya estamos en la pantalla User Account Management
    def _is_on_account_management_page(self) -> bool:
        try:
            self._switch_to_default()

            markers = [
                (By.ID, "AccountManag"),
                (By.ID, "Password:0"),
                (By.ID, "NewPassword:0"),
                (By.ID, "NewConfirmPassword:0"),
                (By.ID, "Btn_apply_AccountManag:0"),
                (By.XPATH, "//*[@id='AccountManagBar:0']"),
            ]

            for by, value in markers:
                try:
                    el = self.driver.find_element(by, value)
                    if el is not None:
                        return True
                except Exception:
                    continue

            return False
        except Exception:
            return False
        
    # Helper para navegar a Management & Diagnosis -> Account Management
    def _go_to_account_management(self) -> None:
        if self._is_on_account_management_page():
            return

        # 1) Menú superior: Management & Diagnosis
        self.click_anywhere(
            selectors=[
                (By.ID, "mgrAndDiag"),
                (By.XPATH, "//*[@id='mgrAndDiag']"),
                (By.XPATH, "//a[@title='Management & Diagnosis']"),
                (By.LINK_TEXT, "Management & Diagnosis"),
            ],
            desc="Management & Diagnosis",
            timeout_s=10,
        )

        time.sleep(1.0)

        # 2) Menú lateral: Account Management
        self.click_anywhere(
            selectors=[
                (By.ID, "accountMgr"),
                (By.XPATH, "//*[@id='accountMgr']"),
                (By.XPATH, "//a[@title='Account Management']"),
                (By.LINK_TEXT, "Account Management"),
            ],
            desc="Account Management",
            timeout_s=10,
        )

        time.sleep(1.5)

        # 3) Esperar primer campo del formulario
        self.find_element_anywhere(
            selectors=self._web_old_password_selectors(),
            desc="campo Old Password",
            timeout_s=8,
            must_be_displayed=True,
        )
    
    # Helper para obtener los selectores del campo de contraseña actual
    def _web_old_password_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "Password:0"),
            (By.NAME, "Password:0"),
            (By.CSS_SELECTOR, "[id='Password:0']"),
            (By.XPATH, "//*[@id='Password:0']"),
        ]
    
    # Helper para obtener los selectores del campo de nueva contraseña
    def _web_new_password_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "NewPassword:0"),
            (By.NAME, "NewPassword:0"),
            (By.CSS_SELECTOR, "[id='NewPassword:0']"),
            (By.XPATH, "//*[@id='NewPassword:0']"),
        ]

    # Helper para obtener los selectores del campo de confirmación de nueva contraseña
    def _web_confirm_password_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "NewConfirmPassword:0"),
            (By.NAME, "NewConfirmPassword:0"),
            (By.CSS_SELECTOR, "[id='NewConfirmPassword:0']"),
            (By.XPATH, "//*[@id='NewConfirmPassword:0']"),
        ]
    
    # Helper para obtener los selectores del botón Apply
    def _web_apply_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "Btn_apply_AccountManag:0"),
            (By.NAME, "Btn_apply_AccountManag:0"),
            (By.CSS_SELECTOR, "[id='Btn_apply_AccountManag:0']"),
            (By.XPATH, "//*[@id='Btn_apply_AccountManag:0']"),
            (
                By.XPATH,
                "//input[@type='button' and @id='Btn_apply_AccountManag:0' and @value='Apply']",
            ),
        ]

    # Método para actualizar la contraseña web del usuario root
    def update_web_password(
        self,
        old_password: str,
        new_password: str,
        confirm_password: Optional[str] = None,
    ) -> dict:
        self._go_to_account_management()

        confirm_password = new_password if confirm_password is None else confirm_password

        old_password_el = self.find_element_anywhere(
            selectors=self._web_old_password_selectors(),
            desc="campo Old Password",
            timeout_s=8,
            must_be_displayed=True,
        )

        new_password_el = self.find_element_anywhere(
            selectors=self._web_new_password_selectors(),
            desc="campo New Password",
            timeout_s=8,
            must_be_displayed=True,
        )

        confirm_password_el = self.find_element_anywhere(
            selectors=self._web_confirm_password_selectors(),
            desc="campo Confirmed Password",
            timeout_s=8,
            must_be_displayed=True,
        )

        self._set_input_value(old_password_el, old_password)
        self._set_input_value(new_password_el, new_password)
        self._set_input_value(confirm_password_el, confirm_password)

        apply_btn = self.find_element_anywhere(
            selectors=self._web_apply_button_selectors(),
            desc="botón Apply Account Management",
            timeout_s=8,
            must_be_displayed=False,
        )

        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                apply_btn,
            )
        except Exception:
            pass

        try:
            apply_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", apply_btn)

        # Igual que en WiFi: dejar tiempo a que la GUI aplique
        time.sleep(3)

        # return {
        #     "username": "root",
        #     "old_password_used": bool(old_password),
        #     "new_password_set": bool(new_password),
        # }
        return {
            "username": "root",
            "old_password_length": len(old_password or ""),
            "new_password_length": len(new_password or ""),
            "confirm_password_length": len(confirm_password or ""),
        }

    # ===================================================================
    # Métodos de utilidad para el orquestador
    # ===================================================================

    # Método para *SOLO LEER* los campos SSID y contraseña de una banda WiFi (2.4 o 5 GHz) y devolverlos en un dict
    def read_wifi_band(self, index: int) -> dict:
        self._open_wifi_ssid(index)

        ssid_el = self.find_element_anywhere(
            selectors=self._ssid_field_selectors(index),
            desc=f"campo SSID index={index}",
            timeout_s=8,
            must_be_displayed=True,
        )

        password_el = self._get_password_input_ready(index)

        ssid_value = self._get_input_value(ssid_el)
        password_value = self._get_input_value(password_el)

        band = "2.4GHz" if index == 0 else "5GHz" if index == 3 else f"index_{index}"

        return {
            "index": index,
            "band": band,
            "ssid": ssid_value,
            "password": password_value,
        }

    # Método SOLO PARA MODIFICAR Y APLICAR cambios en los campos SSID y contraseña de una banda WiFi
    def update_wifi_band(
        self,
        index: int,
        ssid: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict:
        current = self.read_wifi_band(index=index)

        if ssid is not None:
            ssid_el = self.find_element_anywhere(
                selectors=self._ssid_field_selectors(index),
                desc=f"campo SSID index={index}",
                timeout_s=8,
                must_be_displayed=True,
            )
            self._set_input_value(ssid_el, ssid)

        if password is not None:
            password_el = self._get_password_input_ready(index)
            self._set_input_value(password_el, password)

        self._apply_wifi_band(index)

        updated = self.read_wifi_band(index=index)

        return {
            "before": current,
            "after": updated,
        }
    
    # Método para hacer click en el botón Save general de la sección WLAN para aplicar los cambios
    def save_wifi(self) -> None:
        save_button = self.find_element_anywhere(
            selectors=[
                (By.ID, "Btn_apply"),
                (By.ID, "btnApply"),
                (By.NAME, "Btn_apply"),
                (By.CSS_SELECTOR, "input[value='Apply']"),
                (By.CSS_SELECTOR, "input[value='Save']"),
                (By.XPATH, "//input[@type='button' and (@value='Apply' or @value='Save')]"),
                (By.XPATH, "//button[contains(normalize-space(.),'Apply') or contains(normalize-space(.),'Save')]"),
            ],
            desc="botón Apply/Save WLAN",
            timeout_s=8,
            must_be_displayed=False,
        )

        try:
            self.driver.execute_script("arguments[0].click();", save_button)
        except Exception:
            save_button.click()

        time.sleep(3)

        # ==========================================================
    
    # ==========================================================
    # IP (Gateway)
    # ==========================================================
    # Helper para obtener los selectores del menú Local Network
    def _local_network_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "localnet"),
        ]

    # Helper para obtener los selectores del submenú
    def _lan_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "lanConfig"),
        ]

    # Helper para obtener los selectores del toggle DHCP Server
    def _dhcp_toggle_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "DHCPBasicCfgBar"),
        ]

    # Helper para obtener los selectores del campo del primer octeto de la IP
    def _ip_field1_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "sub_IPAddr0:DHCPBasicCfg"),
            (By.NAME, "sub_IPAddr0:DHCPBasicCfg"),
            (By.CSS_SELECTOR, "input[id='sub_IPAddr0:DHCPBasicCfg']"),
            (By.XPATH, "//*[@id='sub_IPAddr0:DHCPBasicCfg']"),
        ]
    
    # Helper para obtener los selectores del campo del segundo octeto de la IP
    def _ip_field2_selectors(self) -> Sequence[Locator]:
            return [
            (By.ID, "sub_IPAddr1:DHCPBasicCfg"),
            (By.NAME, "sub_IPAddr1:DHCPBasicCfg"),
            (By.CSS_SELECTOR, "input[id='sub_IPAddr1:DHCPBasicCfg']"),
            (By.XPATH, "//*[@id='sub_IPAddr1:DHCPBasicCfg']"),
        ]

    # Helper para obtener los selectores del campo del tercer octeto de la IP
    def _ip_field3_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "sub_IPAddr2:DHCPBasicCfg"),
            (By.NAME, "sub_IPAddr2:DHCPBasicCfg"),
            (By.CSS_SELECTOR, "input[id='sub_IPAddr2:DHCPBasicCfg']"),
            (By.XPATH, "//*[@id='sub_IPAddr2:DHCPBasicCfg']"),
        ]

    # Helper para obtener los selectores del campo del último octeto de la IP
    def _ip_field4_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "sub_IPAddr3:DHCPBasicCfg"),
            (By.NAME, "sub_IPAddr3:DHCPBasicCfg"),
            (By.CSS_SELECTOR, "input[id='sub_IPAddr3:DHCPBasicCfg']"),
            (By.XPATH, "//*[@id='sub_IPAddr3:DHCPBasicCfg']"),
        ]

    # Helper para obtener los selectores del botón Apply/Save en la sección IP
    def _apply_ip_button_selectors(self) -> Sequence[Locator]:
        return [
            (By.ID, "Btn_apply_DHCPBasicCfg"),
        ]

    # Método para ir a la sección de configuración IP/LAN del equipo
    def _go_to_ip_configuration(self) -> None:
        try: # 0) Si ya estamos en la pantalla y el primer octeto ya existe, no navegar de nuevo
            self.find_element_anywhere(
                selectors=self._ip_field1_selectors(),
                desc="campo 1 IP ZTE ya visible",
                timeout_s=1,
                must_be_displayed=False,
            )
            return
        except Exception: # No estamos aún en la sección de configuración LAN
            pass
        
        # 1) Si ya estamos en LAN pero la sección DHCP Server no está expandida, expandirla
        try:
            self.find_element_anywhere(
                selectors=self._dhcp_toggle_selectors(),
                desc="barra DHCP Server ZTE",
                timeout_s=1,
                must_be_displayed=False,
            )

            self.click_anywhere(
                selectors=self._dhcp_toggle_selectors(),
                desc="menú DHCP Server ZTE",
                timeout_s=6,
            )

            self.find_element_anywhere(
                selectors=[(By.ID, "template_DHCPBasicCfg")],
                desc="template DHCPBasicCfg ZTE",
                timeout_s=10,
                must_be_displayed=False,
            )

            self.find_element_anywhere(
                selectors=self._ip_field1_selectors(),
                desc="campo 1 IP ZTE",
                timeout_s=10,
                must_be_displayed=False,
            )
            return
        except Exception:
            pass

        # 2) Navegación normal desde el menú principal
        self._ensure_main_page()

        self.click_anywhere( # 3) Menú Local Network
            selectors=self._local_network_selectors(),
            desc="menú Local Network ZTE",
            timeout_s=8,
        )

        self.click_anywhere( # 4) LAN
            selectors=self._lan_selectors(),
            desc="menú LAN ZTE",
            timeout_s=8,
        )

        self.click_anywhere( # 5) DHCP Server
            selectors=self._dhcp_toggle_selectors(),
            desc="menú DHCP Server ZTE",
            timeout_s=8,
        )

        self.find_element_anywhere( # 6) Verificar encontrando el template de DHCP Basic Config para asegurarnos de que se cargó la sección
            selectors=[(By.ID, "template_DHCPBasicCfg")],
            desc="template DHCPBasicCfg ZTE",
            timeout_s=10,
            must_be_displayed=False,
        )

        self.find_element_anywhere( # 7) Verificar encontrando el input con la IP actual
            selectors=self._ip_field1_selectors(),
            desc=f"campo 1 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )

    # Método para leer la configuración actual de LAN
    def read_ip_configuration(self) -> dict:
        self._go_to_ip_configuration()

        ip_field1 = self.find_element_anywhere(
            selectors=self._ip_field1_selectors(),
            desc="campo 1 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )

        ip_field2 = self.find_element_anywhere(
            selectors=self._ip_field2_selectors(),
            desc="campo 2 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )

        ip_field3 = self.find_element_anywhere(
            selectors=self._ip_field3_selectors(),
            desc="campo 3 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )

        ip_field4 = self.find_element_anywhere(
            selectors=self._ip_field4_selectors(),
            desc="campo 4 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )

        ip_full = f"{self._get_input_value(ip_field1)}.{self._get_input_value(ip_field2)}.{self._get_input_value(ip_field3)}.{self._get_input_value(ip_field4)}"

        return {
            "ip": ip_full,
        }

    # Método para actualizar la IP/LAN del equipo
    def update_ip_configuration(self, new_ip: str) -> dict:
        self._go_to_ip_configuration() # 1) Ir a la sección de LAN Settings

        if not new_ip or not str(new_ip).strip():
            raise RuntimeError("No se recibió nueva IP para ZTE")

        new_ip = str(new_ip).strip()

        ip_field1 = self.find_element_anywhere( # 2a) Buscar campo primer octeto
            selectors=self._ip_field1_selectors(),
            desc="campo 1 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )
        ip_field2 = self.find_element_anywhere( # 2b) Buscar campo segundo octeto
            selectors=self._ip_field2_selectors(),
            desc="campo 2 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )
        ip_field3 = self.find_element_anywhere( # 2c) Buscar campo tercer octeto
            selectors=self._ip_field3_selectors(),
            desc="campo 3 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )
        ip_field4 = self.find_element_anywhere( # 2d) Buscar campo cuarto octeto
            selectors=self._ip_field4_selectors(),
            desc="campo 4 IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )

        ip_full_before = f"{self._get_input_value(ip_field1)}.{self._get_input_value(ip_field2)}.{self._get_input_value(ip_field3)}.{self._get_input_value(ip_field4)}"

        before = { # 3) Guardar valor de IP antes de modificar para devolver al final
            "ip": ip_full_before,
        }

        self._set_input_value(ip_field1, new_ip.split('.')[0]) # 4a) Actualizar campo IP con nueva IP
        self._set_input_value(ip_field2, new_ip.split('.')[1]) # 4b) Actualizar campo IP con nueva IP
        self._set_input_value(ip_field3, new_ip.split('.')[2]) # 4c) Actualizar campo IP con nueva IP
        self._set_input_value(ip_field4, new_ip.split('.')[3]) # 4d) Actualizar campo IP con nueva IP

        apply_btn = self.find_element_anywhere( # 5) Buscar botón Apply (espera de 32 segundos en el adapter)
            selectors=self._apply_ip_button_selectors(),
            desc="botón Apply IP ZTE",
            timeout_s=6,
            must_be_displayed=False,
        )
        try:
            apply_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", apply_btn)

        self._maybe_accept_alert(timeout_s=2)

        return { # 6) Devolver valores antes y después del cambio
            "before": before,
            "after": {
                "ip": new_ip,
            },
        }
    