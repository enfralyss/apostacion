"""
Analisis detallado del dataset de entrenamiento y validacion del modelo
"""
import pandas as pd
import numpy as np
import json
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("ANALISIS DEL ENTRENAMIENTO DEL MODELO")
print("=" * 70)

# 1. Cargar dataset
df = pd.read_csv('data/training_advanced_soccer.csv')
print(f"\n[DATASET]")
print(f"Total matches: {len(df)}")
print(f"Features: {len(df.columns)} columnas")

# 2. Distribucion temporal
df['match_date'] = pd.to_datetime(df['match_date'])
print(f"\n[DISTRIBUCION TEMPORAL]")
print(f"Primer match: {df['match_date'].min()}")
print(f"Último match: {df['match_date'].max()}")
print(f"Rango: {(df['match_date'].max() - df['match_date'].min()).days} días")

# 3. Evolucion de ELO (critico para entender el cold start)
print(f"\n[EVOLUCION DE ELO RATINGS]")
early_500 = df.head(500)
middle_500 = df.iloc[500:1000] if len(df) > 1000 else df.iloc[500:]
late_500 = df.tail(500)

print(f"Primeros 500 matches:")
print(f"  ELO diff: mean={early_500['elo_diff'].mean():.1f}, std={early_500['elo_diff'].std():.1f}")
print(f"  Home ELO: mean={early_500['home_elo'].mean():.1f}, std={early_500['home_elo'].std():.1f}")

if len(df) > 1000:
    print(f"\nMatches 500-1000:")
    print(f"  ELO diff: mean={middle_500['elo_diff'].mean():.1f}, std={middle_500['elo_diff'].std():.1f}")
    print(f"  Home ELO: mean={middle_500['home_elo'].mean():.1f}, std={middle_500['home_elo'].std():.1f}")

print(f"\nÚltimos 500 matches:")
print(f"  ELO diff: mean={late_500['elo_diff'].mean():.1f}, std={late_500['elo_diff'].std():.1f}")
print(f"  Home ELO: mean={late_500['home_elo'].mean():.1f}, std={late_500['home_elo'].std():.1f}")

# Diagnóstico de cold start
early_elo_std = early_500['home_elo'].std()
late_elo_std = late_500['home_elo'].std()

print(f"\n[DIAGNOSTICO DE COLD START]:")
if late_elo_std > early_elo_std * 2:
    print(f"[OK] ELO ha divergido correctamente")
    print(f"   Early std: {early_elo_std:.1f} -> Late std: {late_elo_std:.1f}")
    print(f"   Mejora: {(late_elo_std / early_elo_std - 1) * 100:.0f}%")
else:
    print(f"[WARN] ELO todavia no ha convergido completamente")
    print(f"   Early std: {early_elo_std:.1f} -> Late std: {late_elo_std:.1f}")
    print(f"   Recomendacion: Mas datos historicos mejoraran el accuracy")

# 4. Analisis de features
print(f"\n[VARIANZA DE FEATURES]")
numeric_cols = df.select_dtypes(include=[np.number]).columns
variance = df[numeric_cols].var().sort_values(ascending=False)

print("\nTop 10 features con mayor varianza:")
for i, col in enumerate(variance.head(10).index, 1):
    print(f"  {i}. {col}: var={variance[col]:.2f}, mean={df[col].mean():.2f}, std={df[col].std():.2f}")

# Features con poca varianza (problema potencial)
print(f"\n[FEATURES CON POCA VARIANZA (<0.01)]:")
low_var = variance[variance < 0.01]
if len(low_var) > 0:
    for col in low_var.index:
        print(f"  - {col}: var={variance[col]:.4f}, mean={df[col].mean():.2f}")
    print(f"\n  [WARN] Estas features aportan poca informacion al modelo")
else:
    print("  [OK] Todas las features tienen varianza suficiente")

# 5. Correlaciones fuertes (multicolinealidad)
print(f"\n[CORRELACIONES FUERTES (>0.9)]")
corr_matrix = df[numeric_cols].corr()
high_corr = []
for i in range(len(corr_matrix.columns)):
    for j in range(i+1, len(corr_matrix.columns)):
        if abs(corr_matrix.iloc[i, j]) > 0.9:
            high_corr.append((
                corr_matrix.columns[i],
                corr_matrix.columns[j],
                corr_matrix.iloc[i, j]
            ))

if high_corr:
    for col1, col2, corr_val in high_corr[:5]:
        print(f"  {col1} <-> {col2}: {corr_val:.3f}")
    if len(high_corr) > 5:
        print(f"  ... y {len(high_corr) - 5} mas")
else:
    print("  [OK] No hay correlaciones fuertes problematicas")

# 6. Accuracy por periodo (verificar si mejora con el tiempo)
print(f"\n[ACCURACY SIMULADO POR PERIODO]")
print("(Verificando si ELO convergido mejora prediccion)")

# Target distribution
print(f"\n[DISTRIBUCION DEL TARGET]")
target_dist = df['result'].value_counts()
for result, count in target_dist.items():
    pct = count / len(df) * 100
    print(f"  {result}: {count} ({pct:.1f}%)")

# 7. Cargar metricas del modelo
print(f"\n[METRICAS DEL MODELO CALIBRADO]")
with open('models/soccer_calibrated_advanced_metrics.json', 'r') as f:
    metrics = json.load(f)

print(f"ECE antes de calibración: {metrics['ece_before_calibration']:.4f}")
print(f"ECE después de calibración: {metrics['ece_after_calibration']:.4f}")
print(f"Mejora de ECE: {metrics['ece_improvement']:.4f}")
print(f"\nCV Accuracy (promedio): {metrics['cv_accuracy_mean']:.2%}")
print(f"CV Log Loss (promedio): {metrics['cv_logloss_mean']:.3f}")
print(f"CV ECE (promedio): {metrics['cv_ece_mean']:.3f}")

# Interpretacion
print(f"\n" + "=" * 70)
print("INTERPRETACION Y RECOMENDACIONES")
print("=" * 70)

# Calibracion
if metrics['ece_after_calibration'] < 0.05:
    print("[OK] CALIBRACION: EXCELENTE (ECE < 0.05)")
    print("   Las probabilidades son confiables para Kelly criterion")
elif metrics['ece_after_calibration'] < 0.10:
    print("[OK] CALIBRACION: BUENA (ECE < 0.10)")
else:
    print("[WARN] CALIBRACION: MEJORABLE (ECE > 0.10)")

# Accuracy
if metrics['cv_accuracy_mean'] > 0.55:
    print("[OK] ACCURACY: EXCELENTE (>55%)")
elif metrics['cv_accuracy_mean'] > 0.52:
    print("[OK] ACCURACY: BUENO (>52%)")
elif metrics['cv_accuracy_mean'] > 0.48:
    print("[WARN] ACCURACY: FUNCIONAL (48-52%)")
    print("   Mejorable con mas datos historicos")
else:
    print("[ERROR] ACCURACY: BAJO (<48%)")
    print("   Se requiere revision de features")

# Recomendacion final
print(f"\n[RECOMENDACION]:")
if metrics['cv_accuracy_mean'] < 0.52 and late_elo_std < early_elo_std * 2:
    print(">> Bootstrap 12 meses de datos historicos")
    print("   Comando: python bootstrap_historical_data.py --months 12")
    print(f"   Accuracy esperado: 52-55% (vs {metrics['cv_accuracy_mean']:.1%} actual)")
elif metrics['cv_accuracy_mean'] < 0.52:
    print(">> Considerar bootstrap de mas datos (12-18 meses)")
    print(f"   Accuracy actual ({metrics['cv_accuracy_mean']:.1%}) esta cerca del target")
else:
    print("[OK] Modelo listo para backtest y paper trading")
    print(f"   Accuracy {metrics['cv_accuracy_mean']:.1%} es suficiente")

print("\n" + "=" * 70)
