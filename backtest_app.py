import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'backtesting'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'models'))
from backtest_engine import BacktestEngine
from historical_data import HistoricalDataCollector
from predictor import Predictor  # Ajusta si tu clase de modelo tiene otro nombre

st.title("Backtesting de Estrategias - TriunfoBet")

# Parámetros de ejemplo
historical_file = st.text_input("Archivo de datos históricos CSV", "data/historical_matches.csv")
model_file = st.text_input("Modelo entrenado (.pkl)", "models/soccer_model.pkl")

if st.button("Ejecutar Backtesting"):
    with st.spinner("Cargando datos y modelo..."):
        collector = HistoricalDataCollector()
        try:
            df = collector.load_historical_matches(historical_file)
        except Exception as e:
            st.error(f"Error cargando datos históricos: {e}")
            st.stop()
        try:
            model = Predictor.load(model_file)  # Ajusta si tu clase tiene otro método
        except Exception as e:
            st.error(f"Error cargando modelo: {e}")
            st.stop()
        criteria = {"min_probability": 0.65, "min_edge": 0.05}
        engine = BacktestEngine(initial_bankroll=1000)
        st.info("Ejecutando backtest, esto puede tardar unos minutos...")
        results = engine.run_backtest(df, model, criteria)
        if 'error' in results:
            st.error(results['error'])
        else:
            st.success("Backtesting completado!")
            st.write(results)
            if 'daily_balance' in results:
                daily_df = pd.DataFrame(results['daily_balance'])
                st.line_chart(daily_df.set_index('date')['balance'])
