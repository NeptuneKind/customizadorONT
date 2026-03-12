# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from typing import Optional
import time

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from src.backend.customizer.models import WifiBand

# ===================================================================
# Clase y métodos específicos para Huawei
# ===================================================================
# Class para manejar la navegación y acciones específicas en el panel de Huawei
class HuaweiNavigator:
    # Constructor con la URL base del dispositivo
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"

    # Método para buscar en todos los frames para Huawei (Recursiva)
    def find_element_anywhere(self, driver, by, sel, desc="", timeout=10):
        """
        Busca un elemento en el documento principal y en todos los iframes recursivamente.
        Retorna el elemento si lo encuentra, manteniendo el driver en el contexto del frame donde se encontró.
        """
        # Helper recursivo
        def search_in_frames(drv, current_depth=0):
            # 1. Buscar en el contexto actual
            try:
                el = drv.find_element(by, sel)
                if el.is_displayed():
                    return el
            except:
                pass
            
            if current_depth > 3: # Limite de profundidad para evitar loops infinitos
                return None

            # 2. Buscar en sub-frames
            frames = drv.find_elements(By.TAG_NAME, "iframe")
            # También buscar 'frame' si es un frameset
            frames.extend(drv.find_elements(By.TAG_NAME, "frame"))
            
            for i, frame in enumerate(frames):
                try:
                    drv.switch_to.frame(frame)
                    found = search_in_frames(drv, current_depth + 1)
                    if found:
                        return found
                    drv.switch_to.parent_frame()
                except:
                    try:
                        drv.switch_to.parent_frame()
                    except:
                        pass
            return None

        # Inicio de la búsqueda
        try:
            driver.switch_to.default_content()
            
            # Intentar esperar un poco si se pide timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                driver.switch_to.default_content()
                found_el = search_in_frames(driver)
                if found_el:
                    print(f"[SELENIUM] {desc} encontrado con {by}='{sel}'")
                    return found_el
                time.sleep(0.5)
                
            return None
            
        except Exception as e:
            # print(f"[DEBUG] Error buscando {desc}: {e}")
            return None

    # Método para hacer skip del wizard inicial si aparece
    def hw_maybe_skip_initial_guide(self, driver, timeout=10):
        """
        Si el wizard inicial de Huawei está presente, intenta saltarlo usando los 3 pasos específicos:
        1. guidesyscfg (Skip)
        2. guideskip (Skip)
        3. nextpage (Return to Home Page)
        """
        print("[SELENIUM] Verificando si aparece el wizard de configuración inicial (Huawei)...")
        try:
            driver.switch_to.default_content()
            
            # Definir los pasos a ejecutar en orden
            steps = [
                {"id": "guideinternet", "desc": "Exit wizard"},
                # {"id": "guidesyscfg", "desc": "Paso 1: Skip Network Config"},
                # {"id": "guideskip", "desc": "Paso 2: Skip User Config"},
                # {"id": "nextpage", "desc": "Paso 3: Return to Home Page"}
            ]
            
            wizard_found = False
            
            for step in steps:
                print(f"[SELENIUM] Buscando paso del wizard: {step['desc']} (ID: {step['id']})...")
                try:
                    # Buscar el elemento usando búsqueda recursiva en frames con find_element_anywhere
                    element = self.find_element_anywhere(
                        driver, 
                        By.ID, 
                        step["id"], 
                        desc=step["desc"],
                        timeout=5  # Aumentamos timeout a 5s para dar tiempo a cargar
                    )
                    
                    if element:
                        print(f"[SELENIUM] Wizard detectado - Ejecutando {step['desc']}...")
                        wizard_found = True
                        
                        # Hacer click
                        try:
                            element.click()
                        except:
                            driver.execute_script("arguments[0].click();", element)
                            
                        time.sleep(2) # Esperar un poco más entre pasos
                    else:
                        print(f"[SELENIUM] No se encontró el elemento {step['id']} ({step['desc']}).")
                        # Si no se encuentra, quizás ya pasamos ese paso
                        pass
                        
                except Exception as e:
                    print(f"[WARN] Error intentando ejecutar {step['desc']}: {e}")

            if wizard_found:
                print("[SELENIUM] Secuencia de salto de wizard finalizada.")
                # Asegurar que vamos a la página principal
                time.sleep(2)
                return True
            else:
                print("[INFO] No se detectó ningún paso del wizard de configuración inicial.")
                # Debug adicional: imprimir URL actual
                print(f"[DEBUG] URL actual: {driver.current_url}")
                return False

        except Exception as e:
            print(f"[WARN] Error general en hw_maybe_skip_initial_guide: {e}")
            return False

    # Método para abrir la página de inicio del dispositivo
    def open_home(self, driver: WebDriver) -> None:
        driver.switch_to.default_content()
        driver.get(self.base_url)

    # Método para realizar el login en el panel de Huawei
    def login(self, driver: WebDriver, username: str, password: str, timeout_s: int = 10) -> bool:
        # TODO: paste working selenium login logic from tester here
        # Must raise RuntimeError on failure
        raise NotImplementedError
    
    # Método para asegurar que estamos logeados
    def ensure_logged_in(self, driver: WebDriver, timeout_s: int = 10) -> None:
        # TODO: wait for a known element/menu that indicates session is ready
        raise NotImplementedError
    
    # Método para navegar a la sección de configuración básica de WiFi
    def go_to_wifi_basic(self, driver: WebDriver, band: WifiBand) -> None:
        # TODO: band B24 => go to 2.4G basic, band B5 => go to 5G basic
        raise NotImplementedError
    
    # Método para ingresar y establecer la configuración básica de WiFi (SSID y contraseña) para la banda indicada
    def set_wifi_basic(self, driver: WebDriver, band: WifiBand, ssid: str, password: str) -> None:
        # TODO: locate fields, set values, click Apply/Save
        raise NotImplementedError
    
    # Método para navegar a la sección de configuración de credenciales web (cambio de usuario/contraseña del panel)
    def go_to_web_credentials(self, driver: WebDriver) -> None:
        # TODO: navigate to account/user management page
        raise NotImplementedError
    
    # Método para ingresar y establecer la configuración de credenciales web (nuevo usuario y contraseña para el panel)
    def set_web_credentials(self, driver: WebDriver, new_user: str, new_pass: str) -> None:
        # TODO: set new credentials and apply
        raise NotImplementedError