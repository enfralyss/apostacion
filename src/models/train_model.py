"""
Entrenamiento de modelos de Machine Learning para predicción de resultados
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, log_loss
import pickle
import os
from loguru import logger


class BettingModel:
    """Modelo de predicción para apuestas deportivas"""

    def __init__(self, sport: str, model_type: str = "xgboost"):
        """
        Args:
            sport: 'soccer' o 'nba'
            model_type: 'xgboost', 'random_forest', 'gradient_boosting'
        """
        self.sport = sport
        self.model_type = model_type
        self.model = None
        self.feature_columns = []
        self.classes_ = []
        self.label_encoder = LabelEncoder()

    def train(self, data: pd.DataFrame, validation_split: float = 0.2):
        """
        Entrena el modelo con datos históricos

        Args:
            data: DataFrame con features y resultados
            validation_split: Proporción de datos para validación
        """
        logger.info(f"Training {self.model_type} model for {self.sport}")

        # Separar features y target
        X = data.drop('result', axis=1)
        y = data['result']

        self.feature_columns = X.columns.tolist()
        self.classes_ = sorted(y.unique())

        # Convertir labels a numéricos
        y_encoded = self.label_encoder.fit_transform(y)

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=validation_split, random_state=42, stratify=y_encoded
        )

        # Inicializar modelo
        if self.model_type == "xgboost":
            self.model = XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='mlogloss',
                enable_categorical=True  # Permitir strings como labels
            )
        elif self.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                random_state=42
            )
        else:  # gradient_boosting
            self.model = GradientBoostingClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )

        # Entrenar
        logger.info(f"Training on {len(X_train)} samples...")
        self.model.fit(X_train, y_train)

        # Evaluar
        train_preds = self.model.predict(X_train)
        test_preds = self.model.predict(X_test)

        train_acc = accuracy_score(y_train, train_preds)
        test_acc = accuracy_score(y_test, test_preds)

        logger.info(f"Training accuracy: {train_acc:.4f}")
        logger.info(f"Test accuracy: {test_acc:.4f}")

        # Classification report (convertir a labels originales)
        logger.info("\nClassification Report (Test Set):")
        print(classification_report(y_test, test_preds, target_names=self.label_encoder.classes_))

        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y_encoded, cv=5, scoring='accuracy')
        logger.info(f"Cross-validation accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)

            logger.info("\nTop 10 Most Important Features:")
            print(feature_importance.head(10))

        # Log loss (para calibración de probabilidades)
        test_proba = self.model.predict_proba(X_test)
        logloss = log_loss(y_test, test_proba)
        logger.info(f"Log Loss: {logloss:.4f}")

        return {
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'log_loss': logloss
        }

    def predict_proba(self, features: pd.DataFrame) -> dict:
        """
        Predice probabilidades para cada resultado

        Args:
            features: DataFrame con las mismas features del entrenamiento

        Returns:
            Dict con probabilidades para cada clase
        """
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")

        # Asegurar que las features estén en el orden correcto
        features = features[self.feature_columns]

        probas = self.model.predict_proba(features)[0]

        result = {}
        # Decodificar labels numéricos a strings originales
        for i, class_label in enumerate(self.label_encoder.classes_):
            result[class_label] = float(probas[i])

        return result

    def predict(self, features: pd.DataFrame) -> str:
        """Predice el resultado más probable"""
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")

        features = features[self.feature_columns]
        prediction_encoded = self.model.predict(features)[0]
        # Decodificar label numérico a string original
        prediction = self.label_encoder.inverse_transform([prediction_encoded])[0]
        return prediction

    def save(self, filepath: str):
        """Guarda el modelo entrenado"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        model_data = {
            'model': self.model,
            'sport': self.sport,
            'model_type': self.model_type,
            'feature_columns': self.feature_columns,
            'classes': self.classes_,
            'label_encoder': self.label_encoder
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {filepath}")

    @classmethod
    def load(cls, filepath: str):
        """Carga un modelo guardado"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        instance = cls(model_data['sport'], model_data['model_type'])
        instance.model = model_data['model']
        instance.feature_columns = model_data['feature_columns']
        instance.classes_ = model_data['classes']
        instance.label_encoder = model_data.get('label_encoder', LabelEncoder())

        logger.info(f"Model loaded from {filepath}")
        return instance


def train_all_models():
    """Entrena modelos para soccer y NBA"""
    from src.utils.data_generator import generate_training_data

    # Crear directorio de datos si no existe
    os.makedirs("data", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    # Soccer Model
    logger.info("=" * 50)
    logger.info("TRAINING SOCCER MODEL")
    logger.info("=" * 50)

    soccer_data = generate_training_data("soccer", num_matches=2000)
    soccer_model = BettingModel(sport="soccer", model_type="xgboost")
    soccer_metrics = soccer_model.train(soccer_data, validation_split=0.2)
    soccer_model.save("models/soccer_model.pkl")

    # NBA Model
    logger.info("\n" + "=" * 50)
    logger.info("TRAINING NBA MODEL")
    logger.info("=" * 50)

    nba_data = generate_training_data("nba", num_matches=2000)
    nba_model = BettingModel(sport="nba", model_type="xgboost")
    nba_metrics = nba_model.train(nba_data, validation_split=0.2)
    nba_model.save("models/nba_model.pkl")

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Soccer Model - Test Accuracy: {soccer_metrics['test_accuracy']:.4f}")
    logger.info(f"NBA Model - Test Accuracy: {nba_metrics['test_accuracy']:.4f}")


if __name__ == "__main__":
    train_all_models()
