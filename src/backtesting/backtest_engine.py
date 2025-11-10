"""
Sistema de backtesting para validar estrategias de apuestas
"""
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from loguru import logger
from itertools import combinations

class BacktestEngine:
    def __init__(self,
                initial_bankroll: float = 1000.0,
                stake_strategy: str = 'kelly',
                min_picks: int = 3,
                max_picks: int = 5,
                min_total_odds: float = 5.0,
                max_total_odds: float = 20.0,
                min_combined_probability: float = 0.15):
        """
        Args:
            initial_bankroll: Capital inicial
            stake_strategy: Estrategia de stakes ('kelly', 'flat', 'dynamic')
            min_picks: Mínimo de picks por parlay
            max_picks: Máximo de picks por parlay
            min_total_odds: Odds mínimas del parlay
            max_total_odds: Odds máximas del parlay
            min_combined_probability: Probabilidad combinada mínima
        """
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.stake_strategy = stake_strategy
        self.bets_history = []
        self.daily_balance = []

        # Configuración de parlay
        self.min_picks = min_picks
        self.max_picks = max_picks
        self.min_total_odds = min_total_odds
        self.max_total_odds = max_total_odds
        self.min_combined_probability = min_combined_probability
        
    def run_backtest(self,
                    historical_data: pd.DataFrame,
                    model,
                    selection_criteria: Dict) -> Dict:
        """
        Ejecuta backtesting con datos históricos

        Args:
            historical_data: DataFrame con partidos históricos
            model: Modelo de predicción entrenado
            selection_criteria: Criterios de selección (ej: min_prob, min_edge)

        Returns:
            Diccionario con métricas de performance
        """
        logger.info("Iniciando backtesting...")

        if 'date' not in historical_data.columns:
            logger.error("DataFrame must have 'date' column")
            return {'error': 'Missing date column in historical data'}

        # Convertir a lista de diccionarios para procesar
        matches_list = historical_data.to_dict('records')

        # Agrupar por fecha
        from collections import defaultdict
        matches_by_date = defaultdict(list)
        for match in matches_list:
            matches_by_date[match['date']].append(match)

        for date, daily_matches in matches_by_date.items():
            # 1. Generar predicciones
            try:
                predictions = model.predict_multiple_matches(daily_matches)
            except Exception as e:
                logger.warning(f"Error predicting matches for {date}: {e}")
                continue

            # 2. Seleccionar picks según criterios
            picks = self._select_picks(predictions, selection_criteria)

            # 3. Construir parlay (si hay picks suficientes)
            if len(picks) >= self.min_picks:
                parlay = self._build_parlay(picks)

                if parlay:
                    # 4. Calcular stake
                    stake = self._calculate_stake(parlay)

                    # 5. Simular resultado
                    self._simulate_bet(parlay, stake, date, daily_matches)

            # Registrar balance diario
            self.daily_balance.append({
                'date': date,
                'balance': self.current_bankroll
            })

        return self._calculate_metrics()
    
    def _select_picks(self, predictions: List, criteria: Dict) -> List:
        """Selecciona picks que cumplen criterios mínimos"""
        selected = []
        for pred in predictions:
            # Obtener probabilidad predicha
            probabilities = pred.get('probabilities', {})
            prediction_label = pred.get('prediction')
            predicted_prob = probabilities.get(prediction_label, 0)

            # Obtener odds de la predicción
            odds_dict = pred.get('odds', {})
            if prediction_label == 'home_win':
                odds = odds_dict.get('home_win', 0)
            elif prediction_label == 'away_win':
                odds = odds_dict.get('away_win', 0)
            elif prediction_label == 'draw':
                odds = odds_dict.get('draw', 0)
            else:
                continue  # Skip invalid predictions

            if odds <= 0:
                continue

            # Calcular edge
            implied_prob = 1 / odds
            edge = predicted_prob - implied_prob
            edge_percentage = edge * 100

            # Agregar campos calculados a la predicción
            pred['predicted_probability'] = predicted_prob
            pred['odds'] = odds
            pred['edge'] = edge
            pred['edge_percentage'] = edge_percentage

            # Validar criterios
            if predicted_prob >= criteria.get('min_probability', 0.65) and edge_percentage >= criteria.get('min_edge', 5.0):
                selected.append(pred)

        return selected

    def _build_parlay(self, picks: List) -> Dict:
        """
        Construye parlay óptimo con los picks seleccionados
        Usa lógica similar a ParlayBuilder para encontrar mejor combinación
        """
        if not picks or len(picks) < self.min_picks:
            return None

        best_parlay = None
        best_score = -float('inf')

        # Probar diferentes tamaños de parlay
        max_size = min(self.max_picks, len(picks))

        for size in range(self.min_picks, max_size + 1):
            # Generar todas las combinaciones posibles de ese tamaño
            for combo in combinations(picks, size):
                combo_list = list(combo)

                # Calcular métricas
                total_odds = np.prod([p['odds'] for p in combo_list])
                combined_prob = np.prod([p['predicted_probability'] for p in combo_list])
                implied_prob = 1 / total_odds
                edge = combined_prob - implied_prob
                ev = (combined_prob * total_odds * 100) - ((1 - combined_prob) * 100)

                # Validar criterios
                if total_odds < self.min_total_odds or total_odds > self.max_total_odds:
                    continue
                if combined_prob < self.min_combined_probability:
                    continue

                # Score: combinación de edge y EV (priorizando edge)
                score = edge * 0.6 + (ev / 100) * 0.4

                if score > best_score:
                    best_score = score
                    best_parlay = {
                        'picks': combo_list,
                        'num_picks': len(combo_list),
                        'total_odds': total_odds,
                        'combined_probability': combined_prob,
                        'edge': edge,
                        'edge_percentage': edge * 100,
                        'expected_value': ev,
                        'score': score
                    }

        return best_parlay
    
    def _calculate_stake(self, parlay: Dict) -> float:
        """Calcula stake según estrategia elegida"""
        if self.stake_strategy == 'kelly':
            # Kelly Criterion: f = (bp - q) / b
            # donde b = odds - 1, p = probabilidad, q = 1 - p
            edge = parlay['combined_probability'] * parlay['total_odds'] - 1

            if edge <= 0:
                return 0

            kelly_stake = (edge * self.current_bankroll) / (parlay['total_odds'] - 1)

            # Usar Kelly fraccionado (10%) para ser conservadores
            kelly_stake *= 0.10

            # Limitar a máximo 2% del bankroll
            max_stake = self.current_bankroll * 0.02
            return min(kelly_stake, max_stake)

        elif self.stake_strategy == 'flat':
            return self.current_bankroll * 0.02  # 2% flat

        return 0

    def _simulate_bet(self, parlay: Dict, stake: float, date, all_matches: List):
        """
        Simula resultado de una apuesta comparando predicción vs resultado real

        Args:
            parlay: Parlay construido con picks
            stake: Monto apostado
            date: Fecha de la apuesta
            all_matches: Todos los partidos del día (con resultados reales)
        """
        if stake <= 0 or stake > self.current_bankroll:
            logger.warning(f"Invalid stake {stake}, skipping bet")
            return

        # Crear mapeo de match_id a resultado real
        match_results = {}
        for match in all_matches:
            match_id = match.get('match_id', f"{match.get('home_team')}_{match.get('away_team')}")
            result_label = match.get('result_label')
            match_results[match_id] = result_label

        # Verificar si TODOS los picks del parlay ganaron
        all_correct = True
        picks_with_results = []

        for pick in parlay['picks']:
            match_id = pick.get('match_id', f"{pick.get('home_team')}_{pick.get('away_team')}")
            predicted_outcome = pick.get('prediction')
            actual_outcome = match_results.get(match_id)

            # Si no hay resultado real, asumir que perdió (conservador)
            if actual_outcome is None:
                all_correct = False
                pick_won = False
            else:
                pick_won = (predicted_outcome == actual_outcome)
                if not pick_won:
                    all_correct = False

            picks_with_results.append({
                **pick,
                'actual_outcome': actual_outcome,
                'pick_won': pick_won
            })

        # Calcular resultado del parlay
        if all_correct:
            # GANÓ - Recibir payout
            payout = stake * parlay['total_odds']
            profit = payout - stake
            self.current_bankroll += profit
            result = 'won'
        else:
            # PERDIÓ - Perder stake
            self.current_bankroll -= stake
            profit = -stake
            result = 'lost'

        # Registrar apuesta en historial
        self.bets_history.append({
            'date': date,
            'stake': stake,
            'odds': parlay['total_odds'],
            'num_picks': parlay['num_picks'],
            'combined_probability': parlay['combined_probability'],
            'edge': parlay['edge'],
            'picks': picks_with_results,
            'result': result,
            'profit': profit,
            'bankroll_before': self.current_bankroll - profit,
            'bankroll_after': self.current_bankroll
        })
        
    def _calculate_metrics(self) -> Dict:
        """Calcula métricas finales del backtesting"""
        total_bets = len(self.bets_history)

        if total_bets == 0:
            return {
                'error': 'No bets placed during backtest',
                'total_bets': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'final_bankroll': self.current_bankroll,
                'total_roi': 0,
                'total_profit': 0,
                'avg_odds': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'daily_balance': []
            }

        bets_df = pd.DataFrame(self.bets_history)

        # Contar wins y losses
        wins = (bets_df['result'] == 'won').sum()
        losses = (bets_df['result'] == 'lost').sum()
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0

        # ROI y Profit
        total_profit = self.current_bankroll - self.initial_bankroll
        roi = (total_profit / self.initial_bankroll * 100) if self.initial_bankroll > 0 else 0

        # Odds promedio
        avg_odds = bets_df['odds'].mean()

        # Drawdown
        daily_balance_df = pd.DataFrame(self.daily_balance)
        if len(daily_balance_df) > 0:
            daily_balance_df['cummax'] = daily_balance_df['balance'].cummax()
            daily_balance_df['drawdown'] = (daily_balance_df['cummax'] - daily_balance_df['balance']) / daily_balance_df['cummax'] * 100
            max_drawdown = daily_balance_df['drawdown'].max()
        else:
            max_drawdown = 0

        # Sharpe Ratio (anualizado)
        if len(daily_balance_df) > 1:
            daily_returns = daily_balance_df['balance'].pct_change().dropna()
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                sharpe_ratio = np.sqrt(365) * (daily_returns.mean() / daily_returns.std())
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        # Profit promedio por apuesta
        avg_profit_per_bet = total_profit / total_bets if total_bets > 0 else 0

        # Calmar Ratio (ROI anualizado / Max Drawdown)
        calmar_ratio = (roi / max_drawdown) if max_drawdown > 0 else 0

        logger.info(f"Backtesting completed: {total_bets} bets, {wins}W-{losses}L, "
                   f"Win Rate: {win_rate:.1f}%, ROI: {roi:.2f}%, "
                   f"Final Bankroll: {self.current_bankroll:.2f}")

        return {
            'total_bets': int(total_bets),
            'wins': int(wins),
            'losses': int(losses),
            'win_rate': float(win_rate),
            'final_bankroll': float(self.current_bankroll),
            'initial_bankroll': float(self.initial_bankroll),
            'total_profit': float(total_profit),
            'total_roi': float(roi),
            'avg_odds': float(avg_odds),
            'avg_profit_per_bet': float(avg_profit_per_bet),
            'max_drawdown': float(max_drawdown),
            'sharpe_ratio': float(sharpe_ratio),
            'calmar_ratio': float(calmar_ratio),
            'daily_balance': daily_balance_df.to_dict('records') if len(daily_balance_df) > 0 else []
        }