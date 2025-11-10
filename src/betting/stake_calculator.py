"""
Stake Calculator - Versión mejorada con Kelly fraccionado (1/4) y validaciones
"""

from typing import Dict
from loguru import logger
import yaml


class StakeCalculator:
    """Calculador de tamaño de apuesta óptimo con Kelly mejorado"""

    def __init__(self, config_path: str = "config/config.yaml"):
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.bankroll_config = self.config['bankroll']
        except Exception:
            self.bankroll_config = {
                'kelly_fraction': 0.25,
                'max_bet_percentage': 5.0,
                'min_bankroll': 1000.0
            }

    def kelly_criterion(self, probability: float, odds: float) -> float:
        if probability <= 0 or probability >= 1:
            return 0
        if odds <= 1:
            return 0
        b = odds - 1
        p = probability
        q = 1 - p
        k = (b * p - q) / b
        return k if k > 0 else 0

    def calculate_kelly_stake(self, probability: float, odds: float, bankroll: float) -> float:
        edge = (probability * odds) - 1
        if edge < 0.02:  # Edge mínimo 2%
            return 0
        full_kelly = self.kelly_criterion(probability, odds)
        if full_kelly <= 0:
            return 0
        fractional_kelly = full_kelly * 0.25  # 1/4 Kelly
        stake = bankroll * fractional_kelly
        # Cap máximo 5%
        stake = min(stake, bankroll * 0.05)
        # Cap mínimo si edge >5%
        if stake < bankroll * 0.005 and edge > 0.05:
            stake = bankroll * 0.005
        stake = max(stake, 1.0)
        stake = round(stake, 2)
        logger.info(
            f"🎯 Kelly Stake calc: prob={probability:.1%} odds={odds:.2f} edge={edge:.1%} "
            f"full={full_kelly:.1%} frac={fractional_kelly:.1%} stake=${stake:.2f} ({stake/bankroll*100:.2f}%)"
        )
        return stake

    def calculate_flat_stake(self, bankroll: float, percentage: float = 2.0) -> float:
        return round(bankroll * (percentage / 100), 2)

    def validate_stake(self, stake: float, bankroll: float) -> Dict:
        max_bet = bankroll * (self.bankroll_config.get('max_bet_percentage', 5.0) / 100)
        result = {
            'adjusted_stake': stake,
            'warnings': [],
            'is_valid': True
        }
        if stake > max_bet:
            result['warnings'].append("Stake exceeds max bet percentage; adjusted down")
            result['adjusted_stake'] = round(max_bet, 2)
        if bankroll < self.bankroll_config.get('min_bankroll', 1000.0):
            result['warnings'].append("Bankroll below minimum recommended")
        return result

    def calculate_recommended_stake(self, probability: float, odds: float, bankroll: float, strategy: str = 'kelly') -> Dict:
        stake = self.calculate_kelly_stake(probability, odds, bankroll) if strategy == 'kelly' else self.calculate_flat_stake(bankroll)
        validation = self.validate_stake(stake, bankroll)
        adjusted = validation['adjusted_stake']
        return {
            'strategy': strategy,
            'calculated_stake': stake,
            'recommended_stake': adjusted,
            'stake_percentage': (adjusted / bankroll * 100) if bankroll > 0 else 0,
            'potential_return': adjusted * odds,
            'potential_profit': adjusted * (odds - 1),
            'warnings': validation['warnings'],
            'is_valid': validation['is_valid']
        }


if __name__ == "__main__":
    calc = StakeCalculator()
    tests = [
        (0.65, 2.10, 5000),
        (0.55, 1.95, 3000),
        (0.52, 2.40, 4000),
        (0.45, 2.10, 2500)
    ]
    for p, o, b in tests:
        r = calc.calculate_recommended_stake(p, o, b, strategy='kelly')
        print(f"prob={p:.0%} odds={o} bankroll={b} stake={r['recommended_stake']} ({r['stake_percentage']:.2f}%) warnings={r['warnings']}")
