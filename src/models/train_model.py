"""
Entrenamiento de modelos de Machine Learning para predicción de resultados
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
try:
    from xgboost import XGBClassifier  # type: ignore
except Exception:
    XGBClassifier = None  # Fallback si no está disponible XGBoost
from sklearn.metrics import accuracy_score, classification_report, log_loss
try:
    from sklearn.metrics import roc_auc_score, confusion_matrix  # type: ignore
except Exception:
    roc_auc_score = None
    confusion_matrix = None
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

        # Separar features y target (usar solo columnas numéricas para evitar objetos)
        X = data.drop('result', axis=1)
        X = X.select_dtypes(include=[np.number])
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
        if self.model_type == "xgboost" and XGBClassifier is not None:
            self.model = XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='mlogloss'
            )
        elif self.model_type == "xgboost" and XGBClassifier is None:
            logger.warning("XGBoost no disponible en el entorno. Usando GradientBoostingClassifier como fallback.")
            self.model = GradientBoostingClassifier(
                n_estimators=200,
                learning_rate=0.1,
                random_state=42
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

        # AUC multi-clase (OVR) si está disponible
        auc_ovr = None
        if roc_auc_score is not None:
            try:
                auc_ovr = float(roc_auc_score(y_test, test_proba, multi_class='ovr'))
                logger.info(f"AUC (OVR): {auc_ovr:.4f}")
            except Exception as e:
                logger.warning(f"No se pudo calcular AUC OVR: {e}")

        # Matriz de confusión si disponible
        cm = None
        if confusion_matrix is not None:
            try:
                cm = confusion_matrix(y_test, test_preds)
            except Exception as e:
                logger.warning(f"No se pudo calcular matriz de confusión: {e}")

        return {
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'log_loss': logloss,
            'auc_ovr': auc_ovr,
            'confusion_matrix': cm.tolist() if cm is not None else None
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
    """Entrena modelos sólo para deportes habilitados en config (actual: soccer)."""
    from src.utils.data_generator import generate_training_data
    from src.utils.database import BettingDatabase
    import json
    import hashlib
    db = BettingDatabase()

    # Crear directorio de datos si no existe
    os.makedirs("data", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    # Soccer Model
    logger.info("=" * 50)
    logger.info("TRAINING SOCCER MODEL")
    logger.info("=" * 50)

    # Preferir dataset real si existe con suficiente tamaño
    real_soccer_csv = "data/training_real_soccer.csv"
    if os.path.exists(real_soccer_csv):
        try:
            soccer_data = pd.read_csv(real_soccer_csv)
            logger.info(f"Loaded real soccer dataset: {len(soccer_data)} rows")
        except Exception as e:
            logger.warning(f"No se pudo cargar dataset real de soccer, usando sintético. Error: {e}")
            soccer_data = generate_training_data("soccer", num_matches=2000)
    else:
        soccer_data = generate_training_data("soccer", num_matches=2000)
    soccer_model = BettingModel(sport="soccer", model_type="xgboost")
    soccer_metrics = soccer_model.train(soccer_data, validation_split=0.2)
    soccer_model.save("models/soccer_model.pkl")
    # Hash y tamaño de dataset
    soccer_csv = soccer_data.to_csv(index=False).encode('utf-8')
    soccer_hash = hashlib.md5(soccer_csv).hexdigest()
    soccer_rows, soccer_cols = soccer_data.shape
    with open("models/soccer_model_metrics.json", 'w') as f:
        json.dump({**soccer_metrics, 'dataset_hash': soccer_hash, 'dataset_rows': soccer_rows, 'dataset_cols': soccer_cols}, f, indent=2)
    # Guardar resumen en DB (tabla model_registry pendiente de creación si no existe)
    try:
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport TEXT,
                model_type TEXT,
                test_accuracy REAL,
                train_accuracy REAL,
                cv_mean REAL,
                cv_std REAL,
                log_loss REAL,
                auc_ovr REAL,
                dataset_hash TEXT,
                dataset_rows INTEGER,
                dataset_cols INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Intentar agregar columnas nuevas si la tabla ya existía
        for stmt in [
            "ALTER TABLE model_registry ADD COLUMN auc_ovr REAL",
            "ALTER TABLE model_registry ADD COLUMN dataset_hash TEXT",
            "ALTER TABLE model_registry ADD COLUMN dataset_rows INTEGER",
            "ALTER TABLE model_registry ADD COLUMN dataset_cols INTEGER",
        ]:
            try:
                cursor.execute(stmt)
            except Exception:
                pass
        cursor.execute("""
            INSERT INTO model_registry (sport, model_type, test_accuracy, train_accuracy, cv_mean, cv_std, log_loss, auc_ovr, dataset_hash, dataset_rows, dataset_cols)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'soccer', 'xgboost', soccer_metrics['test_accuracy'], soccer_metrics['train_accuracy'],
            soccer_metrics['cv_accuracy_mean'], soccer_metrics['cv_accuracy_std'], soccer_metrics['log_loss'],
            soccer_metrics.get('auc_ovr'), soccer_hash, soccer_rows, soccer_cols
        ))
        db.conn.commit()
    except Exception as e:
        logger.error(f"Error saving soccer model metrics to DB: {e}")

    # Summary (solo soccer)
    logger.info("\n" + "=" * 50)
    logger.info("TRAINING SUMMARY (SOCCER ONLY)")
    logger.info("=" * 50)
    logger.info(f"Soccer Model - Test Accuracy: {soccer_metrics['test_accuracy']:.4f}")
    db.close()


if __name__ == "__main__":
    train_all_models()
