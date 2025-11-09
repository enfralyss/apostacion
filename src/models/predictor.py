"""
Predictor - Usa modelos entrenados para predecir resultados de partidos
"""

import pandas as pd
from typing import Dict
from loguru import logger
from src.models.train_model import BettingModel
from src.scrapers.stats_collector import StatsCollector


class MatchPredictor:
    """Predictor de resultados de partidos"""

    def __init__(self, soccer_model_path: str = "models/soccer_model.pkl",
                 nba_model_path: str = "models/nba_model.pkl"):
        """
        Args:
            soccer_model_path: Ruta al modelo de fútbol
            nba_model_path: Ruta al modelo de NBA
        """
        try:
            self.soccer_model = BettingModel.load(soccer_model_path)
            logger.info("Soccer model loaded successfully")
        except FileNotFoundError:
            logger.warning(f"Soccer model not found at {soccer_model_path}")
            self.soccer_model = None

        try:
            self.nba_model = BettingModel.load(nba_model_path)
            logger.info("NBA model loaded successfully")
        except FileNotFoundError:
            logger.warning(f"NBA model not found at {nba_model_path}")
            self.nba_model = None

        self.stats_collector = StatsCollector(use_mock=True)

    def predict_match(self, match: Dict) -> Dict:
        """
        Predice el resultado de un partido

        Args:
            match: Diccionario con información del partido (de triunfobet_scraper)

        Returns:
            Diccionario con predicciones y probabilidades
        """
        sport = match['sport']
        home_team = match['home_team']
        away_team = match['away_team']

        logger.info(f"Predicting: {home_team} vs {away_team} ({sport})")

        # Obtener estadísticas de equipos
        home_stats = self.stats_collector.get_team_stats(home_team, sport)
        away_stats = self.stats_collector.get_team_stats(away_team, sport)

        # Obtener H2H
        h2h = self.stats_collector.get_head_to_head(home_team, away_team, sport)

        # Calcular features para ambos equipos
        home_features = self.stats_collector.calculate_team_features(home_stats, is_home=True)
        away_features = self.stats_collector.calculate_team_features(away_stats, is_home=False)

        # Crear DataFrame de features
        features_dict = {}

        # Agregar features del equipo local con prefijo 'home_'
        for key, value in home_features.items():
            features_dict[f'home_{key}'] = value

        # Agregar features del equipo visitante con prefijo 'away_'
        for key, value in away_features.items():
            features_dict[f'away_{key}'] = value

        # Agregar H2H
        features_dict['h2h_home_win_rate'] = h2h['team1_win_rate']

        # Calcular diferencial de estadísticas
        if sport == "soccer":
            stat_diff = (home_features['goals_scored_avg'] - home_features['goals_conceded_avg']) - \
                       (away_features['goals_scored_avg'] - away_features['goals_conceded_avg'])
        else:  # NBA
            stat_diff = (home_features['points_scored_avg'] - home_features['points_conceded_avg']) - \
                       (away_features['points_scored_avg'] - away_features['points_conceded_avg'])

        features_dict['stat_differential'] = stat_diff

        # Convertir a DataFrame
        features_df = pd.DataFrame([features_dict])

        # Seleccionar modelo
        model = self.soccer_model if sport == "soccer" else self.nba_model

        if model is None:
            logger.error(f"Model for {sport} not loaded")
            return {
                'error': f'Model for {sport} not available',
                'probabilities': {}
            }

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
            'odds': match['odds']
        }

        logger.info(f"Prediction: {prediction} (confidence: {confidence:.2%})")

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

        for match in matches:
            try:
                prediction = self.predict_match(match)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Error predicting match {match.get('match_id')}: {e}")
                continue

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
