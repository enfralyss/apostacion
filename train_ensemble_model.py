"""
Script de entrenamiento del Ensemble Model
Combina XGBoost + LightGBM + Random Forest con calibración
"""

import pandas as pd
import sys
from pathlib import Path
from loguru import logger

# Configurar logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/train_ensemble_{time}.log", rotation="10 MB")

from src.models.ensemble_model import EnsembleBettingModel


def main():
    """Pipeline completo de entrenamiento del ensemble"""
    
    print("="*70)
    print("ENTRENAMIENTO DE ENSEMBLE MODEL - XGBoost + LightGBM + Random Forest")
    print("="*70)
    print()
    
    # 1. Cargar datos de entrenamiento
    print("📂 Cargando datos de entrenamiento...")
    
    training_file = 'data/training_advanced_soccer.csv'
    if not Path(training_file).exists():
        print(f"❌ Archivo no encontrado: {training_file}")
        print("\n🔧 Soluciones:")
        print("   1. Ejecuta: python train_advanced_model.py")
        print("   2. O ejecuta: python bootstrap_historical_data.py")
        return
    
    df = pd.read_csv(training_file)
    print(f"✓ Dataset cargado: {len(df)} matches")
    print(f"  Período: {df['match_date'].min()} a {df['match_date'].max()}")
    print()
    
    # 2. Preparar features y target
    print("🔧 Preparando features...")
    
    # Columnas a excluir del entrenamiento
    exclude_cols = [
        'result', 'match_id', 'match_date', 'sport', 'league', 
        'home_team', 'away_team'
    ]
    
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    X = df[feature_cols]
    y = df['result']
    
    print(f"✓ Features: {len(feature_cols)}")
    print(f"  Target distribution:")
    for outcome, count in y.value_counts().items():
        print(f"    {outcome}: {count} ({count/len(y)*100:.1f}%)")
    print()
    
    # 3. Validar features
    print("🔍 Validando features...")
    
    # Check NaN
    nan_count = X.isna().sum().sum()
    if nan_count > 0:
        print(f"⚠️  Encontrados {nan_count} valores NaN - rellenando con 0")
        X = X.fillna(0)
    else:
        print("✓ No hay valores NaN")
    
    # Check infinite
    inf_count = np.isinf(X.select_dtypes(include=[np.number])).sum().sum()
    if inf_count > 0:
        print(f"⚠️  Encontrados {inf_count} valores infinitos - rellenando con 0")
        X = X.replace([np.inf, -np.inf], 0)
    else:
        print("✓ No hay valores infinitos")
    
    print()
    
    # 4. Entrenar ensemble
    print("🤖 Entrenando Ensemble Model...")
    print("-" * 70)
    
    model = EnsembleBettingModel(sport='soccer')
    
    try:
        metrics = model.train(
            X=X,
            y=y,
            calibrate=True,  # CRÍTICO para betting
            n_splits=3  # TimeSeriesSplit folds
        )
        
        print()
        print("="*70)
        print("✅ ENTRENAMIENTO COMPLETADO")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error durante el entrenamiento: {e}")
        logger.exception("Error en entrenamiento")
        return
    
    # 5. Mostrar resultados
    print("\n📊 RESULTADOS FINALES:\n")
    
    print(f"  Modelos base: {', '.join(metrics.get('base_models', []))}")
    print(f"  Samples: {metrics['n_samples']}")
    print(f"  Features: {metrics['n_features']}")
    print()
    
    print("  Métricas de Validación (Cross-Validation):")
    print(f"    Accuracy:     {metrics['cv_accuracy']:.1%} ± {metrics['cv_accuracy_std']:.1%}")
    print(f"    Log Loss:     {metrics['cv_log_loss']:.4f}")
    print(f"    Brier Score:  {metrics['cv_brier_score']:.4f}")
    
    if metrics.get('calibrated'):
        print(f"\n  Calibración:")
        print(f"    ECE (Expected Calibration Error): {metrics.get('ece_after_calibration', 0):.4f}")
        
        # Interpretación de ECE
        ece = metrics.get('ece_after_calibration', 1.0)
        if ece < 0.05:
            rating = "⭐⭐⭐⭐⭐ EXCELENTE"
        elif ece < 0.10:
            rating = "⭐⭐⭐⭐ BUENO"
        elif ece < 0.15:
            rating = "⭐⭐⭐ ACEPTABLE"
        else:
            rating = "⭐⭐ MEJORABLE"
        
        print(f"    Rating: {rating}")
    
    print()
    
    # 6. Comparación con benchmarks
    print("📈 Benchmarks para Betting:")
    print(f"  Accuracy:    {metrics['cv_accuracy']:.1%}  (target: > 52%)")
    print(f"  Log Loss:    {metrics['cv_log_loss']:.4f}  (target: < 1.10)")
    print(f"  Brier Score: {metrics['cv_brier_score']:.4f}  (target: < 0.20)")
    
    if metrics.get('calibrated'):
        print(f"  ECE:         {metrics.get('ece_after_calibration', 1):.4f}  (target: < 0.05)")
    
    print()
    
    # Evaluación
    meets_targets = (
        metrics['cv_accuracy'] > 0.52 and
        metrics['cv_log_loss'] < 1.10 and
        metrics['cv_brier_score'] < 0.20 and
        metrics.get('ece_after_calibration', 1.0) < 0.05
    )
    
    if meets_targets:
        print("✅ El modelo CUMPLE con todos los targets - Listo para producción")
    else:
        print("⚠️  El modelo NO cumple todos los targets - Considerar:")
        if metrics['cv_accuracy'] <= 0.52:
            print("  • Aumentar datos históricos (ejecutar bootstrap con más meses)")
        if metrics['cv_log_loss'] >= 1.10:
            print("  • Revisar feature engineering")
        if metrics.get('ece_after_calibration', 1) >= 0.05:
            print("  • Ajustar método de calibración")
    
    print()
    
    # 7. Guardar modelo
    print("💾 Guardando modelo...")
    
    output_file = 'models/soccer_ensemble.pkl'
    model.save(output_file)
    
    print(f"✓ Modelo guardado: {output_file}")
    print(f"✓ Métricas guardadas: {output_file.replace('.pkl', '_metrics.json')}")
    print()
    
    # 8. Feature importance
    print("🎯 Top 15 Features más importantes:\n")
    
    try:
        importance = model.get_feature_importance(method='mean')
        
        for i, (feature, row) in enumerate(importance.head(15).iterrows(), 1):
            print(f"  {i:2d}. {feature:30s} {row['importance']:.4f}")
        
        # Guardar feature importance completa
        importance_file = 'models/soccer_ensemble_feature_importance.csv'
        importance.to_csv(importance_file)
        print(f"\n✓ Feature importance guardado: {importance_file}")
        
    except Exception as e:
        print(f"⚠️  No se pudo calcular feature importance: {e}")
    
    print()
    
    # 9. Siguiente paso
    print("="*70)
    print("🎯 PRÓXIMOS PASOS:")
    print("="*70)
    print()
    print("1. Integrar en predictor.py:")
    print("   from src.models.ensemble_model import EnsembleBettingModel")
    print("   model = EnsembleBettingModel.load('models/soccer_ensemble.pkl')")
    print()
    print("2. Backtest del modelo:")
    print("   python -m src.backtesting.backtest_engine")
    print()
    print("3. Paper trading 30 días")
    print()
    print("4. Validar CLV > 2% antes de go-live")
    print()


if __name__ == "__main__":
    import numpy as np
    main()
