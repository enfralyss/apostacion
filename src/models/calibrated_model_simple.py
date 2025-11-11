"""
Calibrated Betting Model - Versión simplificada e integrable
Modelo ML con probabilidades calibradas para value betting
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss, accuracy_score
from sklearn.preprocessing import LabelEncoder
try:
    from xgboost import XGBClassifier
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier as XGBClassifier
from typing import Dict, Tuple
from loguru import logger
import pickle
import json
import os


class CalibratedBettingModel:
    """
    Modelo de betting con calibración de probabilidades

    Mejoras vs modelo actual:
    1. TimeSeriesSplit (no random split) - evita data leakage
    2. Isotonic calibration - probabilidades confiables
    3. ECE y Brier Score tracking
    """

    def __init__(self, sport: str, model_type: str = 'xgboost'):
        self.sport = sport
        self.model_type = model_type
        self.base_model = None
        self.calibrated_model = None
        self.feature_columns = []
        self.label_encoder = LabelEncoder()
        self.calibration_metrics = {}

    def train(
        self,
        data: pd.DataFrame,
        n_splits: int = 3,
        calibration_method: str = 'isotonic'
    ) -> Dict:
        """
        Entrena modelo con validación temporal y calibración

        Args:
            data: DataFrame con features y 'result' target
            n_splits: Número de splits para TimeSeriesSplit
            calibration_method: 'isotonic' o 'sigmoid'

        Returns:
            Dict con métricas
        """
        logger.info(f"Training calibrated {self.model_type} for {self.sport}")

        # Separar features y target
        X = data.drop(['result', 'match_id', 'match_date'], axis=1, errors='ignore')
        X = X.select_dtypes(include=[np.number])
        y = data['result']

        self.feature_columns = X.columns.tolist()

        # Label encoding
        y_encoded = self.label_encoder.fit_transform(y)

        # TimeSeriesSplit - CRÍTICO
        tscv = TimeSeriesSplit(n_splits=n_splits)

        # Inicializar modelo
        if self.model_type == 'xgboost':
            try:
                self.base_model = XGBClassifier(
                    n_estimators=200,
                    max_depth=6,
                    learning_rate=0.1,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    eval_metric='mlogloss'
                )
            except:
                from sklearn.ensemble import GradientBoostingClassifier
                self.base_model = GradientBoostingClassifier(
                    n_estimators=200,
                    learning_rate=0.1,
                    max_depth=6,
                    random_state=42
                )
        else:
            from sklearn.ensemble import GradientBoostingClassifier
            self.base_model = GradientBoostingClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )

        # Walk-forward validation
        cv_metrics = []
        fold = 1

        logger.info("Starting walk-forward validation...")

        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y_encoded[train_idx], y_encoded[val_idx]

            # Train on fold
            self.base_model.fit(X_train, y_train)

            # Predict
            y_val_proba = self.base_model.predict_proba(X_val)
            y_val_pred = self.base_model.predict(X_val)

            # Métricas
            accuracy = accuracy_score(y_val, y_val_pred)
            logloss = log_loss(y_val, y_val_proba)

            # ECE
            ece = self._calculate_ece(y_val, y_val_proba)

            cv_metrics.append({
                'fold': fold,
                'accuracy': accuracy,
                'log_loss': logloss,
                'ece': ece,
                'n_samples': len(y_val)
            })

            logger.info(
                f"Fold {fold}: Accuracy={accuracy:.3f}, LogLoss={logloss:.3f}, ECE={ece:.3f}"
            )
            fold += 1

        # Train final model on all data
        logger.info("Training final model on all data...")
        self.base_model.fit(X, y_encoded)

        # CALIBRATION - Isotonic regression
        logger.info(f"Calibrating probabilities with {calibration_method}...")

        # Usar últimos 20% para calibración
        cal_size = int(len(X) * 0.2)
        X_cal = X.iloc[-cal_size:]
        y_cal = y_encoded[-cal_size:]

        self.calibrated_model = CalibratedClassifierCV(
            self.base_model,
            method=calibration_method,
            cv='prefit'
        )

        self.calibrated_model.fit(X_cal, y_cal)

        # Métricas post-calibración
        y_cal_proba_before = self.base_model.predict_proba(X_cal)
        y_cal_proba_after = self.calibrated_model.predict_proba(X_cal)

        ece_before = self._calculate_ece(y_cal, y_cal_proba_before)
        ece_after = self._calculate_ece(y_cal, y_cal_proba_after)

        self.calibration_metrics = {
            'ece_before_calibration': ece_before,
            'ece_after_calibration': ece_after,
            'ece_improvement': ece_before - ece_after,
            'cv_metrics': cv_metrics,
            'cv_accuracy_mean': np.mean([m['accuracy'] for m in cv_metrics]),
            'cv_logloss_mean': np.mean([m['log_loss'] for m in cv_metrics]),
            'cv_ece_mean': np.mean([m['ece'] for m in cv_metrics])
        }

        logger.info(f"✅ Calibration: ECE {ece_before:.3f} → {ece_after:.3f} (improvement: {ece_before - ece_after:.3f})")

        return self.calibration_metrics

    def _calculate_ece(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        n_bins: int = 10
    ) -> float:
        """
        Expected Calibration Error (ECE)
        ECE < 0.05 = excelente calibración
        """
        y_pred_proba = np.max(y_proba, axis=1)
        y_pred = np.argmax(y_proba, axis=1)

        bins = np.linspace(0, 1, n_bins + 1)

        ece = 0.0
        total_samples = len(y_true)

        for i in range(n_bins):
            bin_mask = (y_pred_proba > bins[i]) & (y_pred_proba <= bins[i + 1])

            if np.sum(bin_mask) > 0:
                bin_acc = np.mean(y_pred[bin_mask] == y_true[bin_mask])
                bin_conf = np.mean(y_pred_proba[bin_mask])
                bin_weight = np.sum(bin_mask) / total_samples

                ece += bin_weight * np.abs(bin_acc - bin_conf)

        return ece

    def predict_proba(self, features: pd.DataFrame) -> Dict:
        """Predice probabilidades CALIBRADAS"""
        if self.calibrated_model is None:
            raise ValueError("Model not trained yet")

        features = features[self.feature_columns]
        probas = self.calibrated_model.predict_proba(features)[0]

        result = {}
        for i, class_label in enumerate(self.label_encoder.classes_):
            result[class_label] = float(probas[i])

        return result

    def predict(self, features: pd.DataFrame) -> str:
        """Predice clase más probable"""
        if self.calibrated_model is None:
            raise ValueError("Model not trained yet")

        features = features[self.feature_columns]
        prediction_encoded = self.calibrated_model.predict(features)[0]
        prediction = self.label_encoder.inverse_transform([prediction_encoded])[0]

        return prediction

    def save(self, filepath: str):
        """Guarda modelo calibrado"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        model_data = {
            'calibrated_model': self.calibrated_model,
            'sport': self.sport,
            'model_type': self.model_type,
            'feature_columns': self.feature_columns,
            'label_encoder': self.label_encoder,
            'calibration_metrics': self.calibration_metrics
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        # Guardar métricas en JSON
        metrics_path = filepath.replace('.pkl', '_metrics.json')
        metrics_to_save = {}
        for k, v in self.calibration_metrics.items():
            if k != 'cv_metrics':
                metrics_to_save[k] = v

        with open(metrics_path, 'w') as f:
            json.dump(metrics_to_save, f, indent=2)

        logger.info(f"✅ Model saved to {filepath}")

    @classmethod
    def load(cls, filepath: str):
        """Carga modelo calibrado"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        instance = cls(model_data['sport'], model_data['model_type'])
        instance.calibrated_model = model_data['calibrated_model']
        instance.feature_columns = model_data['feature_columns']
        instance.label_encoder = model_data['label_encoder']
        instance.calibration_metrics = model_data.get('calibration_metrics', {})

        logger.info(f"✅ Model loaded from {filepath}")
        return instance


if __name__ == "__main__":
    # Test del modelo calibrado
    print("=== Testing Calibrated Model ===\n")

    # Generar datos de prueba
    from src.utils.database import BettingDatabase
    from src.data.feature_integration import build_training_dataset_with_advanced_features

    db = BettingDatabase()

    # Build dataset
    print("Building training dataset with advanced features...")
    df = build_training_dataset_with_advanced_features(db, sport='soccer', min_rows=100)

    if not df.empty:
        print(f"Dataset: {len(df)} rows, {len(df.columns)} columns\n")

        # Train model
        model = CalibratedBettingModel(sport='soccer')
        metrics = model.train(df, n_splits=3)

        print("\n=== Training Metrics ===")
        print(f"ECE before calibration: {metrics['ece_before_calibration']:.4f}")
        print(f"ECE after calibration: {metrics['ece_after_calibration']:.4f}")
        print(f"ECE improvement: {metrics['ece_improvement']:.4f}")
        print(f"\nCV Accuracy: {metrics['cv_accuracy_mean']:.3f}")
        print(f"CV Log Loss: {metrics['cv_logloss_mean']:.3f}")
        print(f"CV ECE: {metrics['cv_ece_mean']:.3f}")

        # Save model
        model.save("models/soccer_calibrated.pkl")
        print("\n✅ Model saved!")
