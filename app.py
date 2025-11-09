
import streamlit as st
import subprocess
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'utils'))
from src.utils.database import BettingDatabase

st.set_page_config(page_title="TriunfoBet ML Bot", layout="wide")
st.title("TriunfoBet ML Bot - Dashboard MVP")

# Inicializar base de datos
db = BettingDatabase()
metrics = db.calculate_performance_metrics()
bankroll_history = db.get_bankroll_history(30)
recent_bets = db.get_recent_bets(5)

st.markdown("### 📊 Métricas Clave")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Bankroll actual", f"{bankroll_history[0]['bankroll'] if bankroll_history else 'N/A'} VES")
col2.metric("ROI total", f"{metrics['roi']:.2f}%")
col3.metric("Win Rate", f"{metrics['win_rate']:.1f}% ({metrics['wins']}/{metrics['total_bets']})")
col4.metric("Profit total", f"{metrics['total_profit_loss']:.2f} VES")

st.markdown("---\n### 📈 Evolución del Bankroll")
if bankroll_history:
    df = pd.DataFrame(bankroll_history[::-1])
    df['date'] = pd.to_datetime(df['date'])
    st.line_chart(df.set_index('date')['bankroll'])
else:
    st.info("No hay historial de bankroll disponible.")

st.markdown("---\n### 🎯 Picks de Hoy")
if recent_bets:
    for bet in recent_bets:
        st.write(f"**{bet['bet_date'][:10]} | {bet['bet_type'].capitalize()} | Cuota: {bet['total_odds']} | Stake: {bet['stake']}**")
        picks = db.get_bet_picks(bet['id'])
        for pick in picks:
            st.write(f"- {pick['league']}: {pick['home_team']} vs {pick['away_team']} | {pick['prediction']} | Odds: {pick['odds']} | Prob: {pick['predicted_probability']*100:.1f}% | Edge: {pick['edge']*100:.1f}%")
        st.markdown("---")
else:
    st.info("No hay picks recientes.")

if st.button("Ejecutar Análisis ML"):
    with st.spinner("Ejecutando bot_real.py y analizando partidos..."):
        result = subprocess.run([sys.executable, "bot_real.py"], capture_output=True, text=True)
        st.success("Análisis completado.")
        st.code(result.stdout)

st.markdown("---\n_Desarrollado como MVP rápido con Streamlit_")
