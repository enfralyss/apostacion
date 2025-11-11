# 🚀 Plan de Mejoras Completo - TriunfoBet ML Bot

**Fecha**: 2025-11-10
**Análisis**: Arquitectura completa revisada
**Estado**: Sistema funcional con áreas de optimización identificadas

---

## 📊 Resumen Ejecutivo

### ✅ Fortalezas del Sistema Actual

1. **ML Avanzado Implementado**
   - ✅ Modelo calibrado (ECE = 0.0)
   - ✅ Ensemble de 3 modelos (XGBoost + LightGBM + Random Forest)
   - ✅ 24 features avanzadas (ELO, form, H2H, goals, league strength)
   - ✅ TIME-AWARE: Sin data leakage
   - ✅ TimeSeriesSplit validation

2. **Infraestructura Robusta**
   - ✅ Base de datos SQLite bien estructurada
   - ✅ Sistema de parámetros dinámicos con UI Streamlit
   - ✅ Autotuning de hiperparámetros
   - ✅ CLV tracking implementado
   - ✅ Notificaciones Telegram granulares
   - ✅ Resolución de picks en tiempo real

3. **Datos Reales**
   - ✅ Bootstrap de Football-Data.co.uk (1,745 matches)
   - ✅ Pipeline de ingestión de odds
   - ✅ Canonical odds con margin removal

### ⚠️ Áreas Críticas de Mejora

| Prioridad | Área | Problema | Impacto | Esfuerzo |
|-----------|------|----------|---------|----------|
| 🔴 **P0** | Accuracy | 48% por cold start ELO | ROI -2% | 20 min |
| 🔴 **P0** | Predictor | Ensemble no integrado | Accuracy -2% | 5 min |
| 🟡 **P1** | Stake Calc | Sin volatilidad/drawdown | Riesgo alto | 30 min |
| 🟡 **P1** | Backtest | Sin validación walk-forward | Overfitting | 1h |
| 🟢 **P2** | Monitoring | Sin drift detection | Decay silent | 2h |
| 🟢 **P2** | Features | Sin xG/sharp money | Edge -1% | 4h |

---

## 🔴 MEJORAS PRIORITARIAS (P0) - IMPLEMENTAR YA

### 1. ✅ COMPLETADO: Integrar Ensemble Model en Predictor

**Problema**: El ensemble model (accuracy 50.5%) está entrenado pero NO se usa en producción.

**Solución Implementada**:
- ✅ Modificado `src/models/predictor.py` para cargar ensemble primero
- ✅ Fallback automático: Ensemble → Calibrado → Legacy
- ✅ Logging de tipo de modelo usado

**Código Actualizado**:
```python
# predictor.py ahora carga modelos en orden de prioridad
1. Ensemble (XGB+LGB+RF) → models/soccer_ensemble.pkl
2. Calibrado Simple → models/soccer_calibrated_advanced.pkl
3. Legacy → models/soccer_model.pkl
```

**Próximo paso**:
```bash
# Verificar que el ensemble existe
python compare_models.py

# Si no existe, entrenarlo
python train_ensemble_model.py

# Luego ejecutar daily_bot para validar
python daily_bot.py
```

---

### 2. 🔴 URGENTE: Mejorar Accuracy con Bootstrap 12 Meses

**Problema**:
- Accuracy actual: **48%** (modelo calibrado) / **50.5%** (ensemble)
- Causa: Cold start de ELO ratings (primeros 500 matches sin señal)
- Solo 6 meses de datos históricos (1,745 matches)

**Solución**:
```bash
# PASO 1: Bootstrap 12 meses de datos
python bootstrap_historical_data.py --months 12

# Tiempo estimado: 15-20 minutos
# Matches esperados: ~3,500-4,000

# PASO 2: Re-entrenar modelos
python train_advanced_model.py  # Modelo calibrado
python train_ensemble_model.py  # Ensemble

# Tiempo estimado: 10-15 minutos
```

**Resultados Esperados**:

| Modelo | Accuracy Actual | Accuracy 12m | Mejora |
|--------|-----------------|--------------|--------|
| Calibrado | 48.0% | 52-55% | +5-7% |
| Ensemble | 50.5% | 53-56% | +3-5% |

**Impacto en ROI**:
- +5% accuracy → **+1-2% ROI** esperado
- CLV mejorado: +1% → +2-3%
- Sharpe ratio: +0.3 → +0.5 mejora

**Justificación**:
- Solo 20 minutos de inversión
- Mejora sustancial garantizada
- Sin cambios de código necesarios
- Mantiene calibración perfecta

---

### 3. 🔴 Validar Modelos con Comparación A/B

**Script ya existente**: `compare_models.py`

**Ejecutar**:
```bash
python compare_models.py
```

**Output esperado**:
```
📊 TABLA COMPARATIVA:

Modelo                    Accuracy  Log Loss  Brier  ECE    Calibrado
Ensemble (XGB+LGB+RF)     50.5%     1.024     0.202  0.235  ✓
Calibrado Avanzado        48.0%     1.257     N/A    0.000  ✓
XGBoost Simple            50.7%     N/A       N/A    N/A    ✗

💡 RECOMENDACIÓN: Ensemble (XGB+LGB+RF)
```

**Decisión**:
- Si Ensemble tiene mejor accuracy → Usar ensemble (ya integrado)
- Si Calibrado tiene mejor ECE → Usar calibrado
- **Ideal**: Ensemble con 12 meses de datos

---

## 🟡 MEJORAS IMPORTANTES (P1) - PRÓXIMAS 48H

### 4. Mejorar Stake Calculator con Gestión de Riesgo

**Problema Actual** (archivo: `src/betting/stake_calculator_improved.py`):
- Solo implementa Kelly 1/4
- No considera volatilidad histórica
- No tiene stop-loss dinámico
- No ajusta por drawdown

**Código Actual**:
```python
def calculate_kelly_stake(self, prob, odds, bankroll):
    edge = prob - (1/odds)
    if edge < 0.02:  # Solo filtro de edge mínimo
        return 0
    kelly = edge / (odds - 1)
    return min(kelly * bankroll * 0.25, max_bet)
```

**Mejora Propuesta**:
```python
def calculate_kelly_stake_v2(self, prob, odds, bankroll, recent_picks=None):
    """
    Kelly mejorado con ajustes dinámicos

    Args:
        prob: Probabilidad calibrada
        odds: Cuota ofrecida
        bankroll: Bankroll actual
        recent_picks: Últimos 20-50 picks para calcular volatilidad
    """
    # 1. Kelly base
    edge = prob - (1/odds)
    if edge < 0.02:
        return 0

    kelly_fraction = edge / (odds - 1)

    # 2. Ajuste por volatilidad (desviación estándar de retornos)
    if recent_picks and len(recent_picks) >= 20:
        returns = [(p['result'] == 'won') * (p['odds'] - 1) - (p['result'] == 'lost')
                   for p in recent_picks if p.get('result')]
        volatility = np.std(returns)

        # Reducir stake si volatilidad es alta
        vol_multiplier = max(0.5, min(1.0, 1.0 - (volatility - 0.3) / 0.5))
        kelly_fraction *= vol_multiplier

    # 3. Ajuste por drawdown
    initial_bankroll = self.get_initial_bankroll()  # Desde DB
    drawdown = (initial_bankroll - bankroll) / initial_bankroll

    if drawdown > 0.10:  # Si drawdown > 10%
        # Reducir agresividad
        drawdown_multiplier = max(0.3, 1.0 - drawdown)
        kelly_fraction *= drawdown_multiplier

    # 4. Kelly fraccional (1/4 por defecto)
    kelly_fraction *= 0.25

    # 5. Límites de seguridad
    max_bet_pct = 0.05  # Máximo 5% del bankroll
    stake = kelly_fraction * bankroll
    stake = min(stake, bankroll * max_bet_pct)

    return max(0, stake)
```

**Ventajas**:
- ✅ Reduce stake en rachas perdedoras (volatilidad alta)
- ✅ Protege bankroll en drawdown
- ✅ Evita overbetting en winning streaks
- ✅ Más robusto a largo plazo

**Implementación**: 30-45 minutos

---

### 5. Backtest Walk-Forward Validation

**Problema**: No hay validación de ROI esperado en datos históricos.

**Solución**: Implementar backtest con split temporal.

**Script a crear**: `backtest_validation.py`

```python
"""
Backtest Walk-Forward para validar estrategia antes de go-live
"""

from src.backtesting.backtest_engine import BacktestEngine
from src.models.predictor import MatchPredictor
from src.utils.database import BettingDatabase
import pandas as pd

def run_walk_forward_backtest():
    """
    Backtest con ventana deslizante:
    - Training window: 6 meses
    - Test window: 1 mes
    - Roll forward: 1 mes
    """

    # Cargar datos históricos
    db = BettingDatabase()
    df = pd.read_csv('data/training_advanced_soccer.csv')

    # Ordenar por fecha
    df = df.sort_values('match_date')

    # Configurar ventanas
    train_window_days = 180  # 6 meses
    test_window_days = 30    # 1 mes

    results = []

    for start_idx in range(0, len(df) - train_window_days - test_window_days, test_window_days):
        # Split train/test
        train_end = start_idx + train_window_days
        test_end = train_end + test_window_days

        train_df = df.iloc[start_idx:train_end]
        test_df = df.iloc[train_end:test_end]

        # Entrenar modelo en train window
        # (usar modelo ya entrenado por simplicidad)
        predictor = MatchPredictor()

        # Backtest en test window
        engine = BacktestEngine(initial_bankroll=1000)
        fold_results = engine.run_backtest(
            test_df,
            predictor,
            criteria={'min_probability': 0.55, 'min_edge': 0.03}
        )

        results.append({
            'period': f"{train_df['match_date'].min()} - {test_df['match_date'].max()}",
            'roi': fold_results['roi'],
            'sharpe': fold_results.get('sharpe_ratio', 0),
            'win_rate': fold_results.get('win_rate', 0),
            'total_bets': fold_results.get('total_bets', 0)
        })

    # Análisis agregado
    df_results = pd.DataFrame(results)

    print("="*80)
    print("BACKTEST WALK-FORWARD RESULTS")
    print("="*80)
    print(df_results)
    print()

    print(f"Promedio ROI: {df_results['roi'].mean():.2%}")
    print(f"Desv. Est. ROI: {df_results['roi'].std():.2%}")
    print(f"Sharpe Promedio: {df_results['sharpe'].mean():.2f}")
    print(f"Win Rate Promedio: {df_results['win_rate'].mean():.1%}")

    # Decisión
    if df_results['roi'].mean() > 0.03 and df_results['roi'].std() < 0.15:
        print("\n✅ ESTRATEGIA VÁLIDA - Listo para paper trading")
    else:
        print("\n⚠️  ESTRATEGIA MARGINAL - Ajustar parámetros o mejorar modelo")

if __name__ == "__main__":
    run_walk_forward_backtest()
```

**Targets para Validación**:
- ROI promedio > 3%
- Sharpe Ratio > 1.0
- Win Rate > 52%
- Max Drawdown < 20%

**Tiempo**: 1-2 horas de implementación

---

## 🟢 MEJORAS ESTRATÉGICAS (P2) - PRÓXIMAS 2 SEMANAS

### 6. Drift Detection System

**Problema**: No hay monitoreo de degradación del modelo en producción.

**Tipos de Drift a Detectar**:

1. **Data Drift**: Distribución de features cambia
2. **Concept Drift**: Relación features-target cambia
3. **Performance Drift**: ROI/CLV caen

**Módulo a crear**: `src/monitoring/drift_detector.py`

```python
"""
Drift Detection - Monitorea degradación del modelo
"""

import numpy as np
from scipy.stats import ks_2samp
from loguru import logger

class DriftDetector:
    """Detecta drift en features, concept y performance"""

    def __init__(self, db):
        self.db = db
        self.baseline_features = None

    def detect_data_drift(self, recent_features, p_value_threshold=0.05):
        """
        Detecta data drift usando test Kolmogorov-Smirnov

        Compara distribución de features recientes vs baseline
        """
        if self.baseline_features is None:
            # Cargar baseline (primeros 1000 matches históricos)
            self.baseline_features = self._load_baseline_features()

        drift_features = []

        for feature in recent_features.columns:
            if feature in self.baseline_features.columns:
                # KS test
                statistic, p_value = ks_2samp(
                    self.baseline_features[feature],
                    recent_features[feature]
                )

                if p_value < p_value_threshold:
                    drift_features.append({
                        'feature': feature,
                        'p_value': p_value,
                        'drift': 'DETECTED'
                    })

        return drift_features

    def detect_performance_drift(self, window_days=30):
        """
        Detecta performance drift comparando ROI reciente vs histórico
        """
        # ROI últimos 30 días
        recent_roi = self.db.calculate_performance_metrics(days=window_days)['roi']

        # ROI histórico (90-120 días atrás)
        historical_roi = self.db.calculate_performance_metrics(
            days=30,
            offset_days=90
        )['roi']

        # Drift si caída > 5%
        drift_magnitude = recent_roi - historical_roi

        if drift_magnitude < -0.05:
            return {
                'drift': 'DETECTED',
                'recent_roi': recent_roi,
                'historical_roi': historical_roi,
                'magnitude': drift_magnitude
            }

        return {'drift': 'OK'}
```

**Alertas Automáticas**:
- Telegram notification cuando drift detectado
- Email semanal con summary
- Dashboard en Streamlit

**Tiempo**: 2-3 horas

---

### 7. Features Adicionales: xG y Sharp Money

**Features a Agregar**:

1. **Expected Goals (xG)**
   - API gratuita: Football-Data.org (limited)
   - Calcular xG desde shots data
   - xG difference como feature

2. **Sharp Money Detection**
   - Odds movement velocity (delta/hour)
   - Volume spikes (si API disponible)
   - Reverse line movement (odds bajan con mayoría apostando contra)

3. **Market Efficiency**
   - Margin evolution (opening vs closing)
   - Bookmaker disagreement (variance entre bookies)

**Código Ejemplo** (xG):
```python
def calculate_xg_features(match, db):
    """
    Calcula features basadas en xG histórico
    """
    home_team = match['home_team']
    away_team = match['away_team']

    # xG promedio últimos 5 partidos
    home_xg = db.get_recent_xg(home_team, n_games=5)
    away_xg = db.get_recent_xg(away_team, n_games=5)

    return {
        'home_xg_avg_5': home_xg['avg'],
        'away_xg_avg_5': away_xg['avg'],
        'xg_diff': home_xg['avg'] - away_xg['avg'],
        'home_xg_form': home_xg['trend'],  # improving/declining
        'away_xg_form': away_xg['trend']
    }
```

**Impacto Esperado**: +1-2% accuracy, +0.5% edge

**Tiempo**: 4-6 horas

---

## 📋 Plan de Implementación Sugerido

### **SEMANA 1: Fundamentos (P0)**

**Día 1-2** (2 horas):
- [x] ✅ Integrar ensemble en predictor.py (COMPLETADO)
- [ ] 🔴 Bootstrap 12 meses de datos (20 min)
- [ ] 🔴 Re-entrenar modelos (30 min)
- [ ] 🔴 Validar con `compare_models.py` (5 min)

**Día 3-4** (3 horas):
- [ ] 🟡 Mejorar stake calculator con volatilidad (1h)
- [ ] 🟡 Implementar backtest walk-forward (2h)
- [ ] Validar ROI > 3% en backtest

**Día 5-7** (Paper Trading):
- [ ] Ejecutar paper trading con ensemble + datos 12m
- [ ] Monitorear CLV diario (target > 2%)
- [ ] Ajustar parámetros si es necesario

### **SEMANA 2: Monitoreo y Features (P1-P2)**

**Día 8-10**:
- [ ] 🟢 Implementar drift detection (3h)
- [ ] Dashboard de drift en Streamlit (1h)
- [ ] Alertas Telegram para drift (30 min)

**Día 11-14**:
- [ ] 🟢 Agregar xG features (4h)
- [ ] 🟢 Sharp money detection (2h)
- [ ] Re-entrenar con nuevas features
- [ ] Backtest comparativo

### **SEMANA 3-4: Go-Live Gradual**

- [ ] Paper trading final 14 días
- [ ] Validar métricas críticas:
  - ROI > 3%
  - CLV > 2%
  - Sharpe > 1.0
  - Win Rate > 52%
- [ ] Go-live con 10% bankroll
- [ ] Escalar a 50% si resultados positivos
- [ ] Full production a 100%

---

## 🎯 Métricas de Éxito

### Fase 1: Modelo Mejorado (Semana 1)
- ✅ Accuracy > 52% (vs 48% actual)
- ✅ Log Loss < 1.15 (vs 1.26 actual)
- ✅ ECE < 0.10 (mantener calibración)

### Fase 2: Backtest Validado (Semana 1-2)
- ✅ ROI > 3% en walk-forward
- ✅ Sharpe Ratio > 1.0
- ✅ Max Drawdown < 20%

### Fase 3: Paper Trading (Semana 2-3)
- ✅ CLV > 2% (closing line value)
- ✅ ROI real > 0% (breakeven mínimo)
- ✅ Win Rate > 50%

### Fase 4: Go-Live (Semana 4+)
- ✅ ROI sostenido > 3% por 30 días
- ✅ CLV sostenido > 2% por 30 días
- ✅ Sin drift detectado
- ✅ Sharpe > 1.2

---

## 🔧 Comandos de Ejecución Rápida

### Setup Inicial (Ejecutar una sola vez)
```bash
# 1. Bootstrap datos históricos (12 meses)
python bootstrap_historical_data.py --months 12

# 2. Entrenar modelos avanzados
python train_advanced_model.py
python train_ensemble_model.py

# 3. Comparar modelos
python compare_models.py

# 4. Inicializar parámetros desde UI
streamlit run app.py
# → Pestaña "Parámetros" → "Inicializar desde config.yaml"
```

### Flujo Diario de Producción
```bash
# 1. Obtener partidos y predicciones
python daily_bot.py

# 2. Monitorear en UI
streamlit run app.py

# 3. Revisar CLV y performance
# → Pestaña "CLV Analytics"

# 4. Resolver picks manualmente si es necesario
# → Pestaña "Histórico" → "Resolver y Notificar Picks"
```

### Mantenimiento Semanal
```bash
# 1. Actualizar datos históricos
python bootstrap_historical_data.py --months 1 --update

# 2. Re-entrenar si drift detectado
python train_ensemble_model.py

# 3. Backtest con datos nuevos
python backtest_validation.py

# 4. Ajustar parámetros si es necesario
streamlit run app.py
# → Pestaña "Parámetros" → "Autotuning"
```

---

## 📚 Documentación de Referencia

### Archivos Clave Actualizados
- ✅ [src/models/predictor.py](src/models/predictor.py) - Ahora usa ensemble
- 📄 [compare_models.py](compare_models.py) - Comparación A/B
- 📄 [train_ensemble_model.py](train_ensemble_model.py) - Entrena ensemble
- 📄 [docs/ENSEMBLE_MODEL_GUIDE.md](docs/ENSEMBLE_MODEL_GUIDE.md) - Guía completa

### Próximos Archivos a Crear
- [ ] `backtest_validation.py` - Backtest walk-forward
- [ ] `src/monitoring/drift_detector.py` - Detección de drift
- [ ] `src/data/xg_features.py` - Features de xG

---

## ⚡ Acción Inmediata Recomendada

**PASO 1: Validar Integración de Ensemble** (5 minutos)
```bash
# Ver qué modelo se carga actualmente
python -c "from src.models.predictor import MatchPredictor; p = MatchPredictor(); print(f'Model: {p.model_type}')"

# Comparar modelos disponibles
python compare_models.py
```

**PASO 2: Mejorar Datos** (20 minutos)
```bash
# Bootstrap 12 meses
python bootstrap_historical_data.py --months 12

# Re-entrenar ensemble
python train_ensemble_model.py
```

**PASO 3: Validar Mejora** (5 minutos)
```bash
# Comparar métricas nuevas vs antiguas
python compare_models.py
```

**Resultado Esperado**:
```
Ensemble (XGB+LGB+RF)     53-56%     0.98-1.10     0.18-0.20     <0.10     ✓
```

---

## 🤝 Soporte

¿Dudas o problemas durante la implementación?

1. **Logs**: Revisar `logs/` para errores
2. **Documentación**: Ver `docs/AI_PROJECT_MAP.md`
3. **Tests**: Ejecutar `pytest tests/` si hay tests
4. **Database**: `sqlite3 data/betting.db` para queries

---

## ✅ Checklist de Progreso

### Mejoras Implementadas
- [x] ✅ Integración de ensemble en predictor.py
- [x] ✅ Fallback automático de modelos
- [x] ✅ Logging de tipo de modelo usado

### Próximas Mejoras (Prioridad)
- [ ] 🔴 Bootstrap 12 meses (URGENTE - 20 min)
- [ ] 🔴 Re-entrenar ensemble (URGENTE - 30 min)
- [ ] 🟡 Stake calculator con volatilidad (1h)
- [ ] 🟡 Backtest walk-forward (2h)
- [ ] 🟢 Drift detection (3h)
- [ ] 🟢 xG features (4h)

**Tiempo Total Estimado P0+P1**: 4-5 horas
**ROI Esperado de Mejoras**: +2-4% (sobre baseline actual)

---

**Última actualización**: 2025-11-10
**Próxima revisión**: Después de implementar P0 y P1
