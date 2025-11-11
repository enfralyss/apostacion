"""
Scheduler automatizado - Ejecuta crons para mantener el sistema actualizado 24/7
"""

import os
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.scrapers.api_odds_fetcher import OddsAPIFetcher
from src.utils.database import BettingDatabase
from src.utils.notifications import TelegramNotifier
from src.utils.clv_tracker import CLVTracker
from src.models.predictor import MatchPredictor
from src.betting.pick_selector import PickSelector
from src.betting.parlay_builder import ParlayBuilder
import subprocess


class BettingScheduler:
    """Scheduler que automatiza todo el pipeline"""

    def __init__(self):
        self.db = BettingDatabase()
        self.odds_fetcher = OddsAPIFetcher()
        self.notifier = TelegramNotifier()
        self.scheduler = BlockingScheduler()
        self.clv = CLVTracker()
        
        logger.info("🤖 Betting Scheduler initialized")

    def job_capture_odds(self):
        """CRON 1: Captura odds de partidos disponibles"""
        try:
            logger.info("📊 [CRON] Starting odds capture...")
            
            # Fetch odds from API
            matches = self.odds_fetcher.get_available_matches("soccer")
            
            if not matches:
                logger.warning("No matches available from API")
                return
            
            # Aplicar filtros de calidad
            filtered = []
            skipped = 0
            for m in matches:
                odds = m.get('odds', {})
                if m.get('bookmakers_count', 0) < 2:
                    skipped += 1
                    continue
                if not odds.get('home_win') or not odds.get('away_win'):
                    skipped += 1
                    continue
                if odds.get('home_win', 0) > 20 or odds.get('away_win', 0) > 20:
                    skipped += 1
                    continue
                filtered.append(m)
            
            # Guardar en DB
            inserted = self.db.save_odds_snapshot(filtered)
            
            # Build canonical odds
            built = self.db.build_canonical_odds_bulk()
            
            logger.info(f"✅ Odds captured: {inserted} matches saved, {built} canonical odds built (skipped {skipped})")
            
            # Notificación
            self.notifier.send_message(
                f"📊 Odds Snapshot\n\n"
                f"✅ {inserted} partidos capturados\n"
                f"🎯 {built} odds canónicas generadas\n"
                f"⏭️ {skipped} partidos omitidos por calidad"
            )
            
        except Exception as e:
            logger.error(f"Error in odds capture job: {e}")
            self.notifier.send_message(f"❌ Error capturando odds: {e}")

    def job_update_results(self):
        """CRON 2: Actualiza resultados de partidos finalizados"""
        try:
            logger.info("🏆 [CRON] Starting results update...")
            
            # Fetch scores from API
            scores = self.odds_fetcher.fetch_scores("soccer")
            
            if not scores:
                logger.info("No new scores available")
                return
            
            # Guardar resultados en DB
            saved = 0
            for score in scores:
                try:
                    self.db.save_match_result(score)
                    saved += 1
                except Exception as e:
                    logger.debug(f"Could not save result for {score.get('match_id')}: {e}")
            
            logger.info(f"✅ Results updated: {saved} matches")
            
            if saved > 0:
                self.notifier.send_message(
                    f"🏆 Resultados Actualizados\n\n"
                    f"✅ {saved} partidos finalizados registrados\n"
                    f"📊 Dataset listo para actualizar"
                )
                # Resolver picks pendientes y notificar
                resolved = self.db.resolve_pending_picks()
                for info in resolved:
                    # Enriquecer con datos del pick para el mensaje
                    try:
                        c = self.db.conn.cursor()
                        c.execute('SELECT league, home_team, away_team, prediction, odds, predicted_probability, edge FROM picks WHERE id=?', (info['pick_id'],))
                        prow = c.fetchone()
                        pick_detail = dict(prow) if prow else {}
                        pick_detail.update(info)
                        self.notifier.send_pick_result(pick_detail)
                    except Exception:
                        pass
            
        except Exception as e:
            logger.error(f"Error in results update job: {e}")
            self.notifier.send_message(f"❌ Error actualizando resultados: {e}")

    def job_update_closing_odds(self):
        """CRON 2b: Actualiza closing odds para apuestas pendientes y calcula CLV por bet."""
        try:
            logger.info("⏱️ [CRON] Updating closing odds for pending bets...")
            pending = self.db.get_pending_bets()
            if not pending:
                logger.info("No pending bets to update closing odds")
                return
            updated = 0
            for bet in pending:
                bet_id = bet['id']
                picks = self.db.get_picks_for_bet(bet_id)
                if not picks:
                    continue
                # Calcular closing odds del parlay multiplicando últimas odds de cada pick
                closing_total_odds = 1.0
                for p in picks:
                    latest = self.db.get_latest_odds_for_match(p['match_id'], p['prediction'])
                    # Si no hay latest, usar canonical como fallback
                    if latest is None:
                        latest = p.get('odds')
                    if latest and latest > 0:
                        closing_total_odds *= latest
                if closing_total_odds <= 1.0:
                    continue
                # Guardar closing y CLV% a nivel bet
                if self.db.update_bet_closing_odds(bet_id, closing_total_odds):
                    updated += 1
            if updated:
                self.notifier.send_message(f"📈 Closing odds actualizadas para {updated} apuestas (CLV recalculado)")
        except Exception as e:
            logger.error(f"Error updating closing odds: {e}")

    def job_rebuild_dataset(self):
        """CRON 3: Rebuild training dataset y re-entrena modelo"""
        try:
            logger.info("🔧 [CRON] Starting dataset rebuild and model training...")
            
            # Build features
            self.db.build_basic_features()
            
            # Build training dataset
            df_real = self.db.build_training_dataset(min_rows=30)
            
            if df_real is None:
                logger.warning("Insufficient real data, models will use synthetic fallback")
                self.notifier.send_message(
                    "⚠️ Dataset Insuficiente\n\n"
                    "Aún no hay suficientes datos reales.\n"
                    "Modelos usan datos sintéticos por ahora."
                )
                return
            
            # Separar por deporte y guardar CSVs
            import pandas as pd
            df_soc = df_real[df_real['sport'] == 'soccer']
            df_nba = df_real[df_real['sport'] == 'nba']
            
            os.makedirs("data", exist_ok=True)
            if not df_soc.empty:
                df_soc.to_csv("data/training_real_soccer.csv", index=False)
            if not df_nba.empty:
                df_nba.to_csv("data/training_real_nba.csv", index=False)
            
            logger.info(f"✅ Dataset built: soccer={len(df_soc)} rows, nba={len(df_nba)} rows")
            
            # Re-entrenar modelos
            logger.info("🧠 Re-training models...")
            result = subprocess.run(
                [sys.executable, "-m", "src.models.train_model"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Models re-trained successfully")
                self.notifier.send_message(
                    f"🧠 Modelos Re-entrenados\n\n"
                    f"📊 Soccer: {len(df_soc)} partidos reales\n"
                    f"🏀 NBA: {len(df_nba)} partidos reales\n"
                    f"✅ Entrenamiento exitoso"
                )
            else:
                logger.error(f"Model training failed: {result.stderr}")
                self.notifier.send_message(f"❌ Error entrenando modelos:\n{result.stderr[:200]}")
            
        except Exception as e:
            logger.error(f"Error in dataset rebuild job: {e}")
            self.notifier.send_message(f"❌ Error rebuild dataset: {e}")

    def job_generate_picks(self):
        """CRON 4: Genera picks diarios y notifica"""
        try:
            logger.info("🎯 [CRON] Generating daily picks...")
            
            # Ejecutar análisis
            result = subprocess.run(
                [sys.executable, "bot_real.py"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Bot execution failed: {result.stderr}")
                return
            
            # Obtener picks recientes de la DB
            recent_bets = self.db.get_recent_bets(1)
            
            if not recent_bets:
                logger.info("No new picks generated")
                return
            
            bet = recent_bets[0]
            picks = self.db.get_bet_picks(bet['id'])
            
            # Formatear mensaje para Telegram
            message = f"🎯 *PICKS DE HOY*\n\n"
            message += f"💰 Bankroll: VES {bet['bankroll_before']:,.2f}\n"
            message += f"💵 Stake: VES {bet['stake']:,.2f}\n"
            message += f"📊 Cuota Total: {bet['total_odds']:.2f}\n"
            message += f"🎁 Retorno Potencial: VES {bet['potential_return']:,.2f}\n\n"
            message += f"*Partidos ({len(picks)}):*\n\n"
            
            for i, pick in enumerate(picks, 1):
                message += f"{i}. {pick['league']}\n"
                message += f"   {pick['home_team']} vs {pick['away_team']}\n"
                message += f"   ✅ Pick: *{pick['prediction']}*\n"
                message += f"   📈 Odds: {pick['odds']} | Prob: {pick['predicted_probability']*100:.1f}% | Edge: {pick['edge']*100:.1f}%\n\n"
            
            message += f"🔗 [Apostar en TriunfoBet](https://triunfobet.com)\n"
            message += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # CLV stats para enriquecer notificación
            try:
                clv_stats = self.clv.get_clv_stats(days=30)
            except Exception:
                clv_stats = None

            # Enviar notificación con CLV
            try:
                # Reusar método rico si disponible
                self.notifier.send_daily_picks(picks, {
                    'picks': picks,
                    'total_odds': bet['total_odds'],
                    'combined_probability': bet.get('combined_probability', 0.0)
                }, bet['stake'], bet['bankroll_before'], clv_stats=clv_stats)
            except Exception:
                self.notifier.send_message(message)
            logger.info(f"✅ Picks notification sent: {len(picks)} picks")
            
        except Exception as e:
            logger.error(f"Error in generate picks job: {e}")
            self.notifier.send_message(f"❌ Error generando picks: {e}")

    def start(self):
        """Inicia el scheduler con todos los crons configurados"""
        
        # CRON 1: Captura odds - Diario a las 14:00 (2 PM)
        self.scheduler.add_job(
            self.job_capture_odds,
            CronTrigger(hour=14, minute=0),
            id='capture_odds',
            name='Capture Odds Daily',
            replace_existing=True
        )
        logger.info("✅ Scheduled: Capture odds daily at 14:00")
        
        # CRON 2: Actualizar resultados - Cada 6 horas
        self.scheduler.add_job(
            self.job_update_results,
            CronTrigger(hour='*/6'),
            id='update_results',
            name='Update Results Every 6h',
            replace_existing=True
        )
        logger.info("✅ Scheduled: Update results every 6 hours")

        # CRON 2b: Actualizar closing odds - Cada 30 minutos
        self.scheduler.add_job(
            self.job_update_closing_odds,
            CronTrigger(minute='*/30'),
            id='update_closing_odds',
            name='Update Closing Odds Every 30m',
            replace_existing=True
        )
        logger.info("✅ Scheduled: Update closing odds every 30 minutes")
        
        # CRON 3: Rebuild dataset + re-entrenar - Domingos a las 3 AM
        self.scheduler.add_job(
            self.job_rebuild_dataset,
            CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='rebuild_dataset',
            name='Rebuild Dataset Weekly',
            replace_existing=True
        )
        logger.info("✅ Scheduled: Rebuild dataset & retrain models every Sunday at 03:00")
        
        # CRON 4: Generar picks - Diario a las 8 AM
        self.scheduler.add_job(
            self.job_generate_picks,
            CronTrigger(hour=8, minute=0),
            id='generate_picks',
            name='Generate Daily Picks',
            replace_existing=True
        )
        logger.info("✅ Scheduled: Generate picks daily at 08:00")
        
    # Ejecutar capture odds inmediatamente al inicio (opcional)
        logger.info("🚀 Running initial odds capture...")
        self.job_capture_odds()
        
        # Iniciar scheduler
        logger.info("🤖 Scheduler started! Running 24/7...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
            self.scheduler.shutdown()


if __name__ == "__main__":
    scheduler = BettingScheduler()
    scheduler.start()
