"""
Sistema de backtesting para validar estrategias de apuestas
"""
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from loguru import logger

class BacktestEngine:
    def __init__(self, 
                initial_bankroll: float = 1000.0,
                stake_strategy: str = 'kelly'):
        """
        Args:
            initial_bankroll: Capital inicial
            stake_strategy: Estrategia de stakes ('kelly', 'flat', 'dynamic')
        """
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.stake_strategy = stake_strategy
        self.bets_history = []
        self.daily_balance = []
        
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
        
        for date, daily_matches in historical_data.groupby('date'):
            # 1. Generar predicciones
            predictions = model.predict_multiple_matches(daily_matches)
            
            # 2. Seleccionar picks según criterios
            picks = self._select_picks(predictions, selection_criteria)
            
            # 3. Construir parlay (si hay picks)
            if picks:
                parlay = self._build_parlay(picks)
                
                # 4. Calcular stake
                stake = self._calculate_stake(parlay)
                
                # 5. Simular resultado
                self._simulate_bet(parlay, stake, date)
            
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
            if (pred['predicted_probability'] >= criteria['min_probability'] and
                pred['edge_percentage'] >= criteria['min_edge']):
                selected.append(pred)
        return selected
    
    def _build_parlay(self, picks: List) -> Dict:
        """Construye parlay óptimo con los picks seleccionados"""
        # TODO: Implementar lógica de construcción de parlay
        return {
            'picks': picks,
            'total_odds': np.prod([p['odds'] for p in picks]),
            'combined_probability': np.prod([p['predicted_probability'] for p in picks])
        }
    
    def _calculate_stake(self, parlay: Dict) -> float:
        """Calcula stake según estrategia elegida"""
        if self.stake_strategy == 'kelly':
            edge = parlay['combined_probability'] * parlay['total_odds'] - 1
            return (edge * self.current_bankroll) / (parlay['total_odds'] - 1) * 0.5  # Half Kelly
        
        return self.current_bankroll * 0.02  # 2% flat
        
    def _simulate_bet(self, parlay: Dict, stake: float, date: datetime):
        """Simula resultado de una apuesta"""
        # TODO: Implementar lógica de simulación
        
        # Registro para análisis posterior
        self.bets_history.append({
            'date': date,
            'stake': stake,
            'odds': parlay['total_odds'],
            'picks': parlay['picks'],
            'bankroll_before': self.current_bankroll
        })
        
    def _calculate_metrics(self) -> Dict:
        """Calcula métricas finales del backtesting"""
        daily_balance_df = pd.DataFrame(self.daily_balance)
        bets_df = pd.DataFrame(self.bets_history)
        
        total_bets = len(self.bets_history)
        if total_bets == 0:
            return {'error': 'No bets placed during backtest'}
            
        roi = (self.current_bankroll - self.initial_bankroll) / self.initial_bankroll * 100
        
        # Calcular drawdown
        daily_balance_df['drawdown'] = (daily_balance_df['balance'].cummax() - 
                                      daily_balance_df['balance']) / daily_balance_df['balance'].cummax() * 100
        max_drawdown = daily_balance_df['drawdown'].max()
        
        # Calcular Sharpe Ratio (asumiendo retornos diarios)
        daily_returns = daily_balance_df['balance'].pct_change().dropna()
        sharpe = np.sqrt(365) * (daily_returns.mean() / daily_returns.std())
        
        return {
            'total_bets': total_bets,
            'final_bankroll': self.current_bankroll,
            'total_roi': roi,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'win_rate': 0.0,  # TODO: Calcular
            'avg_odds': bets_df['odds'].mean(),
            'daily_balance': daily_balance_df.to_dict('records')
        }