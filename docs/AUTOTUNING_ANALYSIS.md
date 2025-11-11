# Análisis del Sistema de Autotuning

**Fecha**: 2025-01-10
**Status**: ⚠️ REQUIERE ACTUALIZACIÓN para modelo calibrado

---

## 📋 Resumen Ejecutivo

El sistema de autotuning actual (autotune.py) **funciona correctamente** pero está usando el **modelo antiguo** (`BettingModel` en lugar de `CalibratedBettingModel`). Necesita actualización para aprovechar las probabilidades calibradas del nuevo modelo.

---

## 🔍 Análisis del Código Actual

### Ubicación
- **Archivo principal**: `autotune.py`
- **Integración**: `app.py` (Streamlit UI) y ejecutable desde CLI

### Flujo de Funcionamiento

```
1. Carga matches históricos (canonical_odds + raw_match_results)
   ↓
2. Para cada combinación de parámetros:
   - min_edge: [0.02, 0.03, 0.04, 0.05]
   - min_probability: [0.53, 0.55, 0.57, 0.60]
   - min_odds: [1.50, 1.60, 1.70]
   - max_odds: [2.20, 2.50, 3.00]
   ↓
3. Crea PickSelector temporal con esos parámetros
   ↓
4. Genera predicciones con MatchPredictor
   ↓
5. Selecciona picks basado en parámetros
   ↓
6. Evalúa contra resultados reales en DB
   ↓
7. Calcula métricas: ROI, Win Rate, Volatility, Geo Growth, Score
   ↓
8. Retorna mejores parámetros
```

### Métricas Calculadas

```python
# Fórmula del Score Compuesto
score = 0.6 * roi + 0.3 * geo_growth + 0.1 * win_rate - 0.05 * volatility
score -= max(0, 50 - total_bets) * 0.002  # Penalización por muestra baja
```

**Componentes**:
- **ROI** (60%): Retorno sobre inversión
- **Geo Growth** (30%): Crecimiento geométrico con Kelly 0.25
- **Win Rate** (10%): Porcentaje de aciertos
- **Volatility** (-5%): Penalización por alta desviación estándar

---

## ⚠️ Problemas Identificados

### Problema 1: Usa Modelo Antiguo ❌

**Código actual** (línea 160 en autotune.py):
```python
predictor = MatchPredictor()
```

**¿Qué carga?** (líneas 15-34 en predictor.py):
```python
def __init__(self, soccer_model_path: str = "models/soccer_model.pkl", ...):
    self.soccer_model = BettingModel.load(soccer_model_path)  # ❌ MODELO ANTIGUO
```

**Problema**:
- `BettingModel` es el modelo anterior (sin calibración)
- Las probabilidades **NO están calibradas** (ECE alto)
- El edge calculado será **incorrecto** porque las probabilidades tienen sesgo
- Los umbrales de `min_probability` optimizados serán **incorrectos** para el modelo calibrado

**Impacto**:
- ❌ Autotuning optimiza para probabilidades MAL CALIBRADAS
- ❌ Los parámetros óptimos encontrados no funcionarán bien con el modelo calibrado
- ❌ ROI y métricas serán **incorrectas**

---

### Problema 2: Features Antiguas ❌

**Código actual** (línea 67 en predictor.py):
```python
features_dict = self.db.calculate_match_features(match)
```

**¿Qué features calcula?** (database.py):
- Solo features básicas (~10 features)
- Sin ELO ratings
- Sin form decay
- Sin H2H stats
- Sin goals stats avanzados

**Problema**:
- El autotuning evalúa con **features básicas**
- El modelo calibrado nuevo espera **24 features avanzadas**
- Incompatibilidad entre lo que optimiza el autotuning y lo que usa el modelo real

**Impacto**:
- ❌ Autotuning no puede evaluar el modelo calibrado nuevo
- ❌ Los parámetros optimizados serán **para el modelo viejo**

---

### Problema 3: Umbrales de min_probability Incorrectos ⚠️

**Grid search actual**:
```python
'min_probability': [0.53, 0.55, 0.57, 0.60]  # Para 3-way soccer
```

**Análisis**:
- Soccer 3-way: baseline random = 33.3%
- Home win rate histórico: ~43%
- Umbral de 53% es **muy conservador**

**Con modelo calibrado de accuracy 48%**:
- Probabilidades calibradas estarán más distribuidas (35-60% típico)
- Umbral de 53% filtrará **demasiados picks**
- Puede resultar en N < 20 (muestra insuficiente)

**Recomendación**:
```python
'min_probability': [0.40, 0.45, 0.50, 0.52, 0.55]  # Más realista para 48% accuracy
```

---

## ✅ Lo Que Funciona Correctamente

### 1. Lógica de Evaluación ✅

```python
def evaluate_params(params, matches, predictor, db):
    # Crea PickSelector con parámetros
    # Predice matches
    # Selecciona picks
    # Compara con resultados reales
    # Calcula métricas
```

**Correcto**:
- Walk-forward temporal (matches ordenados por fecha)
- Evalúa contra resultados reales en DB
- Métricas sólidas (ROI, geo growth, volatility)

### 2. Score Compuesto ✅

```python
score = 0.6*roi + 0.3*geo_growth + 0.1*win_rate - 0.05*volatility - penalty
```

**Correcto**:
- Prioriza ROI (60%) - métrica más importante
- Considera crecimiento sostenible (30%) - importante para Kelly
- Win rate como señal auxiliar (10%)
- Penaliza volatilidad alta
- Penaliza muestras pequeñas

### 3. Límites de Tiempo y Combinaciones ✅

```python
max_combinations: int = 24
time_limit_sec: int = 120
```

**Correcto**:
- Evita búsquedas exhaustivas que bloqueen UI
- Permite ejecutar desde Streamlit sin timeout
- Balanceo entre exploración y tiempo

### 4. Integración con UI ✅

El autotuning se puede ejecutar desde `app.py` (Streamlit) y los resultados se pueden aplicar directamente a la DB de parámetros.

---

## 🔧 Solución: Actualizar Autotuning para Modelo Calibrado

### Cambios Necesarios

#### 1. Actualizar MatchPredictor

**Archivo**: `src/models/predictor.py`

**Cambio**:
```python
# ANTES (línea 8)
from src.models.train_model import BettingModel

# DESPUÉS
from src.models.calibrated_model_simple import CalibratedBettingModel
```

**Cambio**:
```python
# ANTES (líneas 15-27)
def __init__(self, soccer_model_path: str = "models/soccer_model.pkl", ...):
    self.soccer_model = BettingModel.load(soccer_model_path)

# DESPUÉS
def __init__(self,
             soccer_model_path: str = "models/soccer_calibrated_advanced.pkl",
             nba_model_path: str = "models/nba_model.pkl"):
    try:
        self.soccer_model = CalibratedBettingModel.load(soccer_model_path)
        logger.info("Soccer calibrated model loaded successfully")
    except FileNotFoundError:
        logger.warning(f"Soccer model not found at {soccer_model_path}")
        self.soccer_model = None
```

**Cambio**:
```python
# ANTES (línea 67)
features_dict = self.db.calculate_match_features(match)

# DESPUÉS
from src.data.feature_integration import calculate_match_features_advanced

features_dict = calculate_match_features_advanced(match, self.db)
```

#### 2. Actualizar Grid de Parámetros en Autotuning

**Archivo**: `autotune.py`

**Cambio**:
```python
# ANTES
PARAM_GRID = {
    'min_edge': [0.02, 0.03, 0.04, 0.05],
    'min_probability': [0.53, 0.55, 0.57, 0.60],  # ❌ Muy alto para 48% accuracy
    'min_odds': [1.50, 1.60, 1.70],
    'max_odds': [2.20, 2.50, 3.00]
}

# DESPUÉS
PARAM_GRID = {
    'min_edge': [0.02, 0.03, 0.04, 0.05],
    'min_probability': [0.40, 0.45, 0.50, 0.52, 0.55],  # ✅ Realista para modelo calibrado
    'min_odds': [1.50, 1.60, 1.70],
    'max_odds': [2.50, 3.00, 3.50]  # ✅ Más permisivo para encontrar value
}
```

**Justificación**:
- Modelo calibrado tiene accuracy 48% → probabilidades típicas 35-60%
- Umbral de 53% es demasiado restrictivo
- Queremos explorar umbrales más bajos que aprovechen la calibración perfecta

#### 3. Agregar Validación de Modelo Calibrado

**Archivo**: `autotune.py` (después de línea 160)

**Agregar**:
```python
predictor = MatchPredictor()

# Validar que está usando modelo calibrado
if hasattr(predictor.soccer_model, 'calibrated_model'):
    print("✅ Usando modelo CALIBRADO para autotuning")
else:
    print("⚠️ WARNING: Usando modelo SIN calibrar - resultados no óptimos")
    print("   Ejecuta: python train_advanced_model.py primero")
```

---

## 📊 Testing del Autotuning Actualizado

### Test Mínimo

```python
# test_autotuning.py

from autotune import autotune_parameters
from src.utils.database import BettingDatabase

db = BettingDatabase()

# Ejecutar autotuning con parámetros conservadores
result = autotune_parameters(
    db=db,
    sample_size=100,  # Solo 100 matches para test rápido
    max_combinations=12,  # 12 combinaciones (2-3 min)
    time_limit_sec=180
)

print("\n=== RESULTADO DEL AUTOTUNING ===")
if result['best_params']:
    print(f"Mejores parámetros: {result['best_params']}")
    print(f"ROI: {result['best_metrics']['roi']:.2%}")
    print(f"Win Rate: {result['best_metrics']['win_rate']:.1%}")
    print(f"N: {result['best_metrics']['n']}")
    print(f"Score: {result['best_metrics']['score']:.3f}")
else:
    print("No se encontraron parámetros válidos")
    print(f"Error: {result.get('error', 'Unknown')}")
```

### Expected Output (con modelo calibrado)

```
🔍 Autotuning con 100 partidos históricos...
✅ Usando modelo CALIBRADO para autotuning
📊 Evaluando 12 combinaciones de parámetros...
  [5/12] Evaluando... mejor score hasta ahora: 0.042
  ✓ Nueva mejor configuración encontrada! Score: 0.058, ROI: 3.2%, N: 28
  [10/12] Evaluando... mejor score hasta ahora: 0.058
⏱️ Autotuning completado en 124.3s

=== RESULTADO DEL AUTOTUNING ===
Mejores parámetros: {'min_edge': 0.03, 'min_probability': 0.45, 'min_odds': 1.60, 'max_odds': 3.00}
ROI: 3.2%
Win Rate: 48.6%
N: 28
Score: 0.058
```

---

## 🎯 Prioridad de Implementación

### Crítico (Hacer AHORA) 🔴

1. **Actualizar MatchPredictor** para usar `CalibratedBettingModel`
   - Sin esto, autotuning usa modelo viejo
   - Tiempo: 10-15 minutos

### Importante (Hacer DESPUÉS) 🟡

2. **Actualizar PARAM_GRID** con umbrales realistas
   - Tiempo: 2 minutos

3. **Agregar validación** de modelo calibrado
   - Tiempo: 5 minutos

### Opcional (Mejoras futuras) 🟢

4. **Expandir grid search** con más parámetros
5. **Implementar Bayesian Optimization** en lugar de grid search
6. **Agregar más métricas** (Sharpe ratio, max drawdown)

---

## ✅ Conclusión

### Estado Actual del Autotuning

**Funcionalidad**: ✅ Correcto (lógica sólida)
**Compatibilidad**: ❌ **Usa modelo viejo sin calibrar**
**Urgencia**: 🔴 **Alta - bloquea uso efectivo del modelo calibrado**

### Acción Requerida

**Antes de usar autotuning**:
1. Actualizar `predictor.py` para cargar modelo calibrado
2. Actualizar imports para usar `CalibratedBettingModel`
3. Actualizar features para usar `calculate_match_features_advanced`
4. Ajustar PARAM_GRID para accuracy 48%

**Después de actualizar**:
- Autotuning encontrará parámetros óptimos para modelo calibrado
- ROI esperado mejorará (probabilidades correctas = mejor edge detection)
- Win rate será consistente con modelo (48%)

### Impacto Esperado Post-Actualización

| Métrica | Antes (modelo viejo) | Después (calibrado) |
|---------|---------------------|---------------------|
| Parámetros óptimos | Incorrectos (prob sin calibrar) | Correctos (prob calibradas) |
| ROI autotuning | 1-2% (suerte) | 3-5% (real edge) |
| Win rate | Inconsistente | 48% (como modelo) |
| Confiabilidad | Baja | Alta ✅ |

---

## 📝 Checklist de Implementación

- [ ] Actualizar `src/models/predictor.py`:
  - [ ] Import de `CalibratedBettingModel`
  - [ ] Cambiar path default a `soccer_calibrated_advanced.pkl`
  - [ ] Usar `calculate_match_features_advanced`
- [ ] Actualizar `autotune.py`:
  - [ ] Ajustar `PARAM_GRID` para min_probability
  - [ ] Agregar validación de modelo calibrado
- [ ] Testing:
  - [ ] Ejecutar `test_autotuning.py`
  - [ ] Validar que usa modelo calibrado
  - [ ] Validar que ROI > 0% con N > 20
- [ ] Documentar resultados en `AUTOTUNING_RESULTS.md`

---

**Próximo Paso Recomendado**: Actualizar `predictor.py` primero, luego ejecutar autotuning de validación.
