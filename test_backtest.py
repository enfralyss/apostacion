"""
Script de prueba para BacktestEngine
Genera datos sintéticos y ejecuta backtesting
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.backtesting.backtest_engine import BacktestEngine
from src.models.predictor import MatchPredictor
from src.utils.data_generator import generate_training_data
import pandas as pd

def test_backtest():
    print("="*70)
    print("PRUEBA DE BACKTESTING ENGINE")
    print("="*70)

    # 1. Generar datos sintéticos
    print("\n1. Generando datos históricos sintéticos...")
    df_soccer = generate_training_data("soccer", num_matches=200)
    df_soccer['sport'] = 'soccer'

    # Agregar fechas y match_ids
    from datetime import datetime, timedelta
    import random
    base_date = datetime.now() - timedelta(days=180)
    # Agrupar múltiples partidos en la misma fecha para permitir parlays
    num_dates = len(df_soccer) // 5  # 5 partidos por día
    dates = []
    for i in range(len(df_soccer)):
        date_index = i // 5  # 5 partidos comparten la misma fecha
        dates.append(base_date + timedelta(days=date_index))
    df_soccer['date'] = [d.strftime('%Y-%m-%d') for d in dates]
    df_soccer['match_date'] = [d.isoformat() for d in dates]  # Agregar match_date también
    df_soccer['match_id'] = [f"match_{i}" for i in range(len(df_soccer))]
    df_soccer['home_team'] = [f"Team_{random.randint(1,20)}" for _ in range(len(df_soccer))]
    df_soccer['away_team'] = [f"Team_{random.randint(1,20)}" for _ in range(len(df_soccer))]
    df_soccer['league'] = ['Test League'] * len(df_soccer)

    # Agregar odds basadas en probabilidades del modelo
    df_soccer['home_win_odds'] = df_soccer['home_win_rate'].apply(lambda x: max(1.5, min(5.0, 1 / (x + 0.1))))
    df_soccer['away_win_odds'] = df_soccer['away_win_rate'].apply(lambda x: max(1.5, min(5.0, 1 / (x + 0.1))))
    df_soccer['draw_odds'] = 3.5

    # Agregar odds como diccionario para cada partido
    df_soccer['odds'] = df_soccer.apply(lambda row: {
        'home_win': row['home_win_odds'],
        'away_win': row['away_win_odds'],
        'draw': row['draw_odds']
    }, axis=1)

    print(f"   - {len(df_soccer)} partidos de soccer generados")
    print(f"   - Columnas: {list(df_soccer.columns[:10])}...")

    # 2. Cargar modelo entrenado
    print("\n2. Cargando modelo entrenado...")
    try:
        predictor = MatchPredictor(soccer_model_path="models/soccer_model.pkl")
        print("   - Modelo cargado correctamente")
    except Exception as e:
        print(f"   - Error cargando modelo: {e}")
        print("   - Entrenando nuevo modelo...")
        from src.models.train_model import train_all_models
        train_all_models()
        predictor = MatchPredictor(soccer_model_path="models/soccer_model.pkl")

    # 3. Inicializar BacktestEngine
    print("\n3. Inicializando BacktestEngine...")
    engine = BacktestEngine(
        initial_bankroll=1000.0,
        stake_strategy='kelly',
        min_picks=3,
        max_picks=5,
        min_total_odds=5.0,
        max_total_odds=20.0,
        min_combined_probability=0.15
    )
    print(f"   - Bankroll inicial: ${engine.initial_bankroll:.2f}")

    # 4. Ejecutar backtesting
    print("\n4. Ejecutando backtesting...")
    selection_criteria = {
        'min_probability': 0.50,  # Relajar criterios para testing
        'min_edge': 0.0  # Sin edge mínimo para testing
    }

    results = engine.run_backtest(df_soccer, predictor, selection_criteria)

    # 5. Mostrar resultados
    print("\n" + "="*70)
    print("RESULTADOS DEL BACKTESTING")
    print("="*70)

    if 'error' in results:
        print(f"\nError: {results['error']}")
    else:
        print(f"\nEstadisticas Generales:")
        print(f"   - Total de apuestas: {results['total_bets']}")
        print(f"   - Victorias: {results['wins']}")
        print(f"   - Derrotas: {results['losses']}")
        print(f"   - Win Rate: {results['win_rate']:.1f}%")

        print(f"\nPerformance Financiera:")
        print(f"   - Bankroll inicial: ${results['initial_bankroll']:.2f}")
        print(f"   - Bankroll final: ${results['final_bankroll']:.2f}")
        print(f"   - Profit total: ${results['total_profit']:.2f}")
        print(f"   - ROI: {results['total_roi']:.2f}%")
        print(f"   - Profit promedio por apuesta: ${results['avg_profit_per_bet']:.2f}")

        print(f"\nMetricas de Riesgo:")
        print(f"   - Odds promedio: {results['avg_odds']:.2f}x")
        print(f"   - Max Drawdown: {results['max_drawdown']:.2f}%")
        print(f"   - Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"   - Calmar Ratio: {results['calmar_ratio']:.2f}")

        # Mostrar evolución del bankroll
        if results.get('daily_balance'):
            print(f"\nEvolucion del Bankroll:")
            daily_df = pd.DataFrame(results['daily_balance'])
            print(daily_df.head(10).to_string(index=False))
            if len(daily_df) > 10:
                print(f"   ... ({len(daily_df) - 10} días más)")

    print("\n" + "="*70)
    print("PRUEBA COMPLETADA")
    print("="*70)

if __name__ == "__main__":
    test_backtest()
