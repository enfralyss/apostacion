"""
Predictor - Usa modelos entrenados para predecir resultados de partidos
Actualizado para usar EnsembleModel o CalibratedBettingModel con features avanzadas
"""

import pandas as pd
from typing import Dict, Optional, List
from loguru import logger
from src.models.ensemble_model import EnsembleBettingModel
from src.models.calibrated_model_simple import CalibratedBettingModel
from src.models.train_model import BettingModel  # Fallback para NBA
from src.data.feature_integration import calculate_match_features_advanced
from src.utils.database import BettingDatabase
import os
import json


class MatchPredictor:
    """Predictor de resultados de partidos"""

    def __init__(self,
                 soccer_model_path: Optional[str] = None,
                 nba_model_path: str = "models/nba_model.pkl",
                 use_ensemble: bool = True,
                 auto_select_best: bool = True):
        """Inicializa el predictor y selecciona el mejor modelo disponible.

        Estrategia de selección (si auto_select_best=True):
          1. Carga candidatos (ensemble, calibrated, legacy) si existen.
          2. Lee métricas JSON si están disponibles.
          3. Calcula un score compuesto: higher accuracy, lower logloss, lower ECE.
          4. Penaliza modelos sin métricas reales (evita elegir legacy por métricas 0 artificiales).
          5. Prefiere modelos calibrados si ECE <= 0.10 y diferencia de logloss <= 0.10.

        Args:
            soccer_model_path: Ruta manual (si se quiere forzar un modelo concreto).
            nba_model_path: Ruta modelo NBA.
            use_ensemble: Incluir ensemble como candidato.
            auto_select_best: Si True, decide dinámicamente el mejor modelo.
        """
        self.soccer_model = None
        self.model_type = None
        self.is_calibrated = False

        # --- Helpers internos ---
        def _load_metrics(path: str) -> Dict:
            metrics_path = path.replace('.pkl', '_metrics.json')
            if os.path.exists(metrics_path):
                try:
                    with open(metrics_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Normalizar claves esperadas (ensemble usa cv_*, otros usan nombres directos)
                    accuracy = data.get('cv_accuracy') or data.get('cv_accuracy_mean') or data.get('accuracy')
                    log_loss = data.get('cv_log_loss') or data.get('cv_logloss_mean') or data.get('log_loss')
                    brier = data.get('cv_brier_score') or data.get('brier_score')
                    ece = data.get('ece_after_calibration') or data.get('ece')

                    # Verificar que al menos accuracy esté disponible
                    has_metrics = accuracy is not None

                    return {
                        'accuracy': accuracy,
                        'log_loss': log_loss,
                        'brier_score': brier,
                        'ece': ece,
                        'path': path,
                        'has_metrics': has_metrics
                    }
                except Exception as e:
                    logger.warning(f"No se pudieron leer métricas de {metrics_path}: {e}")
            # Sin métricas
            return {
                'accuracy': None,
                'log_loss': None,
                'brier_score': None,
                'ece': None,
                'path': path,
                'has_metrics': False
            }

        def _score(m: Dict) -> float:
            # Score heurístico. Penaliza ausencia de métricas y mala calibración.
            if not m['has_metrics']:
                return -999.0  # Evitar escoger modelos sin métricas (legacy)
            acc = m['accuracy'] or 0.0
            ll = m['log_loss'] or 5.0
            ece = m['ece'] or 1.0
            # Fórmula: maximize acc, minimize logloss & ece
            return acc - 0.3 * ll - 0.2 * ece

        candidates: List[Dict] = []

        if soccer_model_path:
            # Forzar modelo si se pasa ruta explícita
            forced_metrics = _load_metrics(soccer_model_path)
            try:
                if 'ensemble' in soccer_model_path:
                    model = EnsembleBettingModel.load(soccer_model_path)
                    model_type = 'ensemble'
                    calibrated_flag = True
                elif 'calibrated' in soccer_model_path:
                    model = CalibratedBettingModel.load(soccer_model_path)
                    model_type = 'calibrated_advanced'
                    calibrated_flag = True
                else:
                    model = BettingModel.load(soccer_model_path)
                    model_type = 'legacy'
                    calibrated_flag = False
                self.soccer_model = model
                self.model_type = model_type
                self.is_calibrated = calibrated_flag
                logger.info(f"✅ Soccer model (forced) loaded: {soccer_model_path} [{model_type}]")
            except Exception as e:
                logger.error(f"❌ Failed to load forced soccer model {soccer_model_path}: {e}")
        else:
            # Construir lista de candidatos
            if use_ensemble and os.path.exists("models/soccer_ensemble.pkl"):
                candidates.append({'loader': EnsembleBettingModel.load,
                                   'path': 'models/soccer_ensemble.pkl',
                                   'type': 'ensemble',
                                   'calibrated': True,
                                   'metrics': _load_metrics('models/soccer_ensemble.pkl')})
            if os.path.exists("models/soccer_calibrated_advanced.pkl"):
                candidates.append({'loader': CalibratedBettingModel.load,
                                   'path': 'models/soccer_calibrated_advanced.pkl',
                                   'type': 'calibrated_advanced',
                                   'calibrated': True,
                                   'metrics': _load_metrics('models/soccer_calibrated_advanced.pkl')})
            if os.path.exists("models/soccer_model.pkl"):
                candidates.append({'loader': BettingModel.load,
                                   'path': 'models/soccer_model.pkl',
                                   'type': 'legacy',
                                   'calibrated': False,
                                   'metrics': _load_metrics('models/soccer_model.pkl')})

            if not candidates:
                logger.error("❌ No hay modelos de soccer disponibles.")
            else:
                # Calcular scores
                for c in candidates:
                    c['score'] = _score(c['metrics'])
                # Ordenar por score descendente
                candidates.sort(key=lambda x: x['score'], reverse=True)

                best = candidates[0]
                # Regla adicional: si ensemble tiene calibración mala y calibrado avanzado tiene ECE mucho menor
                if len(candidates) > 1:
                    ensemble_candidate = next((c for c in candidates if c['type'] == 'ensemble'), None)
                    adv_candidate = next((c for c in candidates if 'calibrated' in c['type']), None)
                    if ensemble_candidate and adv_candidate and ensemble_candidate['metrics']['has_metrics'] and adv_candidate['metrics']['has_metrics']:
                        e_ece = ensemble_candidate['metrics']['ece'] or 1.0
                        a_ece = adv_candidate['metrics']['ece'] or 1.0
                        # Si el avanzado está claramente mejor calibrado, y su logloss no es mucho peor, preferirlo
                        if a_ece + 0.05 < e_ece and (adv_candidate['metrics']['log_loss'] or 9) <= (ensemble_candidate['metrics']['log_loss'] or 9) + 0.10:
                            best = adv_candidate
                            logger.info("🔄 Override: usando modelo calibrado avanzado por mejor ECE.")

                try:
                    self.soccer_model = best['loader'](best['path'])
                    self.model_type = best['type']
                    self.is_calibrated = best['calibrated']
                    m = best['metrics']
                    if m['has_metrics']:
                        logger.info(f"✅ Modelo seleccionado [{self.model_type}] - Acc={m['accuracy']}, LogLoss={m['log_loss']}, ECE={m['ece']}")
                    else:
                        logger.info(f"✅ Modelo seleccionado [{self.model_type}] sin métricas JSON (legacy)")
                except Exception as e:
                    logger.error(f"❌ Error cargando modelo seleccionado {best['path']}: {e}")

        # NBA model (legacy por ahora)
        try:
            self.nba_model = BettingModel.load(nba_model_path)
            logger.info("NBA model loaded successfully")
        except FileNotFoundError:
            logger.warning(f"NBA model not found at {nba_model_path}")
            self.nba_model = None

        # DB para features
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
            # Intentar advanced features (ELO, form, H2H, etc.)
            try:
                features_dict = calculate_match_features_advanced(match, self.db)
            except Exception as e:
                logger.warning(f"Advanced feature engine failed: {e} - falling back to basic features")
                features_dict = None
            # Si fallan o vienen vacías, usar básicas
            if not features_dict or len(features_dict) < 5:
                basic = self.db.calculate_match_features(match)
                if basic:
                    features_dict = basic
                    logger.info("Fallback to basic feature set applied")
                else:
                    logger.error("No features (advanced or basic) available for match")
                    return {
                        'error': 'No features available',
                        'probabilities': {}
                    }
        else:
            # Modelo legacy o NBA: usar básicas directamente
            features_dict = self.db.calculate_match_features(match)

        if features_dict is None:
            logger.warning(f"Could not calculate features for {home_team} vs {away_team}")
            return {
                'error': 'Could not calculate features',
                'probabilities': {}
            }

        # Convertir a DataFrame y alinear columnas esperadas del modelo
        features_df = pd.DataFrame([features_dict])
        expected_cols = []
        # Ensemble usa feature_names, calibrated usa feature_columns
        if hasattr(model, 'feature_names') and isinstance(getattr(model, 'feature_names'), list):
            expected_cols = model.feature_names
        elif hasattr(model, 'feature_columns') and isinstance(getattr(model, 'feature_columns'), list):
            expected_cols = model.feature_columns
        # Rellenar columnas faltantes con 0.0 para evitar errores de predicción
        for col in expected_cols:
            if col not in features_df.columns:
                features_df[col] = 0.0
        if expected_cols:
            features_df = features_df[expected_cols]

        # Predecir
        try:
            probabilities = model.predict_proba(features_df)
            prediction = model.predict(features_df)
        except Exception as e:
            logger.error(f"Model prediction failure: {e}")
            return {
                'error': f'Model prediction failure: {e}',
                'probabilities': {}
            }

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
    # Test sencillo del predictor (opcional)
    print("=== Testing Match Predictor ===\n")

    try:
        # Entrenar modelos base si no existen
        if not os.path.exists("models/soccer_model.pkl") and not os.path.exists("models/soccer_calibrated_advanced.pkl") and not os.path.exists("models/soccer_ensemble.pkl"):
            print("Training baseline model first...")
            from src.models.train_model import train_all_models
            train_all_models()

        predictor = MatchPredictor()
        # Intento mínimo: construir un match falso con odds mock y equipos de ejemplo
        mock_match = {
            'match_id': 'TEST-001',
            'sport': 'soccer',
            'league': 'TEST',
            'home_team': 'Home FC',
            'away_team': 'Away FC',
            'match_date': '2099-01-01',
            'odds': {'home_win': 2.0, 'draw': 3.4, 'away_win': 3.6}
        }
        # Nota: El cálculo de features avanzadas requiere DB con datos reales; este test puede fallar si no hay datos.
        result = predictor.predict_match(mock_match)
        print("Resultado de prueba:", result)
    except Exception as e:
        print(f"Self-test skipped due to error: {e}")
