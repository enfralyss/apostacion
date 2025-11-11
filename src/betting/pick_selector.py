"""
Pick Selector - Selecciona picks con valor basándose en predicciones y criterios
"""

from typing import List, Dict
from loguru import logger
import yaml
try:
    from src.utils.database import BettingDatabase
except Exception:
    BettingDatabase = None


class PickSelector:
    """Selector de picks con valor para apuestas"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Args:
            config_path: Ruta al archivo de configuración
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.pick_criteria = self.config['picks']
        # Overrides desde DB si existen
        try:
            if BettingDatabase is not None:
                db = BettingDatabase()
                for key in ['min_probability', 'min_edge', 'min_odds', 'max_odds', 'max_picks_per_league']:
                    val = db.get_parameter(key, None)
                    if val is not None:
                        self.pick_criteria[key] = float(val) if key != 'max_picks_per_league' else int(val)
        except Exception:
            pass

    def calculate_implied_probability(self, odds: float) -> float:
        """
        Calcula la probabilidad implícita de las odds

        Args:
            odds: Cuota decimal (ej: 1.85)

        Returns:
            Probabilidad implícita (0-1)
        """
        return 1 / odds

    def calculate_edge(self, predicted_prob: float, odds: float) -> float:
        """
        Calcula el edge (ventaja) de una apuesta

        Edge = Probabilidad Real - Probabilidad Implícita

        Args:
            predicted_prob: Probabilidad predicha por el modelo
            odds: Cuota ofrecida por la casa

        Returns:
            Edge (puede ser negativo si no hay valor)
        """
        implied_prob = self.calculate_implied_probability(odds)
        edge = predicted_prob - implied_prob
        return edge

    def calculate_expected_value(self, predicted_prob: float, odds: float, stake: float = 100) -> float:
        """
        Calcula el Expected Value (EV) de una apuesta

        EV = (Probabilidad de ganar * Ganancia) - (Probabilidad de perder * Pérdida)

        Args:
            predicted_prob: Probabilidad de ganar
            odds: Cuota
            stake: Monto apostado

        Returns:
            Expected Value
        """
        win_amount = stake * (odds - 1)
        loss_amount = stake

        ev = (predicted_prob * win_amount) - ((1 - predicted_prob) * loss_amount)
        return ev

    def evaluate_pick(self, prediction: Dict) -> Dict:
        """
        Evalúa si un pick cumple con los criterios de selección

        Args:
            prediction: Diccionario de predicción del modelo

        Returns:
            Diccionario con evaluación del pick
        """
        sport = prediction['sport']
        pred_outcome = prediction['prediction']
        probabilities = prediction['probabilities']
        odds_dict = prediction['odds']

        # Determinar la cuota correspondiente a la predicción
        if sport == "soccer":
            if pred_outcome == "home_win":
                odds = odds_dict.get('home_win', 0)
                predicted_prob = probabilities.get('home_win', 0)
            elif pred_outcome == "away_win":
                odds = odds_dict.get('away_win', 0)
                predicted_prob = probabilities.get('away_win', 0)
            else:  # draw
                odds = odds_dict.get('draw', 0)
                predicted_prob = probabilities.get('draw', 0)
        else:  # NBA
            if pred_outcome == "home_win":
                odds = odds_dict.get('home_win', 0)
                predicted_prob = probabilities.get('home_win', 0)
            else:  # away_win
                odds = odds_dict.get('away_win', 0)
                predicted_prob = probabilities.get('away_win', 0)

        if odds == 0:
            return {
                'has_value': False,
                'reason': 'Odds not available for prediction'
            }

        # Calcular métricas
        implied_prob = self.calculate_implied_probability(odds)
        edge = self.calculate_edge(predicted_prob, odds)
        edge_percentage = edge * 100
        ev = self.calculate_expected_value(predicted_prob, odds, 100)

        # Criterios de selección
        criteria = {
            'min_probability': predicted_prob >= self.pick_criteria['min_probability'],
            'min_edge': edge >= self.pick_criteria['min_edge'],
            'min_odds': odds >= self.pick_criteria['min_odds'],
            'max_odds': odds <= self.pick_criteria['max_odds']
        }

        # Determinar si el pick tiene valor
        has_value = all(criteria.values())

        # Razones de rechazo
        reasons = []
        if not criteria['min_probability']:
            reasons.append(f"Probability {predicted_prob:.1%} < {self.pick_criteria['min_probability']:.1%}")
        if not criteria['min_edge']:
            reasons.append(f"Edge {edge_percentage:.1f}% < {self.pick_criteria['min_edge']*100:.1f}%")
        if not criteria['min_odds']:
            reasons.append(f"Odds {odds} < {self.pick_criteria['min_odds']}")
        if not criteria['max_odds']:
            reasons.append(f"Odds {odds} > {self.pick_criteria['max_odds']}")

        evaluation = {
            'match_id': prediction['match_id'],
            'sport': sport,
            'league': prediction['league'],
            'home_team': prediction['home_team'],
            'away_team': prediction['away_team'],
            'match_date': prediction['match_date'],
            'prediction': pred_outcome,
            'predicted_probability': predicted_prob,
            'odds': odds,
            'implied_probability': implied_prob,
            'edge': edge,
            'edge_percentage': edge_percentage,
            'expected_value': ev,
            'has_value': has_value,
            'criteria_met': criteria,
            'rejection_reasons': reasons if not has_value else []
        }

        return evaluation

    def select_picks(self, predictions: List[Dict], max_picks: int = None) -> List[Dict]:
        """
        Selecciona los mejores picks de una lista de predicciones

        Args:
            predictions: Lista de predicciones
            max_picks: Máximo número de picks a seleccionar (None = sin límite)

        Returns:
            Lista de picks con valor, ordenados por edge
        """
        evaluated_picks = []

        for prediction in predictions:
            evaluation = self.evaluate_pick(prediction)

            if evaluation['has_value']:
                evaluated_picks.append(evaluation)
                logger.info(
                    f"✓ Value found: {evaluation['home_team']} vs {evaluation['away_team']} "
                    f"({evaluation['prediction']}) - Edge: {evaluation['edge_percentage']:.1f}%"
                )
            else:
                logger.debug(
                    f"✗ No value: {evaluation['home_team']} vs {evaluation['away_team']} - "
                    f"{', '.join(evaluation['rejection_reasons'])}"
                )

        # Ordenar por edge (mayor primero)
        evaluated_picks.sort(key=lambda x: x['edge'], reverse=True)

        # Aplicar diversificación: máximo 1 pick por liga
        diversified_picks = self._diversify_by_league(evaluated_picks)

        # Limitar número de picks si se especifica
        if max_picks and len(diversified_picks) > max_picks:
            diversified_picks = diversified_picks[:max_picks]

        logger.info(f"\nSelected {len(diversified_picks)} picks with value")

        return diversified_picks

    def _diversify_by_league(self, picks: List[Dict]) -> List[Dict]:
        """
        Asegura diversificación: máximo 1 pick por liga

        Args:
            picks: Lista de picks ordenados por edge

        Returns:
            Lista diversificada de picks
        """
        max_per_league = self.pick_criteria['max_picks_per_league']
        league_counts = {}
        diversified = []

        for pick in picks:
            league = pick['league']

            if league not in league_counts:
                league_counts[league] = 0

            if league_counts[league] < max_per_league:
                diversified.append(pick)
                league_counts[league] += 1

        if len(diversified) < len(picks):
            logger.info(f"Diversification applied: {len(picks)} -> {len(diversified)} picks")

        return diversified

    def display_picks(self, picks: List[Dict]):
        """Muestra los picks seleccionados de forma legible"""
        if not picks:
            print("\n❌ No picks with value found today\n")
            return

        print(f"\n{'='*70}")
        print(f"💎 PICKS WITH VALUE - {len(picks)} found")
        print(f"{'='*70}\n")

        for i, pick in enumerate(picks, 1):
            print(f"{i}. {pick['league']}: {pick['home_team']} vs {pick['away_team']}")
            print(f"   └─ Pick: {pick['prediction']} @ {pick['odds']:.2f}")
            print(f"   └─ Confidence: {pick['predicted_probability']:.1%}")
            print(f"   └─ Edge: {pick['edge_percentage']:.1f}%")
            print(f"   └─ EV: ${pick['expected_value']:.2f} per $100")
            print()


if __name__ == "__main__":
    # Test del selector (scraper opcional no incluido en este entorno)
    from src.models.predictor import MatchPredictor
    import os

    print("=== Testing Pick Selector ===\n")

    # Entrenar modelos si no existen
    if not os.path.exists("models/soccer_model.pkl"):
        print("Training models first...")
        from src.models.train_model import train_all_models
        train_all_models()

    # Obtener partidos y predicciones
    predictor = MatchPredictor()
    selector = PickSelector()
    matches = []  # Placeholder: agregar partidos mock si se requiere
    predictions = predictor.predict_multiple_matches(matches)

    # Seleccionar picks
    picks = selector.select_picks(predictions, max_picks=10)

    # Mostrar resultados
    selector.display_picks(picks)
