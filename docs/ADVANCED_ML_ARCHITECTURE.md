# Advanced ML Architecture for TriunfoBet Bot
## Solución Técnica para Rentabilidad Sostenible

**Autor**: AI Analysis
**Fecha**: 2025-01-10
**Versión**: 1.0

---

## 🎯 PROBLEMA CRÍTICO IDENTIFICADO

### Cuello de Botella Principal: "Garbage In, Garbage Out"

**Problema**: El sistema actual entrena modelos ML con **datos sintéticos aleatorios** (`data_generator.py`), no datos reales del mercado.

**Impacto en Rentabilidad**:
- ❌ El modelo aprende patrones inventados, no ineficiencias reales de bookmakers
- ❌ Edge calculado es ficticio - no hay valor real contra el mercado
- ❌ CLV será aleatorio/negativo porque predicciones no tienen base empírica
- ❌ No captura tendencias reales (home advantage, league-specific patterns)
- ❌ Probabilidades sin calibrar → Kelly stakes incorrectos → riesgo de ruina

### Gap Secundario: Sin Calibración de Probabilidades

Las probabilidades raw de XGBoost **NO son confiables** para betting:
- Sobrestiman confianza en clases frecuentes
- Subestiman probabilidades de underdogs
- ECE (Expected Calibration Error) > 0.10 típicamente

---

## 🏗️ ARQUITECTURA PROPUESTA: "TRUE EDGE DETECTION ENGINE"

```
┌────────────────────────────────────────────────────────────────┐
│                   LAYER 1: DATA ACQUISITION                    │
├────────────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│ │ Odds API     │  │ Historical   │  │ External     │          │
│ │ (Real-time)  │  │ Results API  │  │ Stats APIs   │          │
│ └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│        │                  │                  │                  │
│        └──────────────────┼──────────────────┘                  │
│                           ▼                                     │
│              ┌─────────────────────────┐                        │
│              │ BettingDatabase (SQLite)│                        │
│              │ - raw_odds_snapshots    │                        │
│              │ - raw_match_results     │                        │
│              │ - canonical_odds        │                        │
│              │ - engineered_features   │                        │
│              └─────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│              LAYER 2: FEATURE ENGINEERING ENGINE                │
├───────────────────────────┼─────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐        │
│  │ RealDataCollector (TIME-AWARE)                      │        │
│  ├─────────────────────────────────────────────────────┤        │
│  │ • ELO Ratings (K=32, dynamic update)                │        │
│  │ • Rolling Form (exponential decay, last 3/5/10)     │        │
│  │ • Market Signals (implied probs, margin)            │        │
│  │ • Rest days, H2H history, Goals xG                  │        │
│  │ • League strength, Home advantage                   │        │
│  │ • Bookmaker bias detection                          │        │
│  └─────────────────────────────────────────────────────┘        │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│         LAYER 3: CALIBRATED PREDICTION SYSTEM                   │
├───────────────────────────┼─────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Base Model   │  │ Calibration  │  │ Validation   │          │
│  │ (XGBoost)    │─▶│ (Isotonic)   │─▶│ (TimeSeries) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                 │
│         │         ┌────────▼────────┐         │                 │
│         │         │ ECE < 0.05      │         │                 │
│         │         │ Brier Score     │         │                 │
│         │         └─────────────────┘         │                 │
│         │                                     │                 │
│         └─────────────────┬───────────────────┘                 │
│                           │                                     │
│                  ┌────────▼────────┐                            │
│                  │ Calibrated Probs│                            │
│                  │ (Trustworthy)   │                            │
│                  └─────────────────┘                            │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│         LAYER 4: TRUE EDGE DETECTION & VALIDATION               │
├───────────────────────────┼─────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐           │
│  │ Edge Calculator (Enhanced)                       │           │
│  ├──────────────────────────────────────────────────┤           │
│  │ edge = calibrated_prob - market_prob             │           │
│  │      - uncertainty_discount                      │           │
│  │      - margin_adjustment                         │           │
│  │      + market_inefficiency_bonus                 │           │
│  └──────────────────────────────────────────────────┘           │
│                           │                                     │
│  ┌──────────────────────▼──────────────────────────┐           │
│  │ Multi-Strategy Validator                        │           │
│  ├─────────────────────────────────────────────────┤           │
│  │ ✓ Walk-Forward Backtest (2+ years)              │           │
│  │ ✓ Brier Score < 0.20 (excellent calibration)    │           │
│  │ ✓ Expected Calibration Error < 0.05             │           │
│  │ ✓ Backtest ROI > 3% (after costs)               │           │
│  │ ✓ CLV > 2% sustained                            │           │
│  │ ✓ Sharpe Ratio > 1.0                            │           │
│  └─────────────────────────────────────────────────┘           │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│              LAYER 5: ADAPTIVE MONITORING SYSTEM                │
├───────────────────────────┼─────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Drift        │  │ Performance  │  │ Auto         │          │
│  │ Detector     │  │ Dashboard    │  │ Retraining   │          │
│  │ (KS Test)    │  │ (Weekly ROI) │  │ (Triggered)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                   ┌────────▼────────┐                           │
│                   │ Alert if:       │                           │
│                   │ - ROI < -5%     │                           │
│                   │ - KS p < 0.05   │                           │
│                   │ - ECE > 0.10    │                           │
│                   └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 IMPLEMENTACIÓN TÉCNICA

### FASE 1: Real Data Collection Pipeline

**Objetivo**: Reemplazar datos sintéticos con datos históricos reales.

**Archivos Nuevos**:
- `src/data/real_data_collector.py` - Pipeline de recolección de datos reales
- `src/data/external_api_connectors.py` - Conectores a APIs externas

**Flujo**:
1. **Recolectar odds históricas** desde The Odds API snapshots (DB)
2. **Obtener resultados reales** desde API-Football o Football-Data.org
3. **Calcular features TIME-AWARE** (sin data leakage):
   - ELO rating dinámico (K=32)
   - Form reciente con decay exponencial
   - Win rates, H2H, goals stats
   - Market signals (implied probs, margin)
4. **Almacenar en DB** con formato limpio para training

**Integración con sistema actual**:
```python
# ANTES (train_model.py línea 256):
soccer_data = generate_training_data("soccer", num_matches=2000)  # ❌ Sintético

# DESPUÉS:
from src.data.real_data_collector import RealDataCollector
collector = RealDataCollector(db)
soccer_data = collector.collect_historical_training_data(
    sport='soccer',
    leagues=['Premier League', 'La Liga', 'Serie A'],
    date_from='2022-01-01',
    date_to='2024-12-31',
    min_matches=1000
)  # ✅ Real, time-aware
```

**Métricas de Éxito**:
- ✅ Dataset de al menos 1000 partidos con odds reales y resultados
- ✅ Features calculadas sin data leakage (validar con test temporal)
- ✅ ELO ratings convergen con ratings públicos (ej. FiveThirtyEight)

---

### FASE 2: Calibrated Model Training

**Objetivo**: Entrenar modelo con probabilidades calibradas y validación temporal.

**Archivos Nuevos**:
- `src/models/calibrated_model.py` - Modelo con calibración isotónica
- `src/models/model_validator.py` - Validación rigurosa

**Mejoras vs Sistema Actual**:

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **Validación** | `train_test_split` (random) | `TimeSeriesSplit` (temporal) |
| **Probabilidades** | Raw XGBoost | Isotonic Calibration |
| **Métricas** | Accuracy, Log Loss | + Brier Score, ECE, Sharpe |
| **Data** | Sintética | Real histórica |
| **Overfitting** | Posible (data leakage) | Prevenido (walk-forward) |

**Implementación**:
```python
from src.models.calibrated_model import CalibratedBettingModel

model = CalibratedBettingModel(sport='soccer', model_type='xgboost')
metrics = model.train(
    data=soccer_data,
    n_splits=5,  # TimeSeriesSplit
    calibration_method='isotonic'  # Isotonic regression
)

# Métricas críticas:
# - ECE before: 0.12 → after: 0.04 ✅
# - Brier Score: 0.18 (excellent if < 0.20)
# - Log Loss: 0.52
# - CV ROI: 4.2% (walk-forward backtest)
```

**Integración con predictor actual**:
```python
# src/models/predictor.py
class MatchPredictor:
    def __init__(self):
        # Cargar modelo calibrado en lugar de modelo básico
        self.soccer_model = CalibratedBettingModel.load("models/soccer_calibrated.pkl")

    def predict_match(self, match: Dict) -> Dict:
        # Las probabilidades ahora son CALIBRADAS
        probabilities = self.soccer_model.predict_proba(features_df)
        # Edge calculado será más preciso
```

**Métricas de Éxito**:
- ✅ ECE (Expected Calibration Error) < 0.05
- ✅ Brier Score < 0.20
- ✅ Walk-forward backtest ROI > 3%
- ✅ CLV > 2% en validación

---

### FASE 3: Enhanced Feature Engineering

**Objetivo**: Agregar features avanzadas que capturan valor real.

**Features Nuevas**:

1. **ELO Rating Dinámico**
   ```python
   def update_elo(team_elo, opponent_elo, result, k=32):
       expected = 1 / (1 + 10**((opponent_elo - team_elo) / 400))
       actual = 1.0 if result == 'win' else (0.5 if result == 'draw' else 0.0)
       return team_elo + k * (actual - expected)
   ```

2. **Form con Decay Exponencial**
   ```python
   # Últimos 5 partidos, recientes pesan más
   weights = np.exp(np.linspace(-1, 0, 5))  # [0.37, 0.54, 0.74, 1.0]
   form = np.average(results, weights=weights)
   ```

3. **Market Efficiency Signals**
   ```python
   # Detectar "steam moves" (movimiento rápido de odds)
   odds_movement = (current_odds - opening_odds) / opening_odds
   sharp_money = abs(odds_movement) > 0.05  # 5% move = sharp action
   ```

4. **Bookmaker Bias Detection**
   ```python
   # Favorite-longshot bias
   implied_total = implied_home + implied_away + implied_draw
   margin = implied_total - 1.0

   # Bookies sobrevaloran favoritos, infravaloran underdogs
   # Ajustar edge en consecuencia
   ```

5. **League Strength Index**
   ```python
   # ELO promedio de equipos en la liga
   league_strength = {
       'Premier League': 1650,
       'La Liga': 1620,
       'Serie A': 1600,
       'Bundesliga': 1590
   }
   ```

**Integración**:
```python
# src/data/real_data_collector.py
def _engineer_features_from_history(self, df, sport):
    # ...existing features...

    # + Nuevas features avanzadas
    features['home_elo'] = self._calculate_elo_at_date(...)
    features['form_decay_5'] = self._calculate_form(...)
    features['odds_movement'] = self._calculate_odds_movement(...)
    features['league_strength'] = league_strength_map[league]
```

**Métricas de Éxito**:
- ✅ Feature importance: ELO y Form en top 5
- ✅ Incremento en accuracy: +2-3% vs baseline
- ✅ Edge promedio aumenta: +0.5-1%

---

### FASE 4: Drift Detection & Auto-Retraining

**Objetivo**: Detectar degradación del modelo y re-entrenar automáticamente.

**Archivos Nuevos**:
- `src/monitoring/drift_detector.py` - Detector de drift
- `src/automation/auto_retrain.py` - Pipeline de re-entrenamiento

**Tipos de Drift Monitoreados**:

1. **Data Drift** (distribución de features cambia)
   ```python
   # Kolmogorov-Smirnov test
   statistic, p_value = ks_2samp(baseline_samples, production_samples)
   if p_value < 0.05:
       alert("Data drift detected in feature X")
   ```

2. **Concept Drift** (relación features-target cambia)
   ```python
   # Monitoring performance metrics
   if recent_accuracy < baseline_accuracy - 0.05:
       alert("Concept drift detected")
   ```

3. **Performance Drift** (ROI/CLV caen)
   ```python
   # Mann-Kendall trend test
   if downward_trend and recent_roi < -0.05:
       trigger_retraining()
   ```

**Pipeline de Auto-Retraining**:
```python
# src/automation/auto_retrain.py
class AutoRetrainer:
    def check_and_retrain(self):
        detector = DriftDetector(db)

        # 1. Detectar drift
        performance_drift = detector.detect_performance_drift(lookback_days=30)
        data_drift = detector.detect_data_drift(new_data)

        # 2. Decidir si re-entrenar
        should_retrain = (
            performance_drift['drift_detected'] or
            len([f for f in data_drift if f['drift_detected']]) > 3
        )

        if should_retrain:
            # 3. Re-colectar datos
            collector = RealDataCollector(db)
            new_training_data = collector.collect_historical_training_data(...)

            # 4. Re-entrenar modelo
            model = CalibratedBettingModel(sport='soccer')
            model.train(new_training_data)

            # 5. Validar nuevo modelo
            validator = ModelValidator()
            if validator.validate_model(model, test_data):
                # 6. Deploy nuevo modelo
                model.save("models/soccer_calibrated.pkl")
                logger.info("✅ Model retrained and deployed")
            else:
                logger.warning("❌ New model failed validation, keeping old model")
```

**Integración con daily_bot.py**:
```python
# Agregar check diario
retrainer = AutoRetrainer()
if retrainer.check_and_retrain():
    # Recargar modelos
    predictor = MatchPredictor()  # Carga modelos actualizados
```

**Métricas de Éxito**:
- ✅ Drift detectado antes de ROI < -10%
- ✅ Re-entrenamiento automático funcional
- ✅ Performance se recupera después de retrain

---

## 🎯 MÉTRICAS DE VALIDACIÓN Y CRITERIOS DE ÉXITO

### Nivel 1: Model Quality (ML Metrics)

| Métrica | Target | Crítico |
|---------|--------|---------|
| **ECE** (Expected Calibration Error) | < 0.05 | < 0.10 |
| **Brier Score** | < 0.18 | < 0.22 |
| **Log Loss** | < 0.55 | < 0.65 |
| **Accuracy** (test set) | > 55% | > 52% |
| **AUC-ROC** | > 0.65 | > 0.60 |

### Nivel 2: Betting Performance (Business Metrics)

| Métrica | Target | Crítico |
|---------|--------|---------|
| **ROI** (backtest 2 años) | > 5% | > 3% |
| **CLV** (Closing Line Value) | > 2% | > 1% |
| **Win Rate** | > 53% | > 50% |
| **Sharpe Ratio** | > 1.2 | > 0.8 |
| **Max Drawdown** | < 20% | < 30% |
| **Kelly Stake Accuracy** | Edge±2% | Edge±5% |

### Nivel 3: Production Stability (Operational Metrics)

| Métrica | Target | Crítico |
|---------|--------|---------|
| **Data Drift** (KS p-value) | > 0.10 | > 0.05 |
| **Performance Drift** (ROI trend) | Stable | > -10% |
| **API Uptime** | > 99% | > 95% |
| **Prediction Latency** | < 2s | < 5s |
| **DB Query Time** | < 500ms | < 2s |

---

## 🔄 PLAN DE IMPLEMENTACIÓN INCREMENTAL

### Sprint 1 (Semana 1-2): Data Foundation
- [ ] Implementar `RealDataCollector`
- [ ] Conectar a API-Football para resultados históricos
- [ ] Poblar DB con 1000+ partidos históricos
- [ ] Validar features time-aware (sin data leakage)
- **Milestone**: Dataset real de 1000+ matches listo para training

### Sprint 2 (Semana 3-4): Calibrated Model
- [ ] Implementar `CalibratedBettingModel`
- [ ] Agregar TimeSeriesSplit validation
- [ ] Entrenar modelo con datos reales
- [ ] Validar calibración (ECE < 0.05)
- **Milestone**: Modelo calibrado con ROI > 3% en backtest

### Sprint 3 (Semana 5): Enhanced Features
- [ ] Implementar ELO rating system
- [ ] Agregar form con decay exponencial
- [ ] Implementar market efficiency signals
- [ ] Re-entrenar modelo con nuevas features
- **Milestone**: Accuracy mejora +2% vs baseline

### Sprint 4 (Semana 6): Monitoring & Drift Detection
- [ ] Implementar `DriftDetector`
- [ ] Configurar alertas (Telegram/Email)
- [ ] Implementar auto-retraining pipeline
- [ ] Testing en producción simulada
- **Milestone**: Sistema de monitoreo activo

### Sprint 5 (Semana 7-8): Production Deployment
- [ ] Deploy gradual (paper trading 30 días)
- [ ] Monitorear métricas en vivo
- [ ] Ajustar thresholds basado en performance
- [ ] Go-live con bankroll real (pequeño)
- **Milestone**: Sistema en producción con CLV > 2%

---

## 🚀 VENTAJAS COMPETITIVAS ALCANZADAS

Con esta arquitectura, el sistema tendrá:

1. **Valor Real Sostenible**
   - Edge basado en ineficiencias reales del mercado
   - Probabilidades calibradas → Kelly stakes óptimos
   - CLV positivo consistente (sharp bettor)

2. **Adaptabilidad**
   - Drift detection detecta cambios de mercado
   - Auto-retraining mantiene modelo actualizado
   - Performance monitoring previene degradación

3. **Robustez Estadística**
   - Validación temporal elimina data leakage
   - Múltiples métricas de calibración
   - Backtesting riguroso (walk-forward)

4. **Escalabilidad**
   - Pipeline de datos automatizado
   - Re-entrenamiento automático
   - Modular: fácil agregar nuevos deportes/ligas

5. **Transparencia**
   - Métricas claras y medibles
   - Reporting automático (Telegram)
   - Auditable (todas las decisiones en DB)

---

## 📊 ESTIMACIÓN DE IMPACTO

### Situación Actual (con datos sintéticos):
- **ROI esperado**: 0% (aleatorio vs mercado)
- **CLV esperado**: -2% (peor que mercado)
- **Riesgo de ruina**: Alto (probabilidades mal calibradas)

### Situación Proyectada (con arquitectura avanzada):
- **ROI esperado**: 3-7% (basado en estudios de sharp bettors)
- **CLV esperado**: 2-4% (consistentemente mejor que closing line)
- **Sharpe Ratio**: 1.0-1.5 (comparable a fondos cuantitativos)
- **Max Drawdown**: < 25% (controlado con Kelly 1/4)

### Referencias de la Industria:
- Sharp bettors profesionales: ROI 3-5%, CLV 2-3%
- Fondos de apuestas cuantitativos: ROI 5-8%, Sharpe ~1.2
- CLV > 2% sustained = top 5% de bettors

---

## 🛠️ STACK TECNOLÓGICO

**Existente (mantener)**:
- Python 3.9+
- XGBoost / scikit-learn
- SQLite (BettingDatabase)
- Streamlit (UI)
- Loguru (logging)
- The Odds API

**Nuevo (agregar)**:
- `scipy.stats` - KS test, statistical tests
- `scikit-learn.calibration` - CalibratedClassifierCV
- API-Football / Football-Data.org - resultados históricos
- (Opcional) `optuna` - hyperparameter tuning avanzado
- (Opcional) `shap` - model interpretability

---

## 📝 PRÓXIMOS PASOS INMEDIATOS

1. **Validar con el usuario** este plan técnico
2. **Priorizar sprints** según urgencia/impacto
3. **Comenzar Sprint 1**: Implementar `RealDataCollector`
4. **Configurar APIs externas**: API-Football key
5. **Poblar DB histórica**: Al menos 1000 matches

**¿Deseas que comience con la implementación del Sprint 1 (RealDataCollector)?**

---

## 📚 REFERENCIAS

1. Lisandro Kaunitz et al. (2017) - "Beating the bookies with their own numbers"
2. Joseph Buchdahl - "Fixed Odds Sports Betting" (CLV analysis)
3. Haghighat et al. (2019) - "Prediction models for sports betting"
4. Sklearn Calibration Guide - https://scikit-learn.org/stable/modules/calibration.html
5. Sharp betting research - Pinnacle Sports articles

---

**FIN DEL DOCUMENTO TÉCNICO**
