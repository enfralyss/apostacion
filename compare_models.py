"""
Comparador de Modelos - Compara Single Model vs Ensemble
Ayuda a decidir qué modelo usar en producción
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from loguru import logger


def load_model_metrics(model_path: str) -> dict:
    """Carga métricas guardadas de un modelo"""
    metrics_path = model_path.replace('.pkl', '_metrics.json')
    
    if Path(metrics_path).exists():
        with open(metrics_path, 'r') as f:
            return json.load(f)
    return {}


def compare_models():
    """Compara todos los modelos disponibles"""
    
    print("="*80)
    print("COMPARACIÓN DE MODELOS - Single vs Ensemble")
    print("="*80)
    print()
    
    # Modelos a comparar
    models = {
        'XGBoost Simple': 'models/soccer_model.pkl',
        'Calibrado Avanzado': 'models/soccer_calibrated_advanced.pkl',
        'Ensemble (XGB+LGB+RF)': 'models/soccer_ensemble.pkl'
    }
    
    results = []
    
    for name, path in models.items():
        if not Path(path).exists():
            print(f"⚠️  {name}: No encontrado ({path})")
            continue
        
        metrics = load_model_metrics(path)
        
        if metrics:
            results.append({
                'Modelo': name,
                'Accuracy': metrics.get('cv_accuracy', metrics.get('test_accuracy', 0)),
                'Log Loss': metrics.get('cv_log_loss', metrics.get('test_log_loss', 0)),
                'Brier Score': metrics.get('cv_brier_score', metrics.get('brier_score', 0)),
                'ECE': metrics.get('ece_after_calibration', 0),
                'Samples': metrics.get('n_samples', 0),
                'Features': metrics.get('n_features', 0),
                'Calibrado': '✓' if metrics.get('calibrated', False) else '✗',
                'Path': path
            })
        else:
            print(f"⚠️  {name}: Sin métricas guardadas")
    
    if not results:
        print("\n❌ No se encontraron modelos para comparar")
        print("\n🔧 Soluciones:")
        print("   1. Entrenar modelo simple: python src/models/train_model.py")
        print("   2. Entrenar modelo avanzado: python train_advanced_model.py")
        print("   3. Entrenar ensemble: python train_ensemble_model.py")
        return
    
    # Crear DataFrame
    df = pd.DataFrame(results)
    
    # Ordenar por accuracy
    df = df.sort_values('Accuracy', ascending=False)
    
    print("📊 TABLA COMPARATIVA:\n")
    print(df.to_string(index=False))
    print()
    
    # Análisis detallado
    print("="*80)
    print("📈 ANÁLISIS DETALLADO")
    print("="*80)
    print()
    
    # Mejor modelo por métrica
    print("🏆 Mejor modelo por métrica:\n")
    
    metrics_to_check = [
        ('Accuracy', True, 0.52),  # (nombre, higher_is_better, target)
        ('Log Loss', False, 1.10),
        ('Brier Score', False, 0.20),
        ('ECE', False, 0.05)
    ]
    
    for metric, higher_is_better, target in metrics_to_check:
        if metric not in df.columns:
            continue
        
        if higher_is_better:
            best_idx = df[metric].idxmax()
            best_value = df.loc[best_idx, metric]
            operator = ">"
        else:
            best_idx = df[df[metric] > 0][metric].idxmin() if (df[metric] > 0).any() else df[metric].idxmax()
            best_value = df.loc[best_idx, metric]
            operator = "<"
        
        best_model = df.loc[best_idx, 'Modelo']
        
        # Verificar si cumple target
        meets_target = (
            (higher_is_better and best_value > target) or
            (not higher_is_better and best_value < target)
        )
        
        target_str = f"(target {operator} {target})"
        status = "✅" if meets_target else "⚠️ "
        
        if metric == 'ECE':
            print(f"  {status} {metric:15s}: {best_model:25s} = {best_value:.4f} {target_str}")
        elif metric in ['Log Loss', 'Brier Score']:
            print(f"  {status} {metric:15s}: {best_model:25s} = {best_value:.4f} {target_str}")
        else:
            print(f"  {status} {metric:15s}: {best_model:25s} = {best_value:.1%} {target_str}")
    
    print()
    
    # Recomendación
    print("="*80)
    print("💡 RECOMENDACIÓN")
    print("="*80)
    print()
    
    # Calcular score compuesto
    df['score'] = (
        df['Accuracy'] * 0.4 +
        (1 - df['Log Loss'].clip(0, 2) / 2) * 0.3 +
        (1 - df['Brier Score'].clip(0, 1)) * 0.2 +
        (1 - df['ECE'].clip(0, 1)) * 0.1
    )
    
    best_overall_idx = df['score'].idxmax()
    best_overall = df.loc[best_overall_idx, 'Modelo']
    
    print(f"🎯 Modelo recomendado para PRODUCCIÓN: {best_overall}\n")
    
    # Detalles del mejor modelo
    best_row = df.loc[best_overall_idx]
    
    print("  Métricas:")
    print(f"    Accuracy:     {best_row['Accuracy']:.1%}")
    print(f"    Log Loss:     {best_row['Log Loss']:.4f}")
    print(f"    Brier Score:  {best_row['Brier Score']:.4f}")
    print(f"    ECE:          {best_row['ECE']:.4f}")
    print(f"    Calibrado:    {best_row['Calibrado']}")
    print()
    
    print("  Path:")
    print(f"    {best_row['Path']}")
    print()
    
    # Ventajas
    print("  Ventajas:")
    if 'Ensemble' in best_overall:
        print("    ✓ Mayor robustez (combina 3 modelos)")
        print("    ✓ Menos propenso a overfitting")
        print("    ✓ Mejor generalización")
    elif 'Calibrado' in best_overall:
        print("    ✓ Probabilidades calibradas para Kelly")
        print("    ✓ Features avanzadas (ELO, form, H2H)")
        print("    ✓ Validación temporal (TimeSeriesSplit)")
    else:
        print("    ✓ Más simple y rápido")
        print("    ✓ Menos dependencias")
    print()
    
    # Siguiente paso
    print("  Siguiente paso:")
    print(f"    1. Integrar en predictor.py")
    print(f"    2. Backtest con datos históricos")
    print(f"    3. Paper trading 30 días")
    print(f"    4. Validar CLV > 2% antes de go-live")
    print()
    
    # Comparación de complexity
    print("="*80)
    print("⚙️  COMPLEJIDAD Y RECURSOS")
    print("="*80)
    print()
    
    print(f"{'Modelo':<30} {'Features':<10} {'Calibrado':<12} {'Tipo'}")
    print("-"*80)
    for _, row in df.iterrows():
        model_type = "Ensemble" if "Ensemble" in row['Modelo'] else "Single"
        print(f"{row['Modelo']:<30} {row['Features']:<10} {row['Calibrado']:<12} {model_type}")
    
    print()
    
    # Casos de uso
    print("="*80)
    print("🎯 GUÍA DE SELECCIÓN")
    print("="*80)
    print()
    
    print("Usa ENSEMBLE si:")
    print("  • Buscas máxima accuracy y robustez")
    print("  • Tienes suficientes datos (>1000 matches)")
    print("  • No te importa el tiempo de predicción (+50ms)")
    print()
    
    print("Usa CALIBRADO AVANZADO si:")
    print("  • Necesitas balance accuracy/velocidad")
    print("  • Features avanzadas (ELO, form)")
    print("  • Probabilidades confiables para Kelly")
    print()
    
    print("Usa SIMPLE si:")
    print("  • Estás comenzando / testeando")
    print("  • Datos limitados (<500 matches)")
    print("  • Necesitas predicciones muy rápidas")
    print()


def backtest_comparison():
    """Compara performance en backtest (si hay datos)"""
    
    print("="*80)
    print("🔙 BACKTEST COMPARISON (Work in Progress)")
    print("="*80)
    print()
    
    print("Esta función comparará los modelos en datos históricos out-of-sample")
    print("Implementación futura: Ver src/backtesting/backtest_engine.py")
    print()


if __name__ == "__main__":
    compare_models()
    print()
    # backtest_comparison()  # Descomentar cuando esté implementado
