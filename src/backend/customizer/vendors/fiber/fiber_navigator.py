# ===================================================================
# Imports
# ===================================================================
import time
from collections import deque
from typing import Dict, List, Tuple, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ...models import WifiBand

# ===================================================================
# Clase y métodos específicos para Fiber
# ===================================================================
Locator = Tuple[str, str]

# Class para manejar la navegación y acciones específicas en el panel de Fiber
class FiberhomeNavigator:
    """
    Nota importante:
      - FiberHome suele usar frames/iframes (multi-nivel).
      - Por eso este navigator incluye busqueda BFS por frames, similar a fiber_mixin.py.
    """

    # Constructor con la URL base del dispositivo
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"

    # -------------------------
    # Helpers: frames (multi-level)
    # -------------------------
    # Helper para cambiar a un frame dado un path (lista de indices)
    def _switch_path(self, driver: WebDriver, path: List[int]) -> bool:
        driver.switch_to.default_content()
        for idx in path:
            frames = driver.find_elements(By.CSS_SELECTOR, "frame,iframe")
            if idx >= len(frames):
                return False
            driver.switch_to.frame(frames[idx])
        return True

    # Helper para buscar elemento en default_content y en TODOS los frames/iframes multi-nivel.
    def _find_element_anywhere(
        self,
        driver: WebDriver,
        by: str,
        sel: str,
        timeout_s: int = 10,
        max_depth: int = 8,
        require_displayed: bool = False,
    ):
        """
        Busca elemento en default_content y en TODOS los frames/iframes multi-nivel.
        Deja el driver en el frame donde se encontro (importante para interactuar después).
        """
        end = time.time() + timeout_s
        last_err = None

        while time.time() < end:
            try:
                q = deque([[]])
                visited = set()

                while q:
                    path = q.popleft()
                    tpath = tuple(path)
                    if tpath in visited:
                        continue
                    visited.add(tpath)

                    if not self._switch_path(driver, path):
                        continue

                    els = driver.find_elements(by, sel)
                    if els:
                        el = els[0]
                        if require_displayed and not el.is_displayed():
                            pass
                        else:
                            return el

                    if len(path) < max_depth:
                        frames = driver.find_elements(By.CSS_SELECTOR, "frame,iframe")
                        for i in range(len(frames)):
                            q.append(path + [i])

            except Exception as e:
                last_err = e

            time.sleep(0.25)

        raise RuntimeError(f"FiberHome: element not found: {by}='{sel}' (last_err={last_err})")

    #Helper para hacer click en un elemento localizado con _find_element_anywhere
    def _click_anywhere(self, driver: WebDriver, locators: List[Locator], desc: str, timeout_s: int = 10) -> None:
        last = None
        for _ in range(max(1, int(timeout_s * 3))):
            for by, sel in locators:
                try:
                    el = self._find_element_anywhere(driver, by, sel, timeout_s=1, max_depth=8, require_displayed=False)
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    except Exception:
                        pass
                    try:
                        driver.execute_script("arguments[0].click();", el)
                    except Exception:
                        el.click()
                    return
                except Exception as e:
                    last = e
            time.sleep(0.25)

        raise RuntimeError(f"FiberHome: could not click '{desc}'. last_err={last}")

    def _maybe_accept_alert(self, driver: WebDriver, timeout_s: int = 2) -> bool:
        try:
            WebDriverWait(driver, timeout_s).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert.accept()
            return True
        except Exception:
            return False
        
    # Helper para cambiar a la pestaña de configuración WLAN Security si es necesario
    def _select_band_if_needed(self, driver: WebDriver, band: WifiBand) -> None:
        """
        En FiberHome, la pagina de WLAN Security a veces muestra 2.4 y 5 con:
          - un dropdown (IDs comunes ya vistos en tu tester)
          - tabs de 5G
        Esta funcion intenta cambiar a 5G cuando band == B5.
        """
        if band != WifiBand.B5:
            return

        # Metodo 1: dropdown/selector de banda
        selector_ids = ["WlanIndex", "ssid_mode", "wlan_mode", "wifi_index", "band_select", "SSID_Index"]
        for sel_id in selector_ids:
            try:
                selector = self._find_element_anywhere(driver, By.ID, sel_id, timeout_s=1, max_depth=8)
                if selector.tag_name.lower() == "select":
                    options = selector.find_elements(By.TAG_NAME, "option")
                    for opt in options:
                        txt = (opt.text or "").lower()
                        val = (opt.get_attribute("value") or "").lower()
                        if ("5g" in txt) or ("5ghz" in txt) or (val in ["1", "wlan1", "ssid1"]):
                            opt.click()
                            time.sleep(1.5)
                            return
            except Exception:
                continue

        # Metodo 2: tabs
        tab_ids = ["5g_tab", "wifi_5g", "wlan_5g", "wireless_5g", "tab_5g", "ssid1_tab"]
        for tab_id in tab_ids:
            try:
                tab = self._find_element_anywhere(driver, By.ID, tab_id, timeout_s=1, max_depth=8)
                try:
                    driver.execute_script("arguments[0].click();", tab)
                except Exception:
                    tab.click()
                time.sleep(1.5)
                return
            except Exception:
                continue

    # -------------------------
    # API pública
    # -------------------------
    # Método para abrir la página de inicio del dispositivo
    def open_home(self, driver: WebDriver) -> None:
        driver.switch_to.default_content()
        driver.get(f"{self.base_url}html/login_inter.html")

    # Método para loguearse con Selenium (debe lanzar RuntimeError si falla)
    def login(self, driver: WebDriver, username: str, password: str, timeout_s: int = 12) -> None:
        """
        Responsabilidad:
          - Loguearse con Selenium.
          - Si hay sesion activa (busy), debe fallar con excepcion para que UI lo muestre.

        Logica (basada en fiber_mixin.py):
          1) Esperar campo user_name
          2) password en loginpp (fallback password)
          3) click login_btn (fallback login/LoginId)
          4) aceptar alert si aparece
          5) validar que ya no estas en login_inter.html
        """
        driver.switch_to.default_content()
        WebDriverWait(driver, timeout_s).until(EC.presence_of_element_located((By.ID, "user_name")))

        u = driver.find_element(By.ID, "user_name")
        u.clear()
        u.send_keys(username)

        try:
            p = driver.find_element(By.ID, "loginpp")
        except Exception:
            p = driver.find_element(By.ID, "password")

        p.clear()
        p.send_keys(password)

        btn = None
        for bid in ["login_btn", "login", "LoginId"]:
            try:
                btn = driver.find_element(By.ID, bid)
                break
            except Exception:
                continue
        if not btn:
            raise RuntimeError("FiberHome login: login button not found")

        btn.click()
        self._maybe_accept_alert(driver, timeout_s=2)

        time.sleep(2.0)
        cur = (driver.current_url or "")
        if "login_inter.html" in cur:
            html = (driver.page_source or "").lower()
            if "already" in html or "logged" in html:
                raise RuntimeError("FiberHome login: session busy (already logged in)")
            raise RuntimeError("FiberHome login: still on login page (bad credentials or UI changed)")

        # Opcional: fuerza la UI principal
        try:
            driver.get(f"{self.base_url}html/main_inter.html")
            time.sleep(1.0)
        except Exception:
            pass

    # Método para asegurar que estamos logeados
    def ensure_logged_in(self, driver: WebDriver, timeout_s: int = 12) -> None:
        try:
            _ = self._find_element_anywhere(driver, By.ID, "first_menu_network", timeout_s=timeout_s, max_depth=8)
            return
        except Exception:
            pass

        try:
            _ = self._find_element_anywhere(driver, By.ID, "first_menu_manage", timeout_s=timeout_s, max_depth=8)
            return
        except Exception:
            pass

        raise RuntimeError("FiberHome login: menú no detectado (no está listo)")
    
    # Método para navegar a la configuración básica de WiFi (SSID/PSK)
    def go_to_wifi_basic(self, driver: WebDriver, band: WifiBand) -> None:
        """
        Responsabilidad:
          - Llegar a la pantalla donde se configura WiFi (SSID/PSK) para la banda.

        Logica concreta (tomada de tu metodo _extract_wifi_password_selenium):
          1) GET main_inter.html
          2) Click menu Network: first_menu_network
          3) Click WLAN Security: thr_security
          4) Si band==5G, intentar selector/tab para 5G
          5) Esperar campo PreSharedKey (indica que el panel cargo)
        """
        driver.switch_to.default_content()
        driver.get(f"{self.base_url}html/main_inter.html")
        time.sleep(1.0)

        self._click_anywhere(driver, [(By.ID, "first_menu_network")], "Network menu", timeout_s=12)
        time.sleep(0.5)

        self._click_anywhere(driver, [(By.ID, "thr_security")], "WLAN Security", timeout_s=12)
        time.sleep(1.0)

        self._select_band_if_needed(driver, band)

        # Esperar campo PreSharedKey
        _ = self._find_element_anywhere(driver, By.ID, "PreSharedKey", timeout_s=12, max_depth=8)

    # Método para setear SSID/PSK en la configuración básica de WiFi
    def set_wifi_basic(self, driver: WebDriver, band: WifiBand, ssid: str, password: str) -> None:
        """
        Responsabilidad:
          - Asume que YA estas en WLAN Security (band correcto).
          - Setear SSID/password y aplicar.

        Lo que SI sabemos por tu tester:
          - Password esta en input id=PreSharedKey
          - A veces viene "protegido" por class; en tu tester lo remueves:
              removeAttribute('class')

        Lo que falta definir en tu DOM real:
          - ID exacto del campo SSID (si esta en esta misma pantalla)
          - ID exacto del boton Apply/Save

        Por eso dejo candidates y TU sustituyes con el locator real del tester cuando lo pegues.
        """
        # asegurar banda (por si UI volvio a 2.4 al recargar)
        self._select_band_if_needed(driver, band)

        # SSID (no confirmado en tu fiber_mixin, candidates)
        if ssid:
            ssid_candidates: List[Locator] = [
                (By.ID, "SSID"),
                (By.ID, "Ssid"),
                (By.ID, "wifi_ssid"),
                (By.ID, "WlanSsid"),
                (By.CSS_SELECTOR, "input[id*='ssid' i]"),
                (By.CSS_SELECTOR, "input[name*='ssid' i]"),
            ]
            ssid_el = None
            last = None
            for by, sel in ssid_candidates:
                try:
                    ssid_el = self._find_element_anywhere(driver, by, sel, timeout_s=2, max_depth=8)
                    break
                except Exception as e:
                    last = e
            if not ssid_el:
                raise RuntimeError(f"FiberHome WiFi: SSID field not found (set correct locator). last_err={last}")

            ssid_el.clear()
            ssid_el.send_keys(ssid)

        # Password (confirmado)
        if password:
            psk = self._find_element_anywhere(driver, By.ID, "PreSharedKey", timeout_s=6, max_depth=8)
            try:
                driver.execute_script("arguments[0].removeAttribute('class');", psk)
            except Exception:
                pass
            psk.clear()
            psk.send_keys(password)

        # Apply/Save (no confirmado en tu fiber_mixin para WiFi; candidates)
        apply_candidates: List[Locator] = [
            (By.ID, "apply"),
            (By.ID, "Apply_button"),
            (By.ID, "save"),
            (By.ID, "Save_button"),
            (By.CSS_SELECTOR, "input[type='button'][value*='Apply']"),
            (By.CSS_SELECTOR, "input[type='button'][value*='Save']"),
            (By.XPATH, "//button[contains(.,'Apply') or contains(.,'Save')]"),
        ]
        btn = None
        last = None
        for by, sel in apply_candidates:
            try:
                btn = self._find_element_anywhere(driver, by, sel, timeout_s=2, max_depth=8)
                break
            except Exception as e:
                last = e
        if not btn:
            raise RuntimeError(f"FiberHome WiFi: Apply/Save button not found (set correct locator). last_err={last}")

        try:
            driver.execute_script("arguments[0].click();", btn)
        except Exception:
            btn.click()

        self._maybe_accept_alert(driver, timeout_s=2)

    # Método para navegar a la pantalla de cambio de credenciales web (admin/user)
    def go_to_web_credentials(self, driver: WebDriver) -> None:
        """
        Responsabilidad:
          - Navegar a pantalla de cambio de credenciales web (admin/user).

        FiberHome normalmente esta bajo Management, pero tu fiber_mixin no trae esa ruta lista.
        Cuando tengas el fragmento probado, lo pegas aqui.
        """
        raise NotImplementedError("FiberHome: implement go_to_web_credentials with tested navigation")

    # Método para setear nuevas credenciales web (admin/user)
    def set_web_credentials(self, driver: WebDriver, new_user: str, new_pass: str) -> None:
        """
        Responsabilidad:
          - Asume que YA estas en pantalla de credenciales.
          - Setea user/pass y aplica.
        """
        raise NotImplementedError("FiberHome: implement set_web_credentials with tested selectors")