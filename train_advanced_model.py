"""
Train Advanced Model - Script de entrenamiento con features avanzadas y calibración

USO:
    python train_advanced_model.py

Este script:
1. Carga datos históricos de la DB
2. Genera features avanzadas (ELO, form, H2H)
3. Entrena modelo calibrado con TimeSeriesSplit
4. Guarda modelo y métricas
5. Compara con modelo baseline
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.database import BettingDatabase
from src.data.feature_integration import build_training_dataset_with_advanced_features
from src.models.calibrated_model_simple import CalibratedBettingModel
from loguru import logger
import pandas as pd


def main():
    logger.info("=" * 70)
    logger.info("ADVANCED MODEL TRAINING - WITH CALIBRATION")
    logger.info("=" * 70)

    # 1. Inicializar DB
    db = BettingDatabase()

    # 2. Build training dataset con features avanzadas
    logger.info("\n📊 Step 1: Building training dataset with advanced features...")

    df_soccer = build_training_dataset_with_advanced_features(
        db,
        sport='soccer',
        min_rows=100
    )

    if df_soccer.empty:
        logger.error("❌ No data available for training")
        logger.error("Run: python bootstrap_historical_data.py --months 6")
        return

    logger.info(f"✅ Dataset ready: {len(df_soccer)} matches")
    logger.info(f"Features: {len(df_soccer.columns)} columns")

    # Mostrar distribución de target
    logger.info("\nTarget distribution:")
    result_counts = df_soccer['result'].value_counts()
    for result, count in result_counts.items():
        pct = count / len(df_soccer) * 100
        logger.info(f"  {result}: {count} ({pct:.1f}%)")

    # 3. Train calibrated model
    logger.info("\n🧠 Step 2: Training calibrated model...")

    model = CalibratedBettingModel(sport='soccer', model_type='xgboost')

    metrics = model.train(
        df_soccer,
        n_splits=3,
        calibration_method='isotonic'
    )

    # 4. Show metrics
    logger.info("\n" + "=" * 70)
    logger.info("TRAINING RESULTS")
    logger.info("=" * 70)

    logger.info(f"\n📈 Cross-Validation Metrics:")
    logger.info(f"  Accuracy:  {metrics['cv_accuracy_mean']:.3f}")
    logger.info(f"  Log Loss:  {metrics['cv_logloss_mean']:.3f}")
    logger.info(f"  ECE:       {metrics['cv_ece_mean']:.3f}")

    logger.info(f"\n🎯 Calibration Improvement:")
    logger.info(f"  ECE before: {metrics['ece_before_calibration']:.4f}")
    logger.info(f"  ECE after:  {metrics['ece_after_calibration']:.4f}")
    logger.info(f"  Improvement: {metrics['ece_improvement']:.4f}")

    # Interpretar ECE
    ece_after = metrics['ece_after_calibration']
    if ece_after < 0.05:
        calibration_rating = "⭐⭐⭐⭐⭐ EXCELLENT"
    elif ece_after < 0.10:
        calibration_rating = "⭐⭐⭐⭐ GOOD"
    elif ece_after < 0.15:
        calibration_rating = "⭐⭐⭐ ACCEPTABLE"
    else:
        calibration_rating = "⭐⭐ NEEDS IMPROVEMENT"

    logger.info(f"\n{calibration_rating}")

    # 5. Save model
    logger.info("\n💾 Step 3: Saving model...")

    model_path = "models/soccer_calibrated_advanced.pkl"
    model.save(model_path)

    logger.info(f"✅ Model saved to {model_path}")

    # 6. Compare with baseline (if exists)
    baseline_path = "models/soccer_model.pkl"
    if os.path.exists(baseline_path):
        logger.info("\n📊 Comparison with baseline:")
        logger.info(f"  Baseline: {baseline_path}")
        logger.info(f"  Advanced: {model_path}")
        logger.info("\n  Use the advanced model in predictions for calibrated probabilities!")
    else:
        logger.info("\n✅ No baseline found - this is your first model")

    # 7. Summary
    logger.info("\n" + "=" * 70)
    logger.info("TRAINING COMPLETED")
    logger.info("=" * 70)
    logger.info("\n✅ Next steps:")
    logger.info("  1. Test predictions: from src.models.calibrated_model_simple import CalibratedBettingModel")
    logger.info("  2. Backtest performance: python test_backtest.py")
    logger.info("  3. Update predictor to use calibrated model")
    logger.info("  4. Run daily_bot.py with calibrated predictions")

    db.close()


if __name__ == "__main__":
    main()
