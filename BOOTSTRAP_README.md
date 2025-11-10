# 🚀 Bootstrap de Datos Históricos

## ¿Qué es el Bootstrap?

El bootstrap te permite **cargar meses de datos históricos REALES en minutos**, acelerando dramáticamente el aprendizaje del modelo.

En lugar de esperar 1-2 meses capturando datos día a día, puedes:
- ✅ Cargar 3-12 meses de datos históricos con odds reales
- ✅ Entrenar el modelo inmediatamente
- ✅ Empezar a hacer predicciones desde el día 1

## 📊 Fuentes de Datos

### 1. **Football-Data.co.uk** (RECOMENDADO - GRATIS)
- ✅ **GRATIS** - Sin límites de requests
- ✅ **Odds REALES** de bookmakers (Bet365, Pinnacle, etc.)
- ✅ **Datos históricos** desde 2000
- ✅ **5 ligas europeas** principales
- ❌ Solo fútbol (no NBA)

### 2. **The Odds API** (Limitado)
- ✅ Resultados de últimos 3 días gratis
- ❌ Datos históricos más antiguos requieren plan premium
- ✅ Incluye NBA y fútbol

### 3. **Odds Sintéticas** (Fallback)
- ❌ Generadas artificialmente basadas en resultados
- ❌ Menos precisas que odds reales
- ✅ Útil como fallback si fallan otras fuentes

## 🎯 Uso Rápido

### Opción 1: Bootstrap de 3 meses con datos REALES (Recomendado)

```bash
python bootstrap_historical_data.py
```

Esto hará:
1. Descarga ~500-1000 partidos de fútbol de los últimos 3 meses
2. Con odds REALES de Bet365, Pinnacle, etc.
3. Guarda en la base de datos
4. Re-entrena los modelos automáticamente
5. Envía notificación vía Telegram cuando termine

**Tiempo estimado**: 3-5 minutos

### Opción 2: Bootstrap de 6 meses

```bash
python bootstrap_historical_data.py --months 6
```

Más datos = modelo más robusto, pero toma más tiempo.

### Opción 3: Bootstrap de 12 meses (máximo)

```bash
python bootstrap_historical_data.py --months 12
```

**Advertencia**: Puede tomar 10-15 minutos y generar dataset muy grande.

### Opción 4: Usar odds sintéticas (si falla Football-Data)

```bash
python bootstrap_historical_data.py --months 3 --synthetic
```

## 📈 ¿Cuántos Datos Necesitas?

| Objetivo | Meses Recomendados | Partidos Aprox. | Tiempo |
|----------|-------------------|-----------------|--------|
| **Testing inicial** | 1 mes | 150-200 | 1 min |
| **Entrenamiento básico** | 3 meses | 500-600 | 3 min |
| **Modelo robusto** | 6 meses | 1000-1200 | 5 min |
| **Máxima precisión** | 12 meses | 2000-2500 | 10 min |

## 🔍 ¿Qué Datos Obtienes?

Cada partido incluye:
- ✅ Fecha y hora del partido
- ✅ Equipos (local y visitante)
- ✅ Liga (Premier League, La Liga, Serie A, Bundesliga, Ligue 1)
- ✅ **Odds reales** de apertura (Home/Draw/Away)
- ✅ Resultado final (goles de cada equipo)
- ✅ Resultado categorizado (home_win, away_win, draw)

Ejemplo de datos:
```python
{
  'match_id': 'fd_Premier League_Arsenal_Chelsea_20240115',
  'sport': 'soccer',
  'league': 'Premier League',
  'home_team': 'Arsenal',
  'away_team': 'Chelsea',
  'match_date': '2024-01-15T15:00:00',
  'home_score': 2,
  'away_score': 1,
  'result_label': 'home_win',
  'odds': {
    'home_win': 1.85,  # Odds reales de Bet365
    'draw': 3.40,
    'away_win': 4.20
  },
  'completed': True
}
```

## 🎓 Impacto en el Aprendizaje

### Sin Bootstrap:
- Día 1-30: Capturando datos (0 predicciones confiables)
- Día 31: Primer entrenamiento con ~100 partidos
- Día 60: Modelo empieza a ser útil (~200 partidos)
- Día 90: Modelo decente (~300 partidos)

### Con Bootstrap (3 meses):
- **Día 1**: ✅ Bootstrap carga 600 partidos históricos
- **Día 1**: ✅ Modelo entrenado y listo para usar
- **Día 2**: ✅ Empiezas a hacer predicciones confiables
- **Día 30**: ✅ Modelo excelente (600 históricos + 100 nuevos = 700 partidos)

**Ahorro de tiempo: 2-3 meses**

## 📋 Proceso Completo del Bootstrap

El script ejecuta automáticamente:

1. **Descarga datos históricos**
   - Conecta a Football-Data.co.uk
   - Descarga CSVs de las últimas temporadas
   - Parsea ~500-1000 partidos

2. **Guarda en base de datos**
   - Inserta odds en tabla `odds_snapshots`
   - Guarda resultados en tabla `match_results`
   - Construye odds canónicas

3. **Build training dataset**
   - Calcula features (win_rate, avg_odds, etc.)
   - Separa por deporte (soccer/NBA)
   - Guarda CSVs en `data/training_real_soccer.csv`

4. **Re-entrena modelos**
   - Ejecuta `train_model.py` automáticamente
   - Genera nuevos modelos XGBoost
   - Guarda en `models/soccer_model.pkl`

5. **Notifica vía Telegram**
   - Envía resumen de datos cargados
   - Confirma entrenamiento exitoso

## ⚠️ Consideraciones

### Ventajas del Bootstrap:
- ✅ **Acelera aprendizaje** de 2-3 meses a 1 día
- ✅ **Datos REALES** de bookmakers reales
- ✅ **GRATIS** (Football-Data.co.uk)
- ✅ **Automatizado** - corre solo

### Limitaciones:
- ❌ **Solo fútbol europeo** (no NBA) en datos reales
- ❌ Datos históricos = partidos ya ocurridos (no puedes apostar)
- ✅ Pero sirven para **entrenar** el modelo

### ¿Cuándo Ejecutar Bootstrap?

**Ejecuta SOLO UNA VEZ al inicio:**
- Primera vez que configuras el sistema
- Cuando quieras resetear la base de datos
- Si quieres agregar más datos históricos

**NO ejecutes cada día** - el scheduler ya captura datos automáticamente.

## 🔄 Después del Bootstrap

Una vez ejecutado el bootstrap:

1. ✅ Tu base de datos tiene 600-2000 partidos históricos
2. ✅ Tus modelos están entrenados con datos reales
3. ✅ Puedes empezar a hacer predicciones inmediatamente
4. ✅ El scheduler seguirá capturando nuevos partidos diariamente
5. ✅ El modelo se re-entrenará semanalmente con datos nuevos

## 📊 Verificar que Funcionó

Después del bootstrap, verifica:

```bash
# 1. Verificar partidos en DB
python -c "from src.utils.database import BettingDatabase; db = BettingDatabase(); print(f'Total matches: {db.conn.execute(\"SELECT COUNT(*) FROM match_results\").fetchone()[0]}')"

# 2. Verificar modelos entrenados
ls -la models/

# 3. Ver dashboard
streamlit run app.py
```

En el dashboard deberías ver:
- ✅ Datos reales en tab "Datos Reales"
- ✅ Modelos entrenados en tab "Modelos"
- ✅ Métricas de accuracy > 50%

## 🚀 Ejemplo Completo

```bash
# 1. Ejecutar bootstrap (primera vez)
python bootstrap_historical_data.py --months 6

# Salida esperada:
# ======================================================================
# HISTORICAL DATA BOOTSTRAP
# ======================================================================
# Fetching REAL historical data from Football-Data.co.uk...
# Fetched 200 matches from Premier League 2023/24
# Fetched 180 matches from La Liga 2023/24
# ...
# Total matches to process: 1050
# Saving to database...
# Saved 1050 matches, built 1050 canonical odds
# Saved 1050 match results
# Building features and training dataset...
# Saved soccer training data: 1050 rows
# Re-training models with historical data...
# Models trained successfully!
# ======================================================================
# BOOTSTRAP COMPLETED
# ======================================================================

# 2. Iniciar scheduler para capturas diarias
python scheduler.py

# 3. Ver dashboard
streamlit run app.py
```

## 💡 Tips Pro

1. **Ejecuta bootstrap de 6 meses** para balance perfecto entre datos/tiempo
2. **Verifica Telegram** - recibirás notificación cuando termine
3. **Usa datos reales** siempre que sea posible (no --synthetic)
4. **Ejecuta UNA VEZ** - luego deja que el scheduler capture datos nuevos
5. **Espera 5 minutos** - el proceso toma tiempo, no lo interrumpas

## ❓ Troubleshooting

**Error: "No historical data found"**
- Verifica tu conexión a internet
- Football-Data.co.uk puede estar caído temporalmente
- Intenta con `--synthetic` como fallback

**Error: "Insufficient data for training"**
- Aumenta `--months` a 6 o 12
- Verifica que se guardaron partidos en la DB

**Modelos no mejoran accuracy**
- Datos históricos son buenos para entrenar
- Pero necesitas datos RECIENTES para predicciones actuales
- Ejecuta scheduler por 1-2 semanas para capturar tendencias actuales

## 📚 Lectura Adicional

- [Football-Data.co.uk Documentation](http://www.football-data.co.uk/data.php)
- [The Odds API Docs](https://the-odds-api.com/liveapi/guides/v4/)
- XGBoost Training Guide (ver `docs/training.md`)
