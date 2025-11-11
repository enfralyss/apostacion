"""
Ensemble Model - Combina XGBoost, LightGBM y Random Forest
Mejora accuracy y robustez mediante voting ensemble con calibración
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import pickle
import json
from datetime import datetime
from loguru import logger

from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from sklearn.preprocessing import LabelEncoder

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available - will use only LightGBM and RandomForest")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not available - will use only XGBoost and RandomForest")


class EnsembleBettingModel:
    """
    Ensemble de modelos calibrados para predicción de apuestas deportivas
    
    Combina:
    - XGBoost: Excelente para patrones no lineales complejos
    - LightGBM: Más rápido, bueno con features categóricas
    - Random Forest: Robusto, menos propenso a overfitting
    
    Usa soft voting (promedio de probabilidades) + calibración isotónica
    """
    
    def __init__(self, sport: str = 'soccer'):
        """
        Args:
            sport: 'soccer' o 'nba'
        """
        self.sport = sport
        self.label_encoder = LabelEncoder()
        self.ensemble_model = None
        self.base_models = {}
        self.feature_names = None
        self.metrics = {}
        
    def _create_base_models(self) -> List[Tuple[str, object]]:
        """Crea los modelos base del ensemble"""
        
        estimators = []
        
        # 1. XGBoost - Gradient Boosting optimizado
        if XGBOOST_AVAILABLE:
            xgb_model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=3,
                gamma=0.1,
                reg_alpha=0.1,  # L1 regularization
                reg_lambda=1.0,  # L2 regularization
                random_state=42,
                n_jobs=-1,
                eval_metric='mlogloss'
            )
            estimators.append(('xgboost', xgb_model))
            logger.info("✓ XGBoost agregado al ensemble")
        
        # 2. LightGBM - Gradient Boosting rápido
        if LIGHTGBM_AVAILABLE:
            lgb_model = lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_samples=20,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )
            estimators.append(('lightgbm', lgb_model))
            logger.info("✓ LightGBM agregado al ensemble")
        
        # 3. Random Forest - Robusto y menos propenso a overfitting
        rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            max_features='sqrt',
            bootstrap=True,
            oob_score=True,
            random_state=42,
            n_jobs=-1
        )
        estimators.append(('random_forest', rf_model))
        logger.info("✓ Random Forest agregado al ensemble")
        
        if len(estimators) < 2:
            raise RuntimeError("Se necesitan al menos 2 modelos para ensemble. Instala xgboost y/o lightgbm.")
        
        logger.info(f"Ensemble creado con {len(estimators)} modelos base")
        return estimators
    
    def train(self, X: pd.DataFrame, y: pd.Series, calibrate: bool = True, 
              n_splits: int = 3) -> Dict:
        """
        Entrena el ensemble con validación temporal y calibración
        
        Args:
            X: Features (DataFrame)
            y: Target (Series) - puede ser str ('home_win', 'draw', 'away_win')
            calibrate: Si True, aplica calibración isotónica
            n_splits: Número de folds para TimeSeriesSplit
            
        Returns:
            Dict con métricas de validación
        """
        logger.info(f"=== Entrenando Ensemble Model para {self.sport} ===")
        logger.info(f"Dataset: {len(X)} muestras, {X.shape[1]} features")
        
        # Guardar nombres de features
        self.feature_names = list(X.columns)
        
        # Encode labels si son strings
        if y.dtype == 'object':
            y_encoded = self.label_encoder.fit_transform(y)
            logger.info(f"Labels encoded: {list(self.label_encoder.classes_)}")
        else:
            y_encoded = y.values
        
        # Crear modelos base
        base_estimators = self._create_base_models()
        
        # Crear ensemble con soft voting (promedio de probabilidades)
        self.ensemble_model = VotingClassifier(
            estimators=base_estimators,
            voting='soft',  # Usa probabilidades, no votos duros
            n_jobs=-1
        )
        
        # Validación temporal (TimeSeriesSplit)
        logger.info(f"Validación con TimeSeriesSplit (n_splits={n_splits})")
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        cv_scores = {
            'accuracy': [],
            'log_loss': [],
            'brier_score': []
        }
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            X_train_fold, X_val_fold = X.iloc[train_idx], X.iloc[val_idx]
            y_train_fold, y_val_fold = y_encoded[train_idx], y_encoded[val_idx]
            
            # Entrenar fold
            self.ensemble_model.fit(X_train_fold, y_train_fold)
            
            # Predecir
            y_pred = self.ensemble_model.predict(X_val_fold)
            y_proba = self.ensemble_model.predict_proba(X_val_fold)
            
            # Métricas
            acc = accuracy_score(y_val_fold, y_pred)
            ll = log_loss(y_val_fold, y_proba)
            
            # Brier score para multiclass: promedio de brier por clase
            if y_proba.shape[1] == 2:
                # Binario
                bs = brier_score_loss(y_val_fold, y_proba[:, 1])
            else:
                # Multiclass: calcular brier score por cada clase y promediar
                from sklearn.preprocessing import label_binarize
                y_bin = label_binarize(y_val_fold, classes=range(y_proba.shape[1]))
                bs = np.mean([brier_score_loss(y_bin[:, i], y_proba[:, i]) 
                             for i in range(y_proba.shape[1])])
            
            cv_scores['accuracy'].append(acc)
            cv_scores['log_loss'].append(ll)
            cv_scores['brier_score'].append(bs)
            
            logger.info(f"Fold {fold}/{n_splits} - Acc: {acc:.3f}, LogLoss: {ll:.3f}, Brier: {bs:.3f}")
        
        # Métricas promedio
        metrics_avg = {
            'cv_accuracy': np.mean(cv_scores['accuracy']),
            'cv_accuracy_std': np.std(cv_scores['accuracy']),
            'cv_log_loss': np.mean(cv_scores['log_loss']),
            'cv_brier_score': np.mean(cv_scores['brier_score']),
            'n_folds': n_splits,
            'n_samples': len(X),
            'n_features': X.shape[1]
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"RESULTADOS CV (sin calibrar):")
        logger.info(f"  Accuracy:     {metrics_avg['cv_accuracy']:.1%} ± {metrics_avg['cv_accuracy_std']:.1%}")
        logger.info(f"  Log Loss:     {metrics_avg['cv_log_loss']:.3f}")
        logger.info(f"  Brier Score:  {metrics_avg['cv_brier_score']:.3f}")
        logger.info(f"{'='*60}\n")
        
        # Entrenar modelo final en todo el dataset
        logger.info("Entrenando modelo final en dataset completo...")
        self.ensemble_model.fit(X, y_encoded)
        
        # Calibración (opcional pero RECOMENDADO para betting)
        if calibrate:
            logger.info("Aplicando calibración isotónica con más folds...")

            # Calibrar el ensemble completo con más folds para mejor calibración
            self.ensemble_model = CalibratedClassifierCV(
                self.ensemble_model,
                method='isotonic',
                cv=5,  # Usar 5-fold CV para mejor calibración (antes era 3)
                n_jobs=-1
            )
            self.ensemble_model.fit(X, y_encoded)
            
            # Evaluar calibración
            y_proba_calib = self.ensemble_model.predict_proba(X)
            
            # Expected Calibration Error (ECE)
            ece = self._calculate_ece(y_encoded, y_proba_calib)
            
            metrics_avg['ece_after_calibration'] = ece
            metrics_avg['calibrated'] = True
            
            logger.info(f"✓ Calibración completada - ECE: {ece:.4f}")
        else:
            metrics_avg['calibrated'] = False
        
        # Guardar métricas
        self.metrics = metrics_avg
        self.metrics['sport'] = self.sport
        self.metrics['trained_at'] = datetime.now().isoformat()
        self.metrics['model_type'] = 'ensemble'
        self.metrics['base_models'] = [name for name, _ in base_estimators]
        
        logger.info(f"✅ Ensemble model entrenado exitosamente")
        
        return metrics_avg
    
    def _calculate_ece(self, y_true: np.ndarray, y_proba: np.ndarray, 
                      n_bins: int = 10) -> float:
        """Calcula Expected Calibration Error"""
        try:
            # Para multiclass, usar probabilidad de la clase predicha
            y_pred_proba = y_proba.max(axis=1)
            y_pred_class = y_proba.argmax(axis=1)
            
            # Crear bins de confianza
            bins = np.linspace(0, 1, n_bins + 1)
            bin_indices = np.digitize(y_pred_proba, bins) - 1
            
            ece = 0.0
            for i in range(n_bins):
                mask = bin_indices == i
                if mask.sum() > 0:
                    bin_accuracy = (y_true[mask] == y_pred_class[mask]).mean()
                    bin_confidence = y_pred_proba[mask].mean()
                    bin_weight = mask.sum() / len(y_true)
                    ece += bin_weight * abs(bin_accuracy - bin_confidence)
            
            return ece
        except Exception as e:
            logger.warning(f"Error calculando ECE: {e}")
            return 0.0
    
    def predict_proba(self, X: pd.DataFrame) -> Dict[str, float]:
        """
        Predice probabilidades calibradas para un match
        
        Args:
            X: Features del match (DataFrame con 1 fila o múltiples)
            
        Returns:
            Dict con probabilidades por outcome o lista de dicts si múltiples matches
        """
        if self.ensemble_model is None:
            raise ValueError("Modelo no entrenado. Llama a train() primero.")
        
        # Asegurar que tenga las features correctas
        if self.feature_names:
            missing = set(self.feature_names) - set(X.columns)
            if missing:
                raise ValueError(f"Features faltantes: {missing}")
            X = X[self.feature_names]
        
        # Predecir probabilidades
        probabilities = self.ensemble_model.predict_proba(X)
        
        # Convertir a dict(s)
        if len(X) == 1:
            # Un solo match
            if self.sport == 'soccer':
                return {
                    'home_win': float(probabilities[0][0]),
                    'draw': float(probabilities[0][1]),
                    'away_win': float(probabilities[0][2])
                }
            else:  # NBA (sin empate)
                return {
                    'home_win': float(probabilities[0][0]),
                    'away_win': float(probabilities[0][1])
                }
        else:
            # Múltiples matches
            results = []
            for probs in probabilities:
                if self.sport == 'soccer':
                    results.append({
                        'home_win': float(probs[0]),
                        'draw': float(probs[1]),
                        'away_win': float(probs[2])
                    })
                else:
                    results.append({
                        'home_win': float(probs[0]),
                        'away_win': float(probs[1])
                    })
            return results
    
    def predict(self, X: pd.DataFrame) -> str:
        """Predice el outcome más probable"""
        if self.ensemble_model is None:
            raise ValueError("Modelo no entrenado.")
        
        if self.feature_names:
            X = X[self.feature_names]
        
        prediction = self.ensemble_model.predict(X)
        
        # Decode label
        if hasattr(self.label_encoder, 'classes_'):
            return self.label_encoder.inverse_transform(prediction)[0]
        else:
            return prediction[0]
    
    def get_feature_importance(self, method: str = 'mean') -> pd.DataFrame:
        """
        Obtiene feature importance promediando los modelos base
        
        Args:
            method: 'mean' o 'max'
            
        Returns:
            DataFrame con features y su importancia
        """
        importances = {}
        
        # Extraer importances de cada modelo base
        for name, estimator in self.ensemble_model.named_estimators_.items():
            # Para modelos calibrados, acceder al estimador base
            if hasattr(estimator, 'base_estimator'):
                estimator = estimator.base_estimator
            
            if hasattr(estimator, 'feature_importances_'):
                importances[name] = estimator.feature_importances_
        
        if not importances:
            logger.warning("Ningún modelo tiene feature_importances_")
            return pd.DataFrame()
        
        # Combinar importances
        df_importance = pd.DataFrame(importances, index=self.feature_names)
        
        if method == 'mean':
            df_importance['importance'] = df_importance.mean(axis=1)
        else:  # max
            df_importance['importance'] = df_importance.max(axis=1)
        
        return df_importance.sort_values('importance', ascending=False)
    
    def save(self, filepath: str):
        """Guarda el modelo entrenado"""
        model_data = {
            'ensemble_model': self.ensemble_model,
            'label_encoder': self.label_encoder,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'sport': self.sport
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        # Guardar métricas también en JSON
        metrics_path = filepath.replace('.pkl', '_metrics.json')
        with open(metrics_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        logger.info(f"✓ Modelo guardado: {filepath}")
        logger.info(f"✓ Métricas guardadas: {metrics_path}")
    
    @classmethod
    def load(cls, filepath: str) -> 'EnsembleBettingModel':
        """Carga un modelo guardado"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        instance = cls(sport=model_data.get('sport', 'soccer'))
        instance.ensemble_model = model_data['ensemble_model']
        instance.label_encoder = model_data['label_encoder']
        instance.feature_names = model_data['feature_names']
        instance.metrics = model_data['metrics']
        
        logger.info(f"✓ Modelo cargado: {filepath}")
        logger.info(f"  Tipo: Ensemble ({', '.join(instance.metrics.get('base_models', []))})")
        logger.info(f"  Accuracy CV: {instance.metrics.get('cv_accuracy', 0):.1%}")
        
        return instance


if __name__ == "__main__":
    """Test del ensemble model"""
    
    print("=== Testing Ensemble Model ===\n")
    
    # 1. Crear datos de ejemplo
    from src.utils.database import BettingDatabase
    
    db = BettingDatabase()
    db.connect()
    
    # Cargar training data
    try:
        df = pd.read_csv('data/training_advanced_soccer.csv')
        print(f"✓ Dataset cargado: {len(df)} matches\n")
    except FileNotFoundError:
        print("❌ Ejecuta primero: python train_advanced_model.py")
        exit(1)
    
    # Preparar features y target
    feature_cols = [col for col in df.columns if col not in ['result', 'match_id', 'match_date', 'sport', 'league', 'home_team', 'away_team']]
    X = df[feature_cols]
    y = df['result']
    
    print(f"Features: {X.shape[1]}")
    print(f"Target classes: {y.value_counts().to_dict()}\n")
    
    # 2. Entrenar ensemble
    model = EnsembleBettingModel(sport='soccer')
    metrics = model.train(X, y, calibrate=True, n_splits=3)
    
    # 3. Guardar modelo
    model.save('models/soccer_ensemble.pkl')
    
    # 4. Test de predicción
    print("\n=== Test de Predicción ===")
    sample = X.iloc[:1]
    probs = model.predict_proba(sample)
    pred = model.predict(sample)
    
    print(f"Predicción: {pred}")
    print(f"Probabilidades: {probs}")
    
    # 5. Feature importance
    print("\n=== Top 10 Features ===")
    importance = model.get_feature_importance()
    print(importance.head(10))
    
    print("\n✅ Test completado")
