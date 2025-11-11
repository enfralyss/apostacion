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
tab_dashboard, tab_picks, tab_backtest, tab_realdata, tab_modelos, tab_hist, tab_clv, tab_params = st.tabs([
    "Dashboard", "Picks de hoy", "Backtesting", "Datos Reales", "Modelos", "Histórico", "CLV", "Parámetros"
 ])
import json
import datetime
from autotune import autotune_parameters
with tab_params:
    st.subheader("⚙️ Gestión de Parámetros y Autotuning")
    st.caption("Edita parámetros clave, lanza autotuning y restaura valores previos.")
    # Mostrar parámetros actuales
    params = db.get_all_parameters()
    if params:
        df_params = pd.DataFrame(params)
        # Mostrar columnas disponibles en la tabla actual
        cols = [c for c in ['name', 'value', 'updated_at'] if c in df_params.columns]
        st.dataframe(df_params[cols], use_container_width=True)
    else:
        st.info("No hay parámetros registrados en la base de datos.")
        # Opción para inicializar parámetros básicos desde config.yaml
        if st.button("Inicializar parámetros desde config.yaml", key="btn_seed_params"):
            try:
                import yaml as _yaml
                with open("config/config.yaml", "r", encoding="utf-8") as f:
                    cfg = _yaml.safe_load(f)
                picks_cfg = (cfg or {}).get('picks', {})
                for key in ['min_edge', 'min_probability', 'min_odds', 'max_odds']:
                    if key in picks_cfg:
                        db.set_parameter(key, picks_cfg[key])
                st.success("Parámetros inicializados desde config.yaml")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"No se pudieron inicializar parámetros: {e}")

    st.markdown("### ✏️ Editar Parámetro")
    param_names = [p['name'] for p in params] if params else []
    with st.form("edit_param_form"):
        param_to_edit = st.selectbox("Selecciona parámetro", param_names)
        current_value = next((p['value'] for p in params if p['name'] == param_to_edit), "") if param_to_edit else ""
        new_value = st.text_input("Nuevo valor", value=str(current_value))
        submit_edit = st.form_submit_button("Actualizar parámetro")
        if submit_edit:
            if not param_to_edit:
                st.warning("Selecciona un parámetro para actualizar.")
            else:
                db.set_parameter(param_to_edit, new_value)
                st.success(f"Parámetro '{param_to_edit}' actualizado a {new_value}")
                st.experimental_rerun()

    # Crear nuevo parámetro
    with st.expander("➕ Agregar nuevo parámetro"):
        with st.form("add_param_form"):
            new_name = st.text_input("Nombre del parámetro")
            new_val = st.text_input("Valor")
            submit_new = st.form_submit_button("Crear parámetro")
            if submit_new:
                if not new_name:
                    st.warning("Debes indicar un nombre para el parámetro.")
                else:
                    db.set_parameter(new_name, new_val)
                    st.success(f"Parámetro '{new_name}' creado.")
                    st.experimental_rerun()

    st.markdown("### 🤖 Autotuning de Parámetros")
    st.info("Lanza una búsqueda automática de los mejores parámetros para selección de picks. Esto puede tardar varios minutos.")
    if st.button("Ejecutar Autotuning", key="btn_autotune"):
        with st.spinner("Ejecutando autotuning (rápido)..."):
            # Limitar tamaño y combinaciones para evitar bloqueos largos en UI
            result = autotune_parameters(db, sample_size=200, max_combinations=24, time_limit_sec=120)
            if result and result.get('best_params') is not None:
                best = result.get('best_metrics', {})
                st.success(f"Mejores parámetros encontrados: {json.dumps(result['best_params'])}")
                # Guardar en DB
                for k, v in result['best_params'].items():
                    db.set_parameter(k, v)
                st.info("Parámetros óptimos aplicados.")
                # Métricas
                colm1, colm2, colm3, colm4, colm5 = st.columns(5)
                colm1.metric("ROI", f"{best.get('roi',0):.2%}")
                colm2.metric("Win Rate", f"{best.get('win_rate',0):.1%}")
                colm3.metric("Geo Growth (log)", f"{best.get('geo_growth',0):.4f}")
                colm4.metric("Volatilidad", f"{best.get('volatility',0):.2f}")
                colm5.metric("Score", f"{best.get('score',0):.3f}")
                # Mostrar resumen de pruebas
                tested = result.get('tested', [])
                st.caption(f"Combinaciones evaluadas: {len(tested)}")
                if tested:
                    with st.expander("Detalle de combinaciones evaluadas"):
                        import pandas as _pd
                        df_t = _pd.DataFrame([
                            {
                                **t['params'],
                                'roi': t['metrics'].get('roi'),
                                'win_rate': t['metrics'].get('win_rate'),
                                'geo_growth': t['metrics'].get('geo_growth'),
                                'volatility': t['metrics'].get('volatility'),
                                'score': t['metrics'].get('score'),
                                'n': t['metrics'].get('n')
                            } for t in tested
                        ])
                        st.dataframe(df_t.sort_values('score', ascending=False), use_container_width=True)
            else:
                st.error("❌ No se encontraron parámetros óptimos.")
                st.warning("""
                **Posibles causas:**
                - No hay suficientes datos históricos en la base de datos (se necesitan partidos con resultados en `raw_match_results` y odds en `canonical_odds`)
                - Ninguna combinación de parámetros cumplió con el criterio mínimo (n > 20 picks)
                - El tiempo de ejecución se agotó antes de encontrar buenos parámetros
                
                **Soluciones:**
                - Ejecuta el bootstrap de datos históricos: `python bootstrap_historical_data.py`
                - Aumenta el `sample_size` o `max_combinations` en el código
                - Revisa que tengas modelos entrenados (`models/soccer_model.pkl`, `models/nba_model.pkl`)
                """)
                # Mostrar combinaciones evaluadas para debug
                tested = result.get('tested', []) if result else []
                if tested:
                    st.info(f"Se evaluaron {len(tested)} combinaciones, pero ninguna fue lo suficientemente buena.")
                    with st.expander("🔍 Ver combinaciones evaluadas (debug)"):
                        import pandas as _pd
                        df_t = _pd.DataFrame([
                            {
                                **t['params'],
                                'roi': t['metrics'].get('roi'),
                                'win_rate': t['metrics'].get('win_rate'),
                                'n': t['metrics'].get('n'),
                                'score': t['metrics'].get('score')
                            } for t in tested
                        ])
                        st.dataframe(df_t.sort_values('score', ascending=False), use_container_width=True)
                else:
                    st.warning("No se pudo evaluar ninguna combinación. Verifica que tengas datos históricos.")

    st.markdown("### 🕑 Historial de Cambios de Parámetros")
    # Suponiendo que hay un método get_parameter_history()
    try:
        history = db.get_parameter_history(limit=50) if hasattr(db, 'get_parameter_history') else []
    except Exception:
        history = []
    if history:
        df_hist = pd.DataFrame(history)
        df_hist['changed_at'] = pd.to_datetime(df_hist['changed_at'])
        st.dataframe(df_hist[['name', 'old_value', 'new_value', 'changed_at']], use_container_width=True)
        st.markdown("#### Restaurar valor previo")
        with st.form("restore_param_form"):
            hist_options = [f"{row['name']} @ {row['changed_at']}" for _, row in df_hist.iterrows()]
            restore_sel = st.selectbox("Selecciona cambio a restaurar", hist_options)
            submit_restore = st.form_submit_button("Restaurar")
            if submit_restore and restore_sel:
                idx = hist_options.index(restore_sel)
                row = df_hist.iloc[idx]
                db.set_parameter(row['name'], row['old_value'])
                st.success(f"Parámetro '{row['name']}' restaurado a valor previo: {row['old_value']}")
    else:
        st.info("No hay historial de cambios de parámetros disponible.")

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
        # Enriquecer con ventana de fechas de partidos y renombrar columnas para mayor claridad
        enriched_rows = []
        for b in bets:
            picks = db.get_bet_picks(b['id'])
            # Extraer fechas de los partidos (si existen en picks)
            dates = sorted({p.get('match_date') for p in picks if p.get('match_date')})
            if dates:
                match_window = dates[0] if len(dates) == 1 else f"{dates[0]} → {dates[-1]} ({len(dates)} partidos)"
            else:
                match_window = None
            # Añadir número real de picks (por si num_picks está desfasado)
            b_copy = dict(b)
            b_copy['match_window'] = match_window
            b_copy['real_num_picks'] = len(picks)
            enriched_rows.append(b_copy)
        df_hist_bets = pd.DataFrame(enriched_rows)
        # Mapeo de nombres amigables
        col_map = {
            'id': 'Bet ID',
            'bet_date': 'Fecha apuesta',
            'sport': 'Deporte',
            'bet_type': 'Tipo',
            'num_picks': 'Picks (decl.)',
            'real_num_picks': 'Picks reales',
            'match_window': 'Fecha(s) partidos',
            'total_odds': 'Cuota Total',
            'stake': 'Stake',
            'potential_return': 'Retorno Potencial',
            'status': 'Estado',
            'result': 'Resultado',
            'profit_loss': 'P/L',
            'bankroll_before': 'Bankroll Antes',
            'bankroll_after': 'Bankroll Después',
            'opening_odds': 'Odds Apertura',
            'closing_odds': 'Odds Cierre',
            'clv_percentage': 'CLV %',
            'placed_odds': 'Odds Colocadas',
            'adjusted_stake': 'Stake Ajustado',
            'edge_at_recommendation': 'Edge (Recomendación)',
            'edge_at_placement': 'Edge (Colocación)',
            'created_at': 'Creada',
            'settled_at': 'Cerrada',
            'notes': 'Notas'
        }
        # Reordenar columnas principales para lectura
        preferred_order = [
            'Bet ID','Fecha apuesta','Fecha(s) partidos','Tipo','Deporte','Picks reales','Picks (decl.)',
            'Cuota Total','Stake','Retorno Potencial','Odds Apertura','Odds Colocadas','Odds Cierre','CLV %',
            'Edge (Recomendación)','Edge (Colocación)','Estado','Resultado','P/L','Bankroll Antes','Bankroll Después',
            'Creada','Cerrada','Notas'
        ]
        df_display = df_hist_bets.rename(columns=col_map)
        # Añadir columnas faltantes sin romper
        existing_order = [c for c in preferred_order if c in df_display.columns]
        other_cols = [c for c in df_display.columns if c not in existing_order]
        df_display = df_display[existing_order + other_cols]
        st.dataframe(df_display, use_container_width=True)
        st.markdown("### 🔔 Resolver Picks Pendientes")
        if st.button("Resolver y Notificar Picks", key="btn_resolve_picks"):
            resolved = db.resolve_pending_picks()
            if not resolved:
                st.info("No hay picks pendientes con resultados disponibles.")
            else:
                st.success(f"{len(resolved)} picks resueltos")
                # Enviar notificaciones individuales
                try:
                    from src.utils.notifications import TelegramNotifier
                    notifier = TelegramNotifier()
                    if notifier.enabled:
                        sent = 0
                        for info in resolved:
                            cur = db.conn.cursor()
                            cur.execute('SELECT league, home_team, away_team, prediction, odds, predicted_probability, edge FROM picks WHERE id=?', (info['pick_id'],))
                            prow = cur.fetchone()
                            pick_detail = dict(prow) if prow else {}
                            pick_detail.update(info)
                            if notifier.send_pick_result(pick_detail):
                                sent += 1
                        st.info(f"Notificaciones enviadas: {sent}")
                    else:
                        st.warning("Telegram no está configurado (faltan credenciales).")
                except Exception as e:
                    st.error(f"Error enviando notificaciones: {e}")
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
