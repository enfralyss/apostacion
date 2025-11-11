"""
Stake Calculator - Calcula el tamaño óptimo de apuesta usando Kelly Criterion MEJORADO
"""

from typing import Dict
from loguru import logger
import yaml
try:
    from src.utils.database import BettingDatabase
except Exception:
    BettingDatabase = None


class StakeCalculator:
    """Calculador de tamaño de apuesta óptimo con Kelly Criterion mejorado"""

    def __init__(self, config_path: str = "config/config.yaml"):
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.bankroll_config = self.config['bankroll']
        except:
            # Valores por defecto si no existe config
            self.bankroll_config = {
                'kelly_fraction': 0.25,
                'max_bet_percentage': 5.0
            }
        # Intentar overrides desde DB
        try:
            if BettingDatabase is not None:
                db = BettingDatabase()
                kf = db.get_parameter('kelly_fraction', None)
                mbp = db.get_parameter('max_bet_percentage', None)
                if kf is not None:
                    self.bankroll_config['kelly_fraction'] = float(kf)
                if mbp is not None:
                    self.bankroll_config['max_bet_percentage'] = float(mbp)
        except Exception as e:
            logger.debug(f"DB bankroll overrides not available: {e}")

    def kelly_criterion(self, probability: float, odds: float) -> float:
        """
        Calcula el porcentaje óptimo de bankroll a apostar usando Kelly Criterion

        Formula: f = (bp - q) / b
        Donde:
            f = fracción del bankroll a apostar
            b = odds decimales - 1 (net odds)
            p = probabilidad de ganar
            q = probabilidad de perder (1 - p)

        Args:
            probability: Probabilidad de ganar (0-1)
            odds: Cuota decimal

        Returns:
            Fracción del bankroll a apostar (0-1)
        """
        if probability <= 0 or probability >= 1:
            logger.warning(f"Invalid probability: {probability}")
            return 0

        if odds <= 1:
            logger.warning(f"Invalid odds: {odds}")
            return 0

        b = odds - 1  # Net odds
        p = probability
        q = 1 - p

        kelly_fraction = (b * p - q) / b

        # No apostar si Kelly es negativo (no hay ventaja)
        if kelly_fraction <= 0:
            logger.debug(f"Negative Kelly ({kelly_fraction:.4f}) - No bet recommended")
            return 0

        return kelly_fraction

    def calculate_kelly_stake(self, probability: float, odds: float, bankroll: float) -> float:
        """
        Calcula el monto a apostar usando Kelly Criterion fraccionado MEJORADO

        Mejoras vs versión anterior:
        - Usa 1/4 Kelly (más conservador, reduce volatilidad ~75%)
        - Cap estricto al 5% del bankroll
        - Mínimo stake de 0.5% bankroll
        - Validación de edge mínimo 2%

        Args:
            probability: Probabilidad de ganar (0-1)
            odds: Cuota decimal
            bankroll: Bankroll actual

        Returns:
            Monto a apostar en unidades monetarias
        """
        # Calcular edge primero
        edge = (probability * odds) - 1
        
        # Si edge < 2%, no apostar (demasiado pequeño para ser confiable)
        if edge < 0.02:
            logger.debug(f"Edge too small ({edge:.2%}) - No bet recommended")
            return 0

        # Kelly completo
        full_kelly = self.kelly_criterion(probability, odds)

        if full_kelly <= 0:
            return 0

        # Aplicar Kelly fraccional configurable (default 1/4)
        kelly_frac_cfg = float(self.bankroll_config.get('kelly_fraction', 0.25))
        fractional_kelly = full_kelly * kelly_frac_cfg

        # Calcular stake base
        stake = bankroll * fractional_kelly

        # CAPS DE SEGURIDAD:
        # 1. Cap máximo configurable del bankroll
        max_cap_pct = float(self.bankroll_config.get('max_bet_percentage', 5.0)) / 100.0
        max_stake = bankroll * max_cap_pct
        stake = min(stake, max_stake)

        # 2. Cap mínimo: 0.5% del bankroll (evitar apuestas demasiado pequeñas)
        min_stake = bankroll * 0.005
        if stake < min_stake and edge > 0.05:  # Solo si edge es bueno
            stake = min_stake

        # 3. Cap absoluto mínimo: 1 unidad monetaria
        stake = max(stake, 1.0)

        # Redondear a 2 decimales
        stake = round(stake, 2)

        logger.info(
            f"🎯 Kelly Stake: prob={probability:.1%}, odds={odds:.2f}, "
            f"edge={edge:.1%}, full_kelly={full_kelly:.1%}, "
            f"frac_kelly={fractional_kelly:.1%}, stake=${stake:.2f} "
            f"({stake/bankroll*100:.1f}% of bankroll)"
        )

        return stake

    def calculate_flat_stake(self, bankroll: float, percentage: float = 2.0) -> float:
        """
        Calcula stake usando estrategia flat (porcentaje fijo del bankroll)

        Args:
            bankroll: Bankroll actual
            percentage: Porcentaje del bankroll a apostar

        Returns:
            Monto a apostar
        """
        stake = bankroll * (percentage / 100)
        return round(stake, 2)

    def calculate_parlay_stake(self, picks: list, bankroll: float, 
                              strategy: str = "kelly") -> float:
        """
        Calcula stake para un parlay (combinación de picks)

        Args:
            picks: Lista de picks con sus probabilidades y odds
            bankroll: Bankroll actual
            strategy: 'kelly' o 'flat'

        Returns:
            Stake recomendado
        """
        if not picks:
            return 0

        # Calcular probabilidad combinada del parlay
        combined_prob = 1.0
        for pick in picks:
            combined_prob *= pick.get('predicted_probability', 0.5)

        # Calcular odds combinadas del parlay
        combined_odds = 1.0
        for pick in picks:
            combined_odds *= pick.get('odds', 1.5)

        if strategy == "kelly":
            return self.calculate_kelly_stake(combined_prob, combined_odds, bankroll)
        else:
            return self.calculate_flat_stake(bankroll, percentage=2.0)

    def get_stake_recommendation(self, probability: float, odds: float, 
                                bankroll: float) -> Dict:
        """
        Obtiene recomendación completa de stake con múltiples estrategias

        Args:
            probability: Probabilidad de ganar
            odds: Cuota
            bankroll: Bankroll actual

        Returns:
            Dict con recomendaciones de stake
        """
        kelly_stake = self.calculate_kelly_stake(probability, odds, bankroll)
        flat_stake = self.calculate_flat_stake(bankroll, percentage=3.0)
        
        edge = (probability * odds) - 1

        return {
            'recommended_stake': kelly_stake,  # Usar Kelly como principal
            'kelly_stake': kelly_stake,
            'flat_stake': flat_stake,
            'edge': edge,
            'edge_percentage': edge * 100,
            'kelly_percentage': (kelly_stake / bankroll * 100) if bankroll > 0 else 0,
            'strategy': 'kelly_1/4' if kelly_stake > 0 else 'no_bet'
        }


if __name__ == "__main__":
    # Test
    calc = StakeCalculator()
    
    # Ejemplo 1: Pick con buen edge
    prob = 0.65  # 65% probabilidad
    odds = 2.10  # Odds 2.10
    bankroll = 1000
    
    stake = calc.calculate_kelly_stake(prob, odds, bankroll)
    print(f"\nEjemplo 1 - Buen edge:")
    print(f"Probability: {prob:.1%}, Odds: {odds}, Bankroll: ${bankroll}")
    print(f"Stake recomendado: ${stake} ({stake/bankroll*100:.1f}% del bankroll)")
    
    # Ejemplo 2: Pick con poco edge
    prob2 = 0.52  # 52% probabilidad
    odds2 = 1.90  # Odds 1.90
    
    stake2 = calc.calculate_kelly_stake(prob2, odds2, bankroll)
    print(f"\nEjemplo 2 - Poco edge:")
    print(f"Probability: {prob2:.1%}, Odds: {odds2}, Bankroll: ${bankroll}")
    print(f"Stake recomendado: ${stake2} ({stake2/bankroll*100:.1f}% del bankroll)")
    
    # Ejemplo 3: Pick sin edge
    prob3 = 0.45  # 45% probabilidad
    odds3 = 2.00  # Odds 2.00
    
    stake3 = calc.calculate_kelly_stake(prob3, odds3, bankroll)
    print(f"\nEjemplo 3 - Sin edge:")
    print(f"Probability: {prob3:.1%}, Odds: {odds3}, Bankroll: ${bankroll}")
    print(f"Stake recomendado: ${stake3} (No apostar)")
