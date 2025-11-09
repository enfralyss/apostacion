"""
Bet Placer - Coloca apuestas automáticamente en TriunfoBet
Usa Selenium para automatizar el navegador
"""

import time
import os
from typing import List, Dict
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv

load_dotenv()


class TriunfoBetPlacer:
    """
    Automatizador de apuestas en TriunfoBet.com

    IMPORTANTE: Los selectores CSS/XPath deben ser configurados
    específicamente para TriunfoBet después de inspeccionar la página
    """

    def __init__(self, headless: bool = False, dry_run: bool = True):
        """
        Args:
            headless: Si True, navegador sin interfaz gráfica
            dry_run: Si True, NO coloca apuestas reales (modo seguro)
        """
        self.base_url = "https://www.triunfobet.com"
        self.headless = headless
        self.dry_run = dry_run
        self.driver = None
        self.is_logged_in = False

        if dry_run:
            logger.warning("🔒 DRY RUN MODE - No se colocarán apuestas reales")

    def _init_driver(self):
        """Inicializa Chrome WebDriver"""
        if self.driver is not None:
            return

        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # User agent real
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)

            # Ocultar que es automation
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("Chrome driver initialized")
        except Exception as e:
            logger.error(f"Error initializing driver: {e}")
            raise

    def login(self, username: str = None, password: str = None) -> bool:
        """
        Inicia sesión en TriunfoBet

        Args:
            username: Usuario (o usar TRIUNFOBET_USER de .env)
            password: Contraseña (o usar TRIUNFOBET_PASS de .env)

        Returns:
            True si login exitoso
        """
        username = username or os.getenv('TRIUNFOBET_USER')
        password = password or os.getenv('TRIUNFOBET_PASS')

        if not username or not password:
            logger.error("Username/password not provided")
            return False

        try:
            self._init_driver()

            logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)

            # TODO: CONFIGURAR SELECTORES ESPECÍFICOS DE TRIUNFOBET
            # Estos son ejemplos genéricos que DEBES ajustar

            # Opción 1: Si hay botón de login visible
            try:
                login_btn = self.driver.find_element(By.XPATH,
                    "//button[contains(text(), 'Login') or contains(text(), 'Iniciar') or contains(text(), 'Ingresar')]"
                )
                login_btn.click()
                time.sleep(2)
            except:
                logger.info("No login button found, trying direct form")

            # Formulario de TriunfoBet (selectores reales)
            try:
                # Selectores correctos de TriunfoBet
                username_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "login"))
                )
                password_field = self.driver.find_element(By.NAME, "password")

                username_field.clear()
                username_field.send_keys(username)

                password_field.clear()
                password_field.send_keys(password)

                # Submit
                submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                submit_btn.click()

                time.sleep(3)

                # Verificar login exitoso - buscar el nombre de usuario en el dropdown
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,
                            "//span[@class='text-theme' and contains(text(), 'VES')]"
                        ))
                    )
                    self.is_logged_in = True
                    logger.info("✓ Login successful")
                    return True
                except TimeoutException:
                    logger.error("✗ Login verification failed")
                    return False

            except Exception as e:
                logger.error(f"Error in login form: {e}")
                return False

        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False

    def place_parlay_bet(self, picks: List[Dict], stake: float) -> Dict:
        """
        Coloca una apuesta combinada (parlay)

        Args:
            picks: Lista de picks seleccionados por el modelo
            stake: Monto a apostar

        Returns:
            Dict con resultado de la operación
        """
        if not self.is_logged_in:
            logger.error("Not logged in")
            return {'success': False, 'error': 'Not logged in'}

        if self.dry_run:
            logger.warning("DRY RUN - Simulando apuesta sin ejecutar")
            return self._simulate_bet(picks, stake)

        try:
            logger.info(f"Placing parlay bet: {len(picks)} picks, stake: ${stake}")

            # Limpiar cupón anterior
            self._clear_bet_slip()

            # Agregar cada pick al cupón
            for i, pick in enumerate(picks, 1):
                logger.info(f"Adding pick {i}/{len(picks)}: {pick['home_team']} vs {pick['away_team']}")

                if not self._add_pick_to_slip(pick):
                    logger.error(f"Failed to add pick {i}")
                    return {'success': False, 'error': f'Failed to add pick {i}'}

                time.sleep(1)

            # Ingresar stake
            if not self._enter_stake(stake):
                return {'success': False, 'error': 'Failed to enter stake'}

            # Confirmar apuesta
            if not self._confirm_bet():
                return {'success': False, 'error': 'Failed to confirm bet'}

            logger.info("✓ Bet placed successfully")

            return {
                'success': True,
                'picks_count': len(picks),
                'stake': stake,
                'timestamp': time.time()
            }

        except Exception as e:
            logger.error(f"Error placing bet: {e}")
            return {'success': False, 'error': str(e)}

    def _clear_bet_slip(self):
        """Limpia el cupón de apuestas"""
        try:
            # AJUSTAR SELECTOR del botón de limpiar cupón
            clear_btn = self.driver.find_element(By.XPATH,
                "//button[contains(text(), 'Limpiar') or contains(text(), 'Clear')]"
            )
            clear_btn.click()
            time.sleep(1)
        except:
            logger.debug("No clear button found or bet slip already empty")

    def _add_pick_to_slip(self, pick: Dict) -> bool:
        """
        Agrega un pick al cupón de apuestas

        Args:
            pick: Pick con información del partido

        Returns:
            True si se agregó exitosamente
        """
        try:
            # Estrategia: Buscar el partido y hacer click en la odd

            # 1. Buscar el partido por nombres de equipos
            # AJUSTAR XPATH según estructura de TriunfoBet
            match_element = self.driver.find_element(By.XPATH,
                f"//div[contains(text(), '{pick['home_team']}') and contains(text(), '{pick['away_team']}')]"
            )

            # 2. Dentro del partido, buscar el botón de la odd correcta
            prediction = pick['prediction']  # 'home_win', 'away_win', 'draw'

            if prediction == 'home_win':
                odd_selector = ".//button[contains(@class, 'odd-home')]"  # AJUSTAR
            elif prediction == 'away_win':
                odd_selector = ".//button[contains(@class, 'odd-away')]"  # AJUSTAR
            else:  # draw
                odd_selector = ".//button[contains(@class, 'odd-draw')]"  # AJUSTAR

            odd_button = match_element.find_element(By.XPATH, odd_selector)
            odd_button.click()

            time.sleep(1)

            logger.info(f"✓ Added: {pick['home_team']} vs {pick['away_team']} - {prediction}")
            return True

        except Exception as e:
            logger.error(f"Error adding pick: {e}")
            return False

    def _enter_stake(self, stake: float) -> bool:
        """Ingresa el monto a apostar"""
        try:
            # AJUSTAR SELECTOR del input de stake
            stake_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "stake"))  # O By.ID, "stake-input"
            )

            stake_input.clear()
            stake_input.send_keys(str(stake))
            time.sleep(1)

            logger.info(f"✓ Stake entered: ${stake}")
            return True

        except Exception as e:
            logger.error(f"Error entering stake: {e}")
            return False

    def _confirm_bet(self) -> bool:
        """Confirma y coloca la apuesta"""
        try:
            # AJUSTAR SELECTOR del botón de confirmar
            confirm_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(text(), 'Confirmar') or contains(text(), 'Apostar') or contains(text(), 'Place Bet')]"
                ))
            )

            # SEGURIDAD: Verificar que realmente queremos hacer click
            logger.warning("⚠️  About to place REAL bet in 3 seconds...")
            time.sleep(3)

            confirm_btn.click()
            time.sleep(2)

            logger.info("✓ Bet confirmed")
            return True

        except Exception as e:
            logger.error(f"Error confirming bet: {e}")
            return False

    def _simulate_bet(self, picks: List[Dict], stake: float) -> Dict:
        """Simula la apuesta sin ejecutarla (dry run)"""
        logger.info("="*60)
        logger.info("DRY RUN - SIMULACIÓN DE APUESTA")
        logger.info("="*60)

        total_odds = 1.0
        for pick in picks:
            total_odds *= pick['odds']

        potential_return = stake * total_odds
        potential_profit = potential_return - stake

        logger.info(f"\nApuesta simulada:")
        logger.info(f"  Picks: {len(picks)}")
        logger.info(f"  Stake: ${stake}")
        logger.info(f"  Odds totales: {total_odds:.2f}")
        logger.info(f"  Retorno potencial: ${potential_return:.2f}")
        logger.info(f"  Ganancia potencial: ${potential_profit:.2f}")
        logger.info("\nPicks:")

        for i, pick in enumerate(picks, 1):
            logger.info(f"  {i}. {pick['home_team']} vs {pick['away_team']}")
            logger.info(f"     {pick['prediction']} @ {pick['odds']}")

        logger.info("\n" + "="*60)
        logger.info("⚠️  DRY RUN - Ninguna apuesta fue colocada")
        logger.info("="*60)

        return {
            'success': True,
            'dry_run': True,
            'picks_count': len(picks),
            'stake': stake,
            'total_odds': total_odds,
            'potential_return': potential_return
        }

    def get_balance(self) -> float:
        """Obtiene el balance actual de la cuenta"""
        if not self.is_logged_in:
            return 0.0

        try:
            # Selector correcto para TriunfoBet
            balance_element = self.driver.find_element(By.XPATH,
                "//span[@class='text-theme' and contains(text(), 'VES')]"
            )

            balance_text = balance_element.text
            # Limpiar texto: "VES 3,130.25" -> 3130.25
            balance = float(
                balance_text.replace('VES', '')
                           .replace(',', '')
                           .replace('.', '')
                           .strip()
            ) / 100  # Dividir por 100 porque usa punto como separador de miles

            return balance

        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0

    def take_screenshot(self, filename: str = "screenshot.png"):
        """Toma un screenshot del navegador"""
        if self.driver:
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved: {filename}")

    def close(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Browser closed")


if __name__ == "__main__":
    # Test
    print("=== Testing TriunfoBet Bet Placer ===\n")

    placer = TriunfoBetPlacer(headless=False, dry_run=True)

    try:
        # Login
        if placer.login():
            print("✓ Login successful\n")

            # Test picks
            test_picks = [
                {
                    'home_team': 'Real Madrid',
                    'away_team': 'Barcelona',
                    'prediction': 'home_win',
                    'odds': 1.85
                },
                {
                    'home_team': 'Lakers',
                    'away_team': 'Celtics',
                    'prediction': 'away_win',
                    'odds': 2.10
                }
            ]

            # Simular apuesta
            result = placer.place_parlay_bet(test_picks, stake=100.0)
            print(f"\nResult: {result}")

        else:
            print("✗ Login failed")

    finally:
        input("\nPress Enter to close...")
        placer.close()
