# 🤖 TriunfoBet Automated Betting Bot

Sistema automatizado de apuestas deportivas que usa Machine Learning para identificar picks con valor y generar combinadas optimizadas para NBA y fútbol.

## ⚠️ DISCLAIMER

Este software es solo para propósitos educativos. Las apuestas deportivas conllevan riesgos financieros. Usa este sistema bajo tu propia responsabilidad. **Empieza siempre con paper trading (simulación) antes de apostar dinero real.**

## 🎯 Características

- ✅ Scraping de odds de TriunfoBet.com (mock data incluido)
- ✅ Modelos de ML (XGBoost) para predicción de resultados
- ✅ Recolección de estadísticas de equipos
- ✅ Cálculo de edge y Expected Value
- ✅ Selección automática de picks con valor
- ✅ Construcción de parlays optimizados
- ✅ Kelly Criterion para cálculo de stakes
- ✅ Gestión de bankroll y risk management
- ✅ Base de datos SQLite para tracking
- ✅ Notificaciones por Telegram
- ✅ Paper trading mode
- ✅ Logging detallado

## 📋 Requisitos

- Python 3.10+
- pip
- (Opcional) Cuenta de Telegram para notificaciones

## 🚀 Instalación

### 1. Clonar/Descargar el Proyecto

```bash
cd apostacion
```

### 2. Crear Entorno Virtual (Recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Copia el archivo de ejemplo y configura tus credenciales:

```bash
cp .env.example .env
```

Edita `.env` con tus datos:

```env
TRIUNFOBET_USER=tu_usuario
TRIUNFOBET_PASS=tu_contraseña
TELEGRAM_BOT_TOKEN=tu_token_de_bot  # Opcional
TELEGRAM_CHAT_ID=tu_chat_id         # Opcional
```

### 5. Entrenar Modelos

La primera vez que ejecutes el bot, automáticamente entrenará los modelos con datos sintéticos. También puedes entrenarlos manualmente:

```bash
python src/models/train_model.py
```

Esto generará:
- `models/soccer_model.pkl` - Modelo para fútbol
- `models/nba_model.pkl` - Modelo para NBA

## 🎮 Uso

### Ejecución Básica

```bash
python daily_bot.py
```

Esto ejecutará el análisis completo:
1. Obtiene partidos disponibles
2. Predice resultados con ML
3. Selecciona picks con valor (edge > 5%)
4. Construye parlay óptimo
5. Calcula stake con Kelly Criterion
6. Muestra recomendación
7. Guarda en base de datos
8. Envía notificación (si está configurado)

### Paper Trading (Recomendado para Empezar)

Por defecto, el bot está en modo **paper trading** (simulación). Esto está configurado en `config/config.yaml`:

```yaml
paper_trading:
  enabled: true
  duration_days: 30
```

**IMPORTANTE:** Ejecuta el bot en paper trading por al menos 30 días antes de apostar dinero real.

### Automatización Diaria

#### Windows (Task Scheduler)

1. Abre Task Scheduler
2. Crea nueva tarea básica
3. Configura trigger: Diario a las 10:00 AM
4. Acción: Ejecutar programa
   - Programa: `C:\ruta\a\venv\Scripts\python.exe`
   - Argumentos: `C:\ruta\a\apostacion\daily_bot.py`
   - Iniciar en: `C:\ruta\a\apostacion`

#### Linux/Mac (cron)

```bash
crontab -e
```

Agrega:

```cron
0 10 * * * cd /ruta/a/apostacion && /ruta/a/venv/bin/python daily_bot.py >> logs/cron.log 2>&1
```

## 📁 Estructura del Proyecto

```
apostacion/
│
├── src/
│   ├── scrapers/
│   │   ├── triunfobet_scraper.py    # Scraper de odds
│   │   └── stats_collector.py       # Recolector de estadísticas
│   │
│   ├── models/
│   │   ├── train_model.py           # Entrenamiento de modelos
│   │   └── predictor.py             # Predictor de partidos
│   │
│   ├── betting/
│   │   ├── pick_selector.py         # Selector de picks
│   │   ├── parlay_builder.py        # Constructor de parlays
│   │   └── stake_calculator.py      # Calculador de stakes
│   │
│   └── utils/
│       ├── database.py              # Gestor de BD
│       ├── logger.py                # Sistema de logs
│       ├── notifications.py         # Notificaciones Telegram
│       └── data_generator.py        # Generador de datos de entrenamiento
│
├── data/                            # Base de datos
│   └── betting_history.db
│
├── models/                          # Modelos entrenados
│   ├── soccer_model.pkl
│   └── nba_model.pkl
│
├── config/
│   └── config.yaml                  # Configuración
│
├── logs/                            # Logs del sistema
│
├── daily_bot.py                     # Script principal
├── requirements.txt
├── .env.example
└── README.md
```

## ⚙️ Configuración

Todos los parámetros se configuran en `config/config.yaml`:

### Bankroll Management

```yaml
bankroll:
  initial: 5000.0              # Bankroll inicial
  max_bet_percentage: 2.0      # Máximo 2% por apuesta
  kelly_fraction: 0.10         # Kelly conservador (10%)
  stop_loss_percentage: 20.0   # Stop si drawdown > 20%
```

### Criterios de Selección de Picks

```yaml
picks:
  min_probability: 0.65        # Mínimo 65% de confianza
  min_edge: 0.05              # Mínimo 5% de edge
  min_odds: 1.50              # Evitar favoritos muy bajos
  max_odds: 2.20              # Evitar outsiders
```

### Configuración de Parlay

```yaml
parlay:
  min_picks: 3                 # Mínimo 3 picks
  max_picks: 5                 # Máximo 5 picks
  min_total_odds: 5.0         # Odds mínimas del parlay
  max_total_odds: 20.0        # Odds máximas del parlay
```

## 🧪 Testing de Componentes

Cada módulo tiene un `if __name__ == "__main__"` para testing individual:

```bash
# Test scraper
python src/scrapers/triunfobet_scraper.py

# Test stats collector
python src/scrapers/stats_collector.py

# Test modelo ML
python src/models/train_model.py

# Test predictor
python src/models/predictor.py

# Test selector de picks
python src/betting/pick_selector.py

# Test parlay builder
python src/betting/parlay_builder.py

# Test stake calculator
python src/betting/stake_calculator.py

# Test database
python src/utils/database.py
```

## 📊 Ejemplo de Salida

```
🤖 DAILY ANALYSIS - 2025-11-09
================================================================================

💎 PICKS WITH VALUE - 4 found

🎯 RECOMMENDED PARLAY - 4 PICKS
================================================================================

1. La Liga: Real Madrid vs Barcelona
   └─ home_win @ 1.85
      (Confidence: 71.2%, Edge: 8.3%)

2. NBA: Lakers vs Celtics
   └─ away_win @ 2.10
      (Confidence: 68.5%, Edge: 6.7%)

3. Bundesliga: Bayern Munich vs Dortmund
   └─ home_win @ 1.75
      (Confidence: 73.1%, Edge: 9.2%)

4. NBA: Warriors vs Suns
   └─ home_win @ 1.95
      (Confidence: 69.8%, Edge: 7.1%)

────────────────────────────────────────────────────────────────────────────────
💰 Total Odds: 12.38x
🎲 Combined Probability: 23.8%
📈 Parlay Edge: 7.2%
💵 Expected Value: $85.40 per $100

💸 RECOMMENDED STAKE: $95.00 (1.9% of bankroll)
🏆 Potential Return: $1,176.10
💎 Potential Profit: $1,081.10
================================================================================
```

## 📈 Monitoreo de Performance

El bot guarda todas las apuestas en SQLite. Puedes ver el historial:

```python
from src.utils.database import BettingDatabase

db = BettingDatabase()

# Ver últimas apuestas
recent = db.get_recent_bets(20)

# Calcular métricas
metrics = db.calculate_performance_metrics()
print(f"Win Rate: {metrics['win_rate']:.1f}%")
print(f"ROI: {metrics['roi']:.1f}%")
```

## 🔔 Configurar Notificaciones de Telegram

1. Crear un bot con [@BotFather](https://t.me/botfather)
2. Obtener el token del bot
3. Obtener tu chat ID: [@userinfobot](https://t.me/userinfobot)
4. Configurar en `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
```

## 🎓 Cómo Entrenar con Datos Reales

### Para Fútbol

1. Regístrate en [Football-Data.org](https://www.football-data.org/)
2. Obtén tu API key
3. Modifica `src/scrapers/stats_collector.py`:

```python
def _fetch_soccer_stats(self, team_name: str) -> Dict:
    import requests
    api_key = os.getenv('FOOTBALL_DATA_API_KEY')
    response = requests.get(
        f"https://api.football-data.org/v4/teams/{team_id}",
        headers={'X-Auth-Token': api_key}
    )
    # Procesar respuesta...
```

### Para NBA

1. Usa [NBA Stats API](https://github.com/swar/nba_api)
2. Instala: `pip install nba_api`
3. Implementa en `stats_collector.py`

## 🚨 Risk Management

El bot incluye múltiples capas de protección:

1. **Kelly Criterion Fraccionado**: Usa solo 10% del Kelly completo
2. **Límite de Apuesta**: Máximo 2% del bankroll por apuesta
3. **Stop Loss**: Se detiene si drawdown > 20%
4. **Bankroll Mínimo**: No apuesta si bankroll < $1000
5. **Alertas**: Notifica después de 3 pérdidas consecutivas
6. **Validación de Edge**: Solo apuesta si edge > 5%

## 🐛 Troubleshooting

### Error: "Model not found"

```bash
python src/models/train_model.py
```

### Error: "No module named 'src'"

Asegúrate de ejecutar desde la raíz del proyecto:

```bash
cd apostacion
python daily_bot.py
```

### Error: "Database locked"

Cierra otras conexiones a la base de datos o reinicia el script.

## 🔄 Roadmap

### Fase 1: Prototipo ✅
- [x] Scraping con datos mock
- [x] Modelo ML básico
- [x] Sistema de selección de picks
- [x] Constructor de parlays
- [x] Gestión de bankroll
- [x] Base de datos
- [x] Notificaciones

### Fase 2: Producción (Próximamente)
- [ ] Scraping real con Selenium
- [ ] Integración con APIs de estadísticas reales
- [ ] Dashboard web con Streamlit
- [ ] Automatización de colocación de apuestas
- [ ] Backtesting con datos históricos
- [ ] Optimización de hiperparámetros
- [ ] Modelo de ensemble (múltiples algoritmos)

## 📝 Licencia

Este proyecto es solo para uso educativo. No me hago responsable por pérdidas financieras.

## 🤝 Contribuciones

Si tienes mejoras, abre un issue o pull request.

## 📧 Contacto

Para preguntas o soporte, abre un issue en el repositorio.

---

**⚠️ RECUERDA: Empieza con paper trading. Las apuestas deportivas son riesgosas. Nunca apuestes más de lo que puedes permitirte perder.**
