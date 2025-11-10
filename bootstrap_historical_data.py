"""
Bootstrap Historical Data - Carga datos históricos para entrenar el modelo
Este script se ejecuta UNA VEZ al inicio para llenar la base de datos
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.scrapers.api_odds_fetcher import OddsAPIFetcher
from src.scrapers.historical_odds_scraper import FootballDataUK
from src.utils.database import BettingDatabase
from src.utils.notifications import TelegramNotifier
from datetime import datetime, timedelta
from loguru import logger
import time

class HistoricalDataBootstrap:
    """
    Bootstrap de datos históricos para entrenar el modelo

    Estrategia:
    1. Consulta scores de los últimos 30-90 días
    2. Para cada partido finalizado, busca sus odds originales (si están disponibles)
    3. Guarda en la base de datos como si fueran datos capturados en tiempo real
    4. Permite al modelo entrenarse inmediatamente con datos reales
    """

    def __init__(self):
        self.db = BettingDatabase()
        self.odds_fetcher = OddsAPIFetcher()
        self.historical_scraper = FootballDataUK()
        self.notifier = TelegramNotifier()

    def fetch_historical_scores(self, days_back: int = 30) -> dict:
        """
        Obtiene resultados históricos de partidos finalizados

        Args:
            days_back: Días hacia atrás para consultar (máximo 90)

        Returns:
            Dict con scores por deporte
        """
        logger.info(f"Fetching historical scores from last {days_back} days...")

        all_scores = {
            'soccer': [],
            'nba': []
        }

        # The Odds API permite consultar scores hasta 3 días atrás en plan gratuito
        # Para más historia, necesitamos el endpoint premium o hacer requests incrementales

        # Estrategia: Hacer requests cada 3 días hacia atrás
        max_days_per_request = 3
        requests_needed = (days_back // max_days_per_request) + 1

        logger.info(f"Will need ~{requests_needed} requests per league to fetch {days_back} days")
        logger.warning(f"This will consume ~{requests_needed * 6} API requests total")

        # Consultar últimos 3 días (gratis)
        scores = self.odds_fetcher.fetch_scores("all", days_from=3)

        for score in scores:
            sport = score.get('sport')
            if sport == 'soccer':
                all_scores['soccer'].append(score)
            elif sport == 'nba':
                all_scores['nba'].append(score)

        logger.info(f"Fetched {len(all_scores['soccer'])} soccer scores, {len(all_scores['nba'])} NBA scores")

        return all_scores

    def generate_synthetic_odds_for_historical(self, score: dict) -> dict:
        """
        Genera odds sintéticas realistas basadas en el resultado

        Args:
            score: Score de un partido finalizado

        Returns:
            Match con odds sintéticas agregadas
        """
        result = score['result_label']
        home_score = score['home_score']
        away_score = score['away_score']

        # Generar odds realistas basadas en el resultado
        # Si ganó local por mucho, las odds de local eran bajas

        if result == 'home_win':
            # Local ganó - odds de local más bajas
            if score['sport'] == 'soccer':
                goal_diff = home_score - away_score
                if goal_diff >= 3:
                    # Goleada local - local era favorito claro
                    home_odds = 1.5 + (goal_diff * 0.1)
                    away_odds = 5.0 - (goal_diff * 0.2)
                    draw_odds = 3.5
                else:
                    # Victoria ajustada
                    home_odds = 2.0
                    away_odds = 3.5
                    draw_odds = 3.2
            else:  # NBA
                home_odds = 1.8
                away_odds = 2.1
                draw_odds = None

        elif result == 'away_win':
            # Visitante ganó - odds de visitante más bajas
            if score['sport'] == 'soccer':
                goal_diff = away_score - home_score
                if goal_diff >= 3:
                    home_odds = 5.0 - (goal_diff * 0.2)
                    away_odds = 1.5 + (goal_diff * 0.1)
                    draw_odds = 3.5
                else:
                    home_odds = 3.5
                    away_odds = 2.0
                    draw_odds = 3.2
            else:  # NBA
                home_odds = 2.1
                away_odds = 1.8
                draw_odds = None

        else:  # draw
            home_odds = 2.8
            away_odds = 2.8
            draw_odds = 3.0

        # Agregar ruido aleatorio realista (+/- 10%)
        import random
        home_odds *= random.uniform(0.9, 1.1)
        away_odds *= random.uniform(0.9, 1.1)
        if draw_odds:
            draw_odds *= random.uniform(0.9, 1.1)

        # Redondear
        odds_dict = {
            'home_win': round(home_odds, 2),
            'away_win': round(away_odds, 2)
        }

        if draw_odds:
            odds_dict['draw'] = round(draw_odds, 2)

        # Crear match con odds
        match = {
            'match_id': score['match_id'],
            'sport': score['sport'],
            'league': score['league'],
            'home_team': score['home_team'],
            'away_team': score['away_team'],
            'match_date': score['match_date'],
            'odds': odds_dict,
            'bookmakers_count': 3,  # Simulado
            'historical_bootstrap': True  # Flag para identificar datos de bootstrap
        }

        return match

    def bootstrap_database(self, months_back: int = 3, use_real_odds: bool = True):
        """
        Ejecuta el bootstrap completo de la base de datos

        Args:
            months_back: Meses hacia atrás para cargar (1-12)
            use_real_odds: Si True, usa Football-Data.co.uk (GRATIS, REAL), si False usa odds sintéticas
        """
        logger.info("="*70)
        logger.info("HISTORICAL DATA BOOTSTRAP")
        logger.info("="*70)

        # 1. Fetch datos históricos REALES con odds
        self.notifier.send_message(
            f"*BOOTSTRAP INICIADO*\n\n"
            f"Cargando datos historicos REALES de los ultimos {months_back} meses...\n"
            f"Esto puede tomar varios minutos.\n"
            f"Fuente: Football-Data.co.uk (GRATIS)"
        )

        all_matches = []

        if use_real_odds:
            # Usar Football-Data.co.uk - GRATIS y con odds reales
            logger.info("\nFetching REAL historical data from Football-Data.co.uk...")
            try:
                historical_matches = self.historical_scraper.fetch_historical_data(months_back=months_back)
                all_matches.extend(historical_matches)
                logger.info(f"Fetched {len(historical_matches)} matches with REAL odds")
            except Exception as e:
                logger.error(f"Error fetching from Football-Data.co.uk: {e}")
                logger.warning("Falling back to synthetic odds...")
                use_real_odds = False

        # Fallback a odds sintéticas si falla
        if not use_real_odds or len(all_matches) == 0:
            logger.info("\nUsing synthetic odds (fallback)...")
            days_back = months_back * 30
            scores_dict = self.fetch_historical_scores(days_back)

            for score in scores_dict['soccer'] + scores_dict['nba']:
                match = self.generate_synthetic_odds_for_historical(score)
                all_matches.append(match)

        if len(all_matches) == 0:
            logger.warning("No historical data found")
            self.notifier.send_message("No se encontraron datos historicos.")
            return

        logger.info(f"\nTotal matches to process: {len(all_matches)}")

        # 2. Guardar en base de datos
        logger.info("\nSaving to database...")

        # Separar matches con resultados vs sin resultados
        matches_with_results = [m for m in all_matches if m.get('completed')]
        matches_without_results = [m for m in all_matches if not m.get('completed')]

        # Guardar odds snapshot
        inserted = self.db.save_odds_snapshot(all_matches)

        # Build canonical odds
        built = self.db.build_canonical_odds_bulk()

        logger.info(f"Saved {inserted} matches, built {built} canonical odds")

        # 3. Guardar resultados (solo para matches completados)
        logger.info("\nSaving results...")

        saved_results = 0
        for match in matches_with_results:
            try:
                self.db.save_match_result(match)
                saved_results += 1
            except Exception as e:
                logger.debug(f"Could not save result: {e}")

        logger.info(f"Saved {saved_results} match results")

        # 5. Build features y training dataset
        logger.info("\nBuilding features and training dataset...")

        self.db.build_basic_features()
        df_training = self.db.build_training_dataset(min_rows=20)

        if df_training is not None:
            # Separar por deporte
            import pandas as pd
            df_soc = df_training[df_training['sport'] == 'soccer']
            df_nba = df_training[df_training['sport'] == 'nba']

            os.makedirs("data", exist_ok=True)
            if not df_soc.empty:
                df_soc.to_csv("data/training_real_soccer.csv", index=False)
                logger.info(f"Saved soccer training data: {len(df_soc)} rows")
            if not df_nba.empty:
                df_nba.to_csv("data/training_real_nba.csv", index=False)
                logger.info(f"Saved NBA training data: {len(df_nba)} rows")

            # 6. Re-entrenar modelos
            logger.info("\nRe-training models with historical data...")

            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "src.models.train_model"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info("Models trained successfully!")

                # Notificación final
                self.notifier.send_message(
                    f"*BOOTSTRAP COMPLETADO*\n\n"
                    f"Datos cargados:\n"
                    f"- Soccer: {len(df_soc)} partidos\n"
                    f"- NBA: {len(df_nba)} partidos\n\n"
                    f"Modelos entrenados con exito!\n"
                    f"El sistema esta listo para hacer predicciones."
                )
            else:
                logger.error(f"Model training failed: {result.stderr}")
                self.notifier.send_message(
                    f"Bootstrap completado pero fallo entrenamiento:\n{result.stderr[:200]}"
                )
        else:
            logger.warning("Insufficient data for training dataset")
            self.notifier.send_message(
                "Bootstrap completado pero datos insuficientes para entrenar."
            )

        logger.info("="*70)
        logger.info("BOOTSTRAP COMPLETED")
        logger.info("="*70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Bootstrap historical betting data')
    parser.add_argument('--months', type=int, default=3,
                       help='Months of historical data to load (1-12, default: 3)')
    parser.add_argument('--synthetic', action='store_true',
                       help='Use synthetic odds instead of real ones')

    args = parser.parse_args()

    bootstrap = HistoricalDataBootstrap()

    # Ejecutar bootstrap con datos REALES
    logger.info(f"Starting bootstrap: {args.months} months back")
    logger.info(f"Using {'SYNTHETIC' if args.synthetic else 'REAL'} odds")

    bootstrap.bootstrap_database(
        months_back=args.months,
        use_real_odds=not args.synthetic
    )
