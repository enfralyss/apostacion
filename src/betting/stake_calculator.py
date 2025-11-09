"""
Stake Calculator - Calcula el tamaño óptimo de apuesta usando Kelly Criterion
"""

from typing import Dict
from loguru import logger
import yaml


class StakeCalculator:
    """Calculador de tamaño de apuesta óptimo"""

    def __init__(self, config_path: str = "config/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.bankroll_config = self.config['bankroll']

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
        Calcula el monto a apostar usando Kelly Criterion fraccionado

        Args:
            probability: Probabilidad de ganar
            odds: Cuota decimal
            bankroll: Bankroll actual

        Returns:
            Monto a apostar en unidades monetarias
        """
        # Kelly completo
        full_kelly = self.kelly_criterion(probability, odds)

        if full_kelly <= 0:
            return 0

        # Aplicar fracción de Kelly (conservative Kelly)
        kelly_fraction = self.bankroll_config['kelly_fraction']
        fractional_kelly = full_kelly * kelly_fraction

        # Calcular stake
        stake = bankroll * fractional_kelly

        # Aplicar límites
        max_stake = bankroll * (self.bankroll_config['max_bet_percentage'] / 100)
        stake = min(stake, max_stake)

        # Redondear a 2 decimales
        stake = round(stake, 2)

        logger.debug(f"Kelly calculation: probability={probability:.2%}, odds={odds:.2f}, "
                    f"full_kelly={full_kelly:.2%}, fractional_kelly={fractional_kelly:.2%}, "
                    f"stake=${stake:.2f}")

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

    def validate_stake(self, stake: float, bankroll: float) -> Dict:
        """
        Valida que el stake cumpla con las reglas de gestión de bankroll

        Args:
            stake: Monto propuesto a apostar
            bankroll: Bankroll actual

        Returns:
            Dict con resultado de validación
        """
        max_bet = bankroll * (self.bankroll_config['max_bet_percentage'] / 100)
        stake_percentage = (stake / bankroll * 100) if bankroll > 0 else 0

        validation = {
            'is_valid': True,
            'warnings': [],
            'adjusted_stake': stake
        }

        # Verificar que no exceda el máximo
        if stake > max_bet:
            validation['warnings'].append(
                f"Stake ${stake:.2f} exceeds max bet of ${max_bet:.2f} "
                f"({self.bankroll_config['max_bet_percentage']}% of bankroll)"
            )
            validation['adjusted_stake'] = max_bet

        # Verificar bankroll mínimo
        if bankroll < self.bankroll_config['min_bankroll']:
            validation['is_valid'] = False
            validation['warnings'].append(
                f"Bankroll ${bankroll:.2f} below minimum ${self.bankroll_config['min_bankroll']:.2f}"
            )

        # Verificar que quede bankroll suficiente después de apostar
        remaining_bankroll = bankroll - validation['adjusted_stake']
        if remaining_bankroll < self.bankroll_config['min_bankroll'] * 0.5:
            validation['warnings'].append(
                f"Warning: Only ${remaining_bankroll:.2f} will remain after bet"
            )

        return validation

    def calculate_recommended_stake(self, probability: float, odds: float,
                                   bankroll: float, strategy: str = "kelly") -> Dict:
        """
        Calcula el stake recomendado con validaciones completas

        Args:
            probability: Probabilidad de ganar
            odds: Cuota decimal
            bankroll: Bankroll actual
            strategy: 'kelly' o 'flat'

        Returns:
            Dict con stake recomendado y detalles
        """
        if strategy == "kelly":
            stake = self.calculate_kelly_stake(probability, odds, bankroll)
        else:  # flat
            stake = self.calculate_flat_stake(bankroll)

        # Validar stake
        validation = self.validate_stake(stake, bankroll)

        result = {
            'strategy': strategy,
            'calculated_stake': stake,
            'recommended_stake': validation['adjusted_stake'],
            'stake_percentage': (validation['adjusted_stake'] / bankroll * 100) if bankroll > 0 else 0,
            'is_valid': validation['is_valid'],
            'warnings': validation['warnings'],
            'potential_return': validation['adjusted_stake'] * odds,
            'potential_profit': validation['adjusted_stake'] * (odds - 1),
            'risk_reward_ratio': (odds - 1) if stake > 0 else 0
        }

        return result


if __name__ == "__main__":
    # Test del calculator
    calculator = StakeCalculator()

    print("=== Testing Stake Calculator ===\n")

    test_cases = [
        {"probability": 0.70, "odds": 1.85, "bankroll": 5000, "desc": "High confidence, good odds"},
        {"probability": 0.55, "odds": 2.10, "bankroll": 5000, "desc": "Medium confidence, higher odds"},
        {"probability": 0.75, "odds": 1.50, "bankroll": 5000, "desc": "Very high confidence, low odds"},
        {"probability": 0.45, "odds": 2.50, "bankroll": 5000, "desc": "Low confidence (no edge)"},
    ]

    for case in test_cases:
        print(f"\n{case['desc']}")
        print(f"Probability: {case['probability']:.0%}, Odds: {case['odds']}, Bankroll: ${case['bankroll']}")

        result = calculator.calculate_recommended_stake(
            case['probability'],
            case['odds'],
            case['bankroll'],
            strategy="kelly"
        )

        print(f"  Recommended Stake: ${result['recommended_stake']:.2f} ({result['stake_percentage']:.2f}% of bankroll)")
        print(f"  Potential Return: ${result['potential_return']:.2f}")
        print(f"  Potential Profit: ${result['potential_profit']:.2f}")

        if result['warnings']:
            print(f"  Warnings: {', '.join(result['warnings'])}")
