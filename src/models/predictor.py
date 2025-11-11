"""
Predictor - Usa modelos entrenados para predecir resultados de partidos
Actualizado para usar EnsembleModel o CalibratedBettingModel con features avanzadas
"""

import pandas as pd
from typing import Dict
from loguru import logger
from src.models.ensemble_model import EnsembleBettingModel
from src.models.calibrated_model_simple import CalibratedBettingModel
from src.models.train_model import BettingModel  # Fallback para NBA
from src.data.feature_integration import calculate_match_features_advanced
from src.utils.database import BettingDatabase
import os


class MatchPredictor:
    """Predictor de resultados de partidos"""

    def __init__(self,
                 soccer_model_path: str = "models/soccer_ensemble.pkl",
                 nba_model_path: str = "models/nba_model.pkl",
                 use_ensemble: bool = True):
        """
        Args:
            soccer_model_path: Ruta al modelo de fútbol (ensemble por defecto)
            nba_model_path: Ruta al modelo de NBA
            use_ensemble: Si True, intenta cargar ensemble primero, luego calibrado
        """
        # Cargar modelo de soccer con prioridad: Ensemble > Calibrado > Antiguo
        self.soccer_model = None
        self.model_type = None
        self.is_calibrated = False

        # 1. Intentar cargar ENSEMBLE (mejor opción)
        if use_ensemble:
            ensemble_path = "models/soccer_ensemble.pkl"
            if os.path.exists(ensemble_path):
                try:
                    self.soccer_model = EnsembleBettingModel.load(ensemble_path)
                    self.model_type = "ensemble"
                    self.is_calibrated = True
                    logger.info(f"✅ Soccer ENSEMBLE model loaded from {ensemble_path}")
                    logger.info(f"   Models: XGBoost + LightGBM + Random Forest")
                except Exception as e:
                    logger.warning(f"Could not load ensemble model: {e}")

        # 2. Fallback: Modelo calibrado simple
        if self.soccer_model is None:
            calibrated_path = "models/soccer_calibrated_advanced.pkl"
            if os.path.exists(calibrated_path):
                try:
                    self.soccer_model = CalibratedBettingModel.load(calibrated_path)
                    self.model_type = "calibrated_simple"
                    self.is_calibrated = True
                    logger.info(f"✅ Soccer CALIBRATED (simple) model loaded from {calibrated_path}")
                except Exception as e:
                    logger.warning(f"Could not load calibrated model: {e}")

        # 3. Fallback final: Modelo antiguo sin calibrar
        if self.soccer_model is None:
            fallback_path = "models/soccer_model.pkl"
            try:
                self.soccer_model = BettingModel.load(fallback_path)
                self.model_type = "legacy"
                logger.warning(f"⚠️ Using LEGACY (uncalibrated) soccer model from {fallback_path}")
                logger.warning("   Train advanced model with: python train_ensemble_model.py")
            except FileNotFoundError:
                logger.error(f"❌ No soccer model found")
                self.soccer_model = None

        # NBA model (sin calibrar por ahora)
        try:
            self.nba_model = BettingModel.load(nba_model_path)
            logger.info("NBA model loaded successfully")
        except FileNotFoundError:
            logger.warning(f"NBA model not found at {nba_model_path}")
            self.nba_model = None

        # Use database for feature calculation (same as training)
        self.db = BettingDatabase()

    def predict_match(self, match: Dict) -> Dict:
        """
        Predice el resultado de un partido usando features de la base de datos

        Args:
            match: Diccionario con información del partido (de API)
                   Debe incluir: home_team, away_team, sport, league, match_date, odds

        Returns:
            Diccionario con predicciones y probabilidades
        """
        sport = match['sport']
        home_team = match['home_team']
        away_team = match['away_team']

        logger.info(f"Predicting: {home_team} vs {away_team} ({sport})")

        # Seleccionar modelo
        model = self.soccer_model if sport == "soccer" else self.nba_model

        if model is None:
            logger.error(f"Model for {sport} not loaded")
            return {
                'error': f'Model for {sport} not available',
                'probabilities': {}
            }

        # Calcular features - usar avanzadas si modelo calibrado
        if sport == "soccer" and self.is_calibrated:
            # Modelo calibrado: usar features avanzadas (ELO, form, H2H, etc.)
            try:
                features_dict = calculate_match_features_advanced(match, self.db)
            except Exception as e:
                logger.error(f"Error calculating advanced features: {e}")
                return {
                    'error': f'Could not calculate advanced features: {str(e)}',
                    'probabilities': {}
                }
        else:
            # Modelo antiguo o NBA: usar features básicas
            features_dict = self.db.calculate_match_features(match)

        if features_dict is None:
            logger.warning(f"Could not calculate features for {home_team} vs {away_team}")
            return {
                'error': 'Could not calculate features',
                'probabilities': {}
            }

        # Convertir a DataFrame
        features_df = pd.DataFrame([features_dict])

        # Predecir
        probabilities = model.predict_proba(features_df)
        prediction = model.predict(features_df)

        # Calcular confianza (probabilidad de la predicción)
        confidence = probabilities[prediction]

        result = {
            'match_id': match['match_id'],
            'sport': sport,
            'league': match['league'],
            'home_team': home_team,
            'away_team': away_team,
            'match_date': match['match_date'],
            'prediction': prediction,
            'confidence': confidence,
            'probabilities': probabilities,
            'odds': match['odds'],
            'model_type': self.model_type,  # Nuevo: identificar modelo usado
            'is_calibrated': self.is_calibrated
        }

        logger.info(f"Prediction: {prediction} (confidence: {confidence:.2%}) [Model: {self.model_type}]")

        return result

    def predict_multiple_matches(self, matches: list) -> list:
        """
        Predice resultados para múltiples partidos

        Args:
            matches: Lista de diccionarios de partidos

        Returns:
            Lista de predicciones
        """
        predictions = []
        errors = []

        for match in matches:
            try:
                prediction = self.predict_match(match)

                # Skip if prediction contains error
                if 'error' in prediction:
                    errors.append(f"{match.get('match_id')}: {prediction['error']}")
                    continue

                predictions.append(prediction)
            except Exception as e:
                import traceback
                error_msg = f"{match.get('match_id')}: {str(e)}\n{traceback.format_exc()}"
                logger.error(f"Error predicting match: {error_msg}")
                errors.append(str(e))
                continue

        # Log summary
        if errors:
            logger.warning(f"Prediction errors summary: {len(errors)} failures out of {len(matches)} matches")
            logger.warning(f"First error: {errors[0]}")

        logger.info(f"Successfully predicted {len(predictions)} out of {len(matches)} matches")

        return predictions


if __name__ == "__main__":
    # Test del predictor
    from src.scrapers.triunfobet_scraper import TriunfoBetScraper

    print("=== Testing Match Predictor ===\n")

    # Primero necesitamos entrenar los modelos si no existen
    import os
    if not os.path.exists("models/soccer_model.pkl"):
        print("Training models first...")
        from src.models.train_model import train_all_models
        train_all_models()

    # Crear predictor
    predictor = MatchPredictor()

    # Obtener partidos
    scraper = TriunfoBetScraper(use_mock=True)
    matches = scraper.get_available_matches("all")

    # Predecir algunos partidos
    print("\n=== Predictions ===\n")
    for match in matches[:5]:
        prediction = predictor.predict_match(match)

        print(f"\n{prediction['home_team']} vs {prediction['away_team']}")
        print(f"League: {prediction['league']}")
        print(f"Prediction: {prediction['prediction']} (Confidence: {prediction['confidence']:.1%})")
        print(f"Probabilities: {prediction['probabilities']}")
        print(f"Odds: {prediction['odds']}")
