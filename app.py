import streamlit as st
import subprocess
import sys
import pandas as pd
from src.utils.database import BettingDatabase
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.historical_data import HistoricalDataCollector
from src.models.predictor import MatchPredictor
from src.utils.data_generator import generate_training_data
from src.utils.clv_tracker import CLVTracker

st.set_page_config(page_title="TriunfoBet ML Bot", layout="wide")
st.title("TriunfoBet ML Bot - Panel")

# Inicializar DB
db = BettingDatabase()

# Secciones con tabs para organización
tab_dashboard, tab_picks, tab_backtest, tab_realdata, tab_modelos, tab_hist, tab_clv = st.tabs([
    "Dashboard", "Picks de hoy", "Backtesting", "Datos Reales", "Modelos", "Histórico", "CLV"
 ])

with tab_dashboard:
    metrics = db.calculate_performance_metrics()
    bankroll_history = db.get_bankroll_history(60)
    st.subheader("📊 Métricas Clave")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Bankroll actual", f"{bankroll_history[0]['bankroll'] if bankroll_history else 'N/A'} VES")
    col2.metric("ROI total", f"{metrics['roi']:.2f}%")
    col3.metric("Win Rate", f"{metrics['win_rate']:.1f}% ({metrics['wins']}/{metrics['total_bets']})")
    col4.metric("Profit total", f"{metrics['total_profit_loss']:.2f} VES")

    st.markdown("### 📈 Evolución del Bankroll")
    if bankroll_history:
        df_b = pd.DataFrame(bankroll_history[::-1])
        df_b['date'] = pd.to_datetime(df_b['date'])
        st.line_chart(df_b.set_index('date')['bankroll'])
    else:
        st.info("No hay historial de bankroll disponible.")

    st.markdown("### 🧮 Ejecutar análisis ML (manual)")
    if st.button("Ejecutar Análisis ML", key="run_ml"):
        with st.spinner("Ejecutando bot_real.py y analizando partidos..."):
            result = subprocess.run([sys.executable, "bot_real.py"], capture_output=True, text=True)
            if result.returncode != 0:
                st.error("Hubo un error al ejecutar el análisis")
                st.code(result.stderr)
            else:
                st.success("Análisis completado.")
                st.code(result.stdout)

with tab_picks:
    st.subheader("🎯 Picks de Hoy")
    recent_bets = db.get_recent_bets(10)
    if recent_bets:
        for bet in recent_bets:
            st.write(f"**{bet['bet_date'][:10]} | {bet['bet_type'].capitalize()} | Cuota: {bet['total_odds']} | Stake: {bet['stake']}**")
            picks = db.get_bet_picks(bet['id'])
            for pick in picks:
                st.write(f"- {pick['league']}: {pick['home_team']} vs {pick['away_team']} | {pick['prediction']} | Odds: {pick['odds']} | Prob: {pick['predicted_probability']*100:.1f}% | Edge: {pick['edge']*100:.1f}%")
            st.markdown("---")

        st.markdown("### 📝 Registrar colocación real (Placement Validation)")
        with st.form("placement_form"):
            bet_to_update = st.selectbox(
                "Selecciona apuesta pendiente", 
                [b['id'] for b in recent_bets if b['status'] == 'pending'],
                help="Sólo apuestas pendientes admiten actualización de odds colocadas"
            )
            placed_odds = st.number_input("Odds reales obtenidas", min_value=1.01, step=0.01)
            combined_prob_manual = st.number_input("Probabilidad combinada (si deseas sobreescribir)", min_value=0.0, max_value=1.0, value=0.0, help="Déjalo en 0 para usar la del parlay original")
            submit_place = st.form_submit_button("Actualizar colocación")
            if submit_place and bet_to_update:
                # Recuperar probabilidad original si no se especifica
                if combined_prob_manual == 0.0:
                    try:
                        # estimar desde picks
                        picks_parlay = db.get_bet_picks(bet_to_update)
                        combined_prob = 1.0
                        for p in picks_parlay:
                            combined_prob *= p.get('predicted_probability', 0)
                    except Exception:
                        combined_prob = None
                else:
                    combined_prob = combined_prob_manual
                update_info = db.update_bet_placement(bet_to_update, placed_odds, combined_probability=combined_prob)
                if update_info:
                    st.success(f"Placement registrado. Stake ajustado: {update_info['adjusted_stake']:.2f}. Edge nuevo: {update_info['edge_at_placement']*100:.2f}%")
                    st.json(update_info)
                    # Notificar por Telegram si está configurado
                    try:
                        from src.utils.notifications import TelegramNotifier
                        notifier = TelegramNotifier()
                        if notifier.enabled:
                            notifier.send_placement_update(update_info)
                    except Exception:
                        pass
                else:
                    st.error("No se pudo actualizar la colocación")
    else:
        st.info("No hay picks recientes.")

with tab_backtest:
    st.subheader("🧪 Backtesting de Estrategias")
    historical_file = st.text_input("Archivo de datos históricos CSV", "data/historical_matches.csv", key="hist_file")
    uploader = st.file_uploader("O sube un CSV histórico", type=["csv"], key="hist_upl")
    model_file = st.text_input("Modelo entrenado (.pkl)", "models/soccer_model.pkl", key="model_file")
    if st.button("Generar dataset sintético", key="gen_hist"):
        with st.spinner("Generando dataset sintético (soccer + NBA)..."):
            try:
                df_soccer = generate_training_data("soccer", 1000)
                df_soccer['sport'] = 'soccer'
                df_nba = generate_training_data("nba", 1000)
                df_nba['sport'] = 'nba'
                combined = pd.concat([df_soccer, df_nba], ignore_index=True)
                import os as _os
                _os.makedirs("data", exist_ok=True)
                combined.to_csv("data/historical_matches.csv", index=False)
                st.success("Dataset generado en data/historical_matches.csv")
                st.session_state['hist_file'] = "data/historical_matches.csv"
            except Exception as e:
                st.error(f"No se pudo generar el dataset sintético: {e}")
    if st.button("Ejecutar Backtesting", key="run_bt"):
        with st.spinner("Cargando datos y modelo..."):
            collector = HistoricalDataCollector()
            try:
                if uploader is not None:
                    import pandas as _pd
                    dfh = _pd.read_csv(uploader)
                else:
                    import os as _os
                    if not _os.path.exists(historical_file):
                        st.warning("El archivo indicado no existe. Generando dataset sintético de ejemplo...")
                        df_soccer = generate_training_data("soccer", 500)
                        df_soccer['sport'] = 'soccer'
                        df_nba = generate_training_data("nba", 500)
                        df_nba['sport'] = 'nba'
                        combined = pd.concat([df_soccer, df_nba], ignore_index=True)
                        _os.makedirs("data", exist_ok=True)
                        combined.to_csv("data/historical_matches.csv", index=False)
                        historical_file = "data/historical_matches.csv"
                    dfh = collector.load_historical_matches(historical_file)
            except Exception as e:
                st.error(f"Error cargando datos históricos: {e}")
                st.stop()
            try:
                predictor = MatchPredictor(soccer_model_path=model_file)
            except Exception as e:
                st.error(f"Error cargando modelo: {e}")
                st.stop()
            criteria = {"min_probability": 0.65, "min_edge": 0.05}
            engine = BacktestEngine(initial_bankroll=1000)
            st.info("Ejecutando backtest, esto puede tardar unos minutos...")
            results = engine.run_backtest(dfh, predictor, criteria)
            if 'error' in results:
                st.error(results['error'])
            else:
                st.success("Backtesting completado!")
                st.json({k: v for k, v in results.items() if k not in ['daily_balance']})
                if 'daily_balance' in results:
                    daily_df = pd.DataFrame(results['daily_balance'])
                    st.line_chart(daily_df.set_index('date')['balance'])

with tab_realdata:
    st.subheader("🌐 Ingestión y Dataset Real")
    from src.scrapers.api_odds_fetcher import OddsAPIFetcher
    st.caption("Captura snapshots de odds, resultados y construye dataset de entrenamiento real.")
    col_ingest, col_build, col_result, col_dataset = st.columns(4)
    # Mostrar conteos actuales
    try:
        db.connect()
        cur_stats = db.conn.cursor()
        cur_stats.execute("SELECT COUNT(*) c FROM raw_odds_snapshots")
        raw_ct = cur_stats.fetchone()[0]
        cur_stats.execute("SELECT COUNT(*) c FROM canonical_odds")
        canon_ct = cur_stats.fetchone()[0]
        cur_stats.execute("SELECT COUNT(*) c FROM raw_match_results")
        res_ct = cur_stats.fetchone()[0]
        cur_stats.execute("SELECT COUNT(*) c FROM engineered_features")
        feat_ct = cur_stats.fetchone()[0]
        st.markdown(f"**Snapshots:** {raw_ct} | **Canonical:** {canon_ct} | **Resultados:** {res_ct} | **Features:** {feat_ct}")
    except Exception as e:
        st.warning(f"No se pudieron cargar estadísticas: {e}")

    with col_ingest:
        if st.button("Snapshot Odds Ahora", key="btn_snapshot"):
            fetcher = OddsAPIFetcher()
            with st.spinner("Consultando API de odds..."):
                matches = fetcher.get_available_matches("all")
                # Filtros de calidad (bookmakers >=2, odds válidas, odds <=20)
                filtered = []
                skipped = 0
                for m in matches:
                    odds = m.get('odds', {})
                    if m.get('bookmakers_count',0) < 2:
                        skipped +=1; continue
                    if not odds.get('home_win') or not odds.get('away_win'):
                        skipped +=1; continue
                    if odds.get('home_win',0) > 20 or odds.get('away_win',0) > 20:
                        skipped +=1; continue
                    filtered.append(m)
                inserted = db.save_odds_snapshot(filtered)
                st.success(f"Snapshot guardado: {inserted} partidos (skipped {skipped})")
    with col_build:
        if st.button("Build Canonical Odds", key="btn_canon"):
            with st.spinner("Construyendo odds canónicas..."):
                built = db.build_canonical_odds_bulk()
                st.success(f"Canonical odds generadas para {built} partidos nuevos")
    with col_result:
        st.write("Registrar resultado manual")
        with st.form("result_form"):
            match_id_f = st.text_input("match_id", placeholder="ID evento API")
            result_label_f = st.selectbox("Resultado", ["home_win","away_win","draw"], index=0)
            home_score_f = st.number_input("Home score", min_value=0, step=1)
            away_score_f = st.number_input("Away score", min_value=0, step=1)
            submitted = st.form_submit_button("Guardar Resultado")
            if submitted and match_id_f:
                db.save_match_result({
                    'match_id': match_id_f,
                    'sport': 'soccer',  # TODO derivar
                    'league': '',
                    'home_team': '',
                    'away_team': '',
                    'match_date': '',
                    'result_label': result_label_f,
                    'home_score': int(home_score_f),
                    'away_score': int(away_score_f)
                })
                st.success("Resultado guardado")
    with col_dataset:
        if st.button("Rebuild Training Dataset", key="btn_dataset"):
            with st.spinner("Generando features y dataset..."):
                db.build_basic_features()
                df_real = db.build_training_dataset(min_rows=30)
                if df_real is None:
                    st.warning("Dataset insuficiente, continuar con sintético.")
                else:
                    # Separar por deporte y guardar CSV consumido por train_model.py
                    try:
                        import os as _os
                        _os.makedirs("data", exist_ok=True)
                        df_soc = df_real[df_real['sport']== 'soccer']
                        df_nba = df_real[df_real['sport']== 'nba']
                        if not df_soc.empty:
                            df_soc.to_csv("data/training_real_soccer.csv", index=False)
                        if not df_nba.empty:
                            df_nba.to_csv("data/training_real_nba.csv", index=False)
                        st.success(f"Dataset real creado: soccer={len(df_soc)} filas, nba={len(df_nba)} filas")
                    except Exception as e:
                        st.error(f"Error guardando CSVs: {e}")

with tab_modelos:
    st.subheader("🧠 Entrenamiento de Modelos")
    st.caption("Re-entrena y monitorea el desempeño de los modelos.")
    if st.button("Entrenar Modelos Ahora", key="train_models"):
        with st.spinner("Entrenando modelos... esto puede tardar varios minutos"):
            proc = subprocess.run([sys.executable, "-m", "src.models.train_model"], capture_output=True, text=True)
            if proc.returncode != 0:
                st.error("Falló el entrenamiento")
                st.code(proc.stderr)
            else:
                st.success("Entrenamiento completado")
                st.code(proc.stdout)

    # Métricas históricas y alertas
    try:
        db.connect()
        cur = db.conn.cursor()
        cur.execute("SELECT sport, model_type, test_accuracy, cv_mean, log_loss, auc_ovr, dataset_hash, dataset_rows, dataset_cols, created_at FROM model_registry ORDER BY created_at ASC")
        rows = cur.fetchall()
        if rows:
            dfm = pd.DataFrame(rows, columns=['sport','model_type','test_accuracy','cv_mean','log_loss','auc_ovr','dataset_hash','dataset_rows','dataset_cols','created_at'])
            st.markdown("### 📈 Evolución de métricas")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.line_chart(dfm[['created_at','test_accuracy']].set_index('created_at'))
            with col_b:
                st.line_chart(dfm[['created_at','log_loss']].set_index('created_at'))
            with col_c:
                if dfm['auc_ovr'].notna().any():
                    st.line_chart(dfm[['created_at','auc_ovr']].set_index('created_at'))

            latest = dfm.iloc[-1]['test_accuracy']
            baseline = dfm['test_accuracy'][:-1].mean() if len(dfm) > 1 else latest
            if len(dfm) > 1 and latest < baseline - 0.03:
                st.warning(f"La última test_accuracy ({latest:.3f}) está >3 pts por debajo del promedio histórico ({baseline:.3f}). Revisar datos/modelo.")

            # Alerta por incremento de log_loss > 10%
            latest_ll = dfm.iloc[-1]['log_loss']
            baseline_ll = dfm['log_loss'][:-1].mean() if len(dfm) > 1 else latest_ll
            if len(dfm) > 1 and latest_ll > baseline_ll * 1.10:
                st.warning(f"El último log_loss ({latest_ll:.3f}) creció >10% sobre el promedio ({baseline_ll:.3f}). Posible descalibración o drift.")

            st.markdown("### 📋 Últimos registros")
            st.dataframe(dfm.tail(10))

            st.markdown("### 🧾 Detalles del último modelo")
            last = dfm.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("Test Acc", f"{last['test_accuracy']:.3f}")
            c2.metric("CV mean", f"{last['cv_mean']:.3f}")
            c3.metric("LogLoss", f"{last['log_loss']:.3f}")
            c1.metric("AUC (OVR)", f"{(last['auc_ovr'] if pd.notna(last['auc_ovr']) else 0):.3f}")
            c2.write(f"Dataset hash: {last['dataset_hash']}")
            c3.write(f"Dataset size: {int(last['dataset_rows'])}x{int(last['dataset_cols'])}")
        else:
            st.info("Aún no hay registros en model_registry. Entrena los modelos para generar métricas.")
    except Exception as e:
        st.warning(f"No se pudieron cargar métricas del registro: {e}")

with tab_hist:
    st.subheader("🗂️ Histórico de apuestas")
    bets = db.get_recent_bets(50)
    if bets:
        st.dataframe(pd.DataFrame(bets))
    else:
        st.info("Sin apuestas registradas.")

with tab_clv:
    st.subheader("📊 CLV Analytics - Closing Line Value")
    st.markdown("""
    **CLV (Closing Line Value)** es el mejor indicador de si eres un apostador rentable a largo plazo.
    
    - **CLV > 3%**: Eres un sharp bettor, rentable a largo plazo
    - **CLV > 0%**: Estás batiendo al mercado
    - **CLV < 0%**: El mercado tiene mejores odds que tú al cierre
    """)
    
    clv_tracker = CLVTracker()
    
    # Período de análisis
    days = st.selectbox("Período de análisis", [7, 30, 90], index=1)
    
    # Stats principales
    stats = clv_tracker.get_clv_stats(days=days)
    analysis = clv_tracker.analyze_clv_performance()
    
    st.markdown(f"### {analysis['rating']}")
    st.info(analysis['interpretation'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CLV Promedio", f"{stats['avg_clv_percentage']:.2f}%", 
                delta=f"{stats['avg_clv_percentage']:.2f}%")
    col2.metric("Total Apuestas", stats['total_bets'])
    col3.metric("CLV Positivos", f"{stats['positive_clv_rate']:.1f}%")
    col4.metric("Mejor CLV", f"{stats['max_clv_percentage']:.2f}%")
    
    # Historial CLV
    st.markdown("### 📈 Historial CLV")
    history = clv_tracker.get_clv_history(limit=50)
    
    if history:
        df_clv = pd.DataFrame(history)
        df_clv['created_at'] = pd.to_datetime(df_clv['created_at'])
        
        # Gráfico de CLV temporal
        st.line_chart(df_clv.set_index('created_at')['clv_percentage'])
        
        # Tabla detallada
        st.dataframe(df_clv[[
            'match_id', 'sport', 'opening_odds', 'bet_odds', 'closing_odds', 
            'clv_percentage', 'created_at'
        ]].style.background_gradient(subset=['clv_percentage'], cmap='RdYlGn'))
    else:
        st.info("No hay datos de CLV disponibles. Comienza a registrar apuestas con odds de apertura y cierre.")
    
    # Instrucciones
    with st.expander("ℹ️ ¿Cómo usar CLV Analytics?"):
        st.markdown("""
        **1. Registra odds de apertura**: Cuando detectes un partido, guarda las primeras odds
        
        **2. Registra tus apuestas**: Guarda las odds exactas a las que apostaste
        
        **3. Actualiza odds de cierre**: Justo antes del inicio del partido, registra las últimas odds
        
        **4. Analiza tu CLV**: El sistema calcula automáticamente si batiste al mercado
        
        **Ejemplo**:
        - Odds de apertura: 2.00
        - Apostaste a: 2.10
        - Odds de cierre: 1.95
        - **CLV = (1.95 / 2.10) - 1 = -7.14%** ❌ (negativo)
        
        **Objetivo**: CLV promedio > 3% en 100+ apuestas = sharp bettor
        """)
    
    clv_tracker.close()

st.markdown("---\n_Desarrollado como MVP rápido con Streamlit_")
