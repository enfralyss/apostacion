"""
Parlay Builder - Construye apuestas combinadas optimizadas
"""

from typing import List, Dict, Tuple
from itertools import combinations
from loguru import logger
import yaml


class ParlayBuilder:
    """Constructor de apuestas combinadas (parlays)"""

    def __init__(self, config_path: str = "config/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.parlay_config = self.config['parlay']

    def calculate_parlay_odds(self, picks: List[Dict]) -> float:
        """
        Calcula la cuota total de un parlay (multiplicando odds individuales)

        Args:
            picks: Lista de picks

        Returns:
            Cuota total del parlay
        """
        total_odds = 1.0
        for pick in picks:
            total_odds *= pick['odds']
        return total_odds

    @staticmethod
    def decimal_to_american(odds: float) -> str:
        if odds >= 2:
            return f"+{int(round((odds - 1) * 100))}"
        else:
            return f"-{int(round(100 / (odds - 1)))}"

    @staticmethod
    def expected_value(prob: float, odds: float, stake: float) -> float:
        return stake * (prob * (odds - 1) - (1 - prob))

    def correlation_factor(self, picks: List[Dict]) -> float:
        """Ajuste simple por correlación: si varias picks comparten liga o equipo.
        Penaliza exceso de correlación para no sobreestimar probabilidad combinada.
        Método heurístico MVP.
        """
        if not picks:
            return 1.0
        leagues = {}
        teams = {}
        for p in picks:
            leagues[p['league']] = leagues.get(p['league'], 0) + 1
            teams[p['home_team']] = teams.get(p['home_team'], 0) + 1
            teams[p['away_team']] = teams.get(p['away_team'], 0) + 1
        # Penalizaciones acumulativas
        penalty = 0.0
        penalty += sum((cnt - 1) * 0.02 for cnt in leagues.values() if cnt > 1)
        penalty += sum((cnt - 1) * 0.015 for cnt in teams.values() if cnt > 1)
        penalty = min(penalty, 0.15)  # Cap máximo 15%
        return max(0.85, 1.0 - penalty)

    def calculate_parlay_probability(self, picks: List[Dict]) -> float:
        """
        Calcula la probabilidad combinada de que gane el parlay
        (producto de probabilidades individuales - asume independencia)

        Args:
            picks: Lista de picks

        Returns:
            Probabilidad de ganar el parlay (0-1)
        """
        combined_prob = 1.0
        for pick in picks:
            combined_prob *= pick['predicted_probability']
        # Ajustar por correlación
        corr = self.correlation_factor(picks)
        combined_prob_adj = combined_prob * corr
        return combined_prob_adj

    def calculate_parlay_edge(self, picks: List[Dict]) -> float:
        """
        Calcula el edge del parlay completo

        Args:
            picks: Lista de picks

        Returns:
            Edge del parlay
        """
        parlay_prob = self.calculate_parlay_probability(picks)
        parlay_odds = self.calculate_parlay_odds(picks)
        implied_prob = 1 / parlay_odds
        edge = parlay_prob - implied_prob
        return edge

    def calculate_parlay_expected_value(self, picks: List[Dict], stake: float = 100) -> float:
        """
        Calcula el Expected Value del parlay

        Args:
            picks: Lista de picks
            stake: Monto apostado

        Returns:
            Expected Value
        """
        parlay_prob = self.calculate_parlay_probability(picks)
        parlay_odds = self.calculate_parlay_odds(picks)
        win_amount = stake * (parlay_odds - 1)
        loss_amount = stake
        ev = (parlay_prob * win_amount) - ((1 - parlay_prob) * loss_amount)
        return ev

    def validate_parlay(self, picks: List[Dict]) -> Dict:
        """
        Valida que un parlay cumpla con los criterios de configuración

        Args:
            picks: Lista de picks

        Returns:
            Dict con resultado de validación
        """
        num_picks = len(picks)
        parlay_odds = self.calculate_parlay_odds(picks)
        parlay_prob = self.calculate_parlay_probability(picks)

        criteria = {
            'min_picks': num_picks >= self.parlay_config['min_picks'],
            'max_picks': num_picks <= self.parlay_config['max_picks'],
            'min_total_odds': parlay_odds >= self.parlay_config['min_total_odds'],
            'max_total_odds': parlay_odds <= self.parlay_config['max_total_odds'],
            'min_combined_probability': parlay_prob >= self.parlay_config['min_combined_probability']
        }

        is_valid = all(criteria.values())

        reasons = []
        if not criteria['min_picks']:
            reasons.append(f"Too few picks: {num_picks} < {self.parlay_config['min_picks']}")
        if not criteria['max_picks']:
            reasons.append(f"Too many picks: {num_picks} > {self.parlay_config['max_picks']}")
        if not criteria['min_total_odds']:
            reasons.append(f"Odds too low: {parlay_odds:.2f} < {self.parlay_config['min_total_odds']}")
        if not criteria['max_total_odds']:
            reasons.append(f"Odds too high: {parlay_odds:.2f} > {self.parlay_config['max_total_odds']}")
        if not criteria['min_combined_probability']:
            reasons.append(f"Probability too low: {parlay_prob:.1%} < {self.parlay_config['min_combined_probability']:.1%}")

        return {
            'is_valid': is_valid,
            'criteria_met': criteria,
            'rejection_reasons': reasons
        }

    def build_best_parlay(self, picks: List[Dict]) -> Dict:
        """
        Construye el mejor parlay posible con los picks disponibles

        Args:
            picks: Lista de picks con valor

        Returns:
            Mejor parlay encontrado
        """
        if not picks:
            logger.warning("No picks available to build parlay")
            return None

        min_picks = self.parlay_config['min_picks']
        max_picks = min(self.parlay_config['max_picks'], len(picks))

        best_parlay = None
        best_score = -float('inf')

        # Probar diferentes tamaños de parlay
        for size in range(min_picks, max_picks + 1):
            # Generar todas las combinaciones posibles de ese tamaño
            for combo in combinations(picks, size):
                combo_list = list(combo)

                # Validar parlay
                validation = self.validate_parlay(combo_list)

                if not validation['is_valid']:
                    continue

                # Calcular métricas
                parlay_odds = self.calculate_parlay_odds(combo_list)
                parlay_prob = self.calculate_parlay_probability(combo_list)
                parlay_edge = self.calculate_parlay_edge(combo_list)
                parlay_ev = self.calculate_parlay_expected_value(combo_list, 100)
                corr_factor = self.correlation_factor(combo_list)

                # Score: combinación de edge y EV
                # Priorizamos edge pero también consideramos EV
                score = parlay_edge * 0.6 + (parlay_ev / 100) * 0.4

                if score > best_score:
                    best_score = score
                    best_parlay = {
                        'picks': combo_list,
                        'num_picks': len(combo_list),
                        'total_odds': parlay_odds,
                        'combined_probability': parlay_prob,
                        'correlation_factor': corr_factor,
                        'edge': parlay_edge,
                        'edge_percentage': parlay_edge * 100,
                        'expected_value': parlay_ev,
                        'score': score
                    }

        if best_parlay:
            logger.info(f"Best parlay found: {best_parlay['num_picks']} picks, "
                       f"odds {best_parlay['total_odds']:.2f}, "
                       f"edge {best_parlay['edge_percentage']:.2f}%")
        else:
            logger.warning("No valid parlay could be built with available picks")

        return best_parlay

    def build_multiple_parlays(self, picks: List[Dict], num_parlays: int = 3) -> List[Dict]:
        """
        Construye múltiples parlays diferentes (para diversificación)

        Args:
            picks: Lista de picks con valor
            num_parlays: Número de parlays a construir

        Returns:
            Lista de parlays
        """
        if not picks:
            return []

        parlays = []
        used_picks = set()

        for _ in range(num_parlays):
            # Filtrar picks no usados
            available_picks = [p for p in picks if p['match_id'] not in used_picks]

            if len(available_picks) < self.parlay_config['min_picks']:
                break

            # Construir parlay con picks disponibles
            parlay = self.build_best_parlay(available_picks)

            if parlay:
                parlays.append(parlay)
                # Marcar picks usados
                for pick in parlay['picks']:
                    used_picks.add(pick['match_id'])
            else:
                break

        return parlays

    def display_parlay(self, parlay: Dict, bankroll: float = 5000):
        """
        Muestra el parlay de forma legible

        Args:
            parlay: Diccionario con información del parlay
            bankroll: Bankroll actual para calcular stake
        """
        if not parlay:
            print("\n❌ No valid parlay could be built\n")
            return

        from src.betting.stake_calculator import StakeCalculator
        calculator = StakeCalculator()
        stake = calculator.calculate_kelly_stake(
            probability=parlay['combined_probability'],
            odds=parlay['total_odds'],
            bankroll=bankroll
        )

        potential_return = stake * parlay['total_odds']
        profit = potential_return - stake

        print(f"\n{'='*80}")
        print(f"🎯 RECOMMENDED PARLAY - {parlay['num_picks']} PICKS")
        print(f"{'='*80}\n")

        for i, pick in enumerate(parlay['picks'], 1):
            print(f"{i}. {pick['league']}: {pick['home_team']} vs {pick['away_team']}")
            print(f"   └─ {pick['prediction']} @ {pick['odds']:.2f}")
            print(f"      (Confidence: {pick['predicted_probability']:.1%}, Edge: {pick['edge_percentage']:.1f}%)")
            print()

        print(f"{'─'*80}")
        american_total = self.decimal_to_american(parlay['total_odds'])
        print(f"💰 Total Odds: {parlay['total_odds']:.2f}x ({american_total})")
        print(f"🎲 Combined Probability: {parlay['combined_probability']:.1%}")
        print(f"🔗 Correlation Factor: {parlay.get('correlation_factor',1.0):.3f}")
        print(f"📈 Parlay Edge: {parlay['edge_percentage']:.2f}%")
        print(f"💵 Expected Value: ${parlay['expected_value']:.2f} per $100 (post-correlation)")
        print(f"\n💸 RECOMMENDED STAKE: ${stake:.2f} ({stake/bankroll*100:.1f}% of bankroll)")
        print(f"🏆 Potential Return: ${potential_return:.2f}")
        print(f"💎 Potential Profit: ${profit:.2f}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    # Test simple sin scraper externo
    from src.models.predictor import MatchPredictor
    from src.betting.pick_selector import PickSelector
    import os

    print("=== Testing Parlay Builder (Simplified) ===\n")

    if not os.path.exists("models/soccer_model.pkl"):
        print("Training models first...")
        from src.models.train_model import train_all_models
        train_all_models()

    # Mock de partidos mínimos
    matches = [
        {
            'match_id': 'TEST1', 'sport': 'soccer', 'league': 'La Liga',
            'home_team': 'Equipo A', 'away_team': 'Equipo B', 'match_date': '2025-11-10',
            'odds': {'home_win': 2.05, 'away_win': 3.50, 'draw': 3.10}
        },
        {
            'match_id': 'TEST2', 'sport': 'soccer', 'league': 'Serie A',
            'home_team': 'Equipo C', 'away_team': 'Equipo D', 'match_date': '2025-11-10',
            'odds': {'home_win': 1.90, 'away_win': 4.00, 'draw': 3.40}
        },
        {
            'match_id': 'TEST3', 'sport': 'soccer', 'league': 'La Liga',
            'home_team': 'Equipo E', 'away_team': 'Equipo F', 'match_date': '2025-11-10',
            'odds': {'home_win': 2.20, 'away_win': 3.00, 'draw': 3.25}
        }
    ]

    predictor = MatchPredictor()
    predictions = predictor.predict_multiple_matches(matches)
    selector = PickSelector()
    picks = selector.select_picks(predictions)
    builder = ParlayBuilder()

    parlay = builder.build_best_parlay(picks)
    builder.display_parlay(parlay, bankroll=5000)
