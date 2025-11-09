# 📚 Ejemplos de Uso - TriunfoBet Bot

## 🎯 Caso de Uso 1: Primera Ejecución

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar el bot (entrena modelos automáticamente la primera vez)
python daily_bot.py
```

**Salida esperada:**
```
============================================================
DAILY ANALYSIS - 2025-11-09 10:00:00
============================================================

📥 Fetching available matches...
Found 10 matches

🤖 Predicting match outcomes...
Generated 10 predictions

💎 Selecting picks with value...
✓ Value found: Real Madrid vs Barcelona (home_win) - Edge: 8.3%
✓ Value found: Lakers vs Celtics (away_win) - Edge: 6.7%
Selected 4 picks with value

🎯 Building optimal parlay...
Best parlay found: 4 picks, odds 12.38, edge 7.2%

💰 Calculating optimal stake...

================================================================================
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

✅ Analysis complete - 4 picks found
💵 Recommended stake: $95.00
🏆 Potential profit: $1,081.10
```

---

## 🎯 Caso de Uso 2: No Hay Picks con Valor

```bash
python daily_bot.py
```

**Salida cuando no hay valor:**
```
============================================================
DAILY ANALYSIS - 2025-11-09 10:00:00
============================================================

📥 Fetching available matches...
Found 8 matches

🤖 Predicting match outcomes...
Generated 8 predictions

💎 Selecting picks with value...
✗ No value: Manchester City vs Arsenal - Edge 2.1% < 5.0%
✗ No value: Nets vs Heat - Probability 62.0% < 65.0%
✗ No value: PSG vs Lyon - Odds 1.45 < 1.50

🚫 NO PICKS TODAY

No se encontraron apuestas con valor suficiente.

⚠️  Analysis complete - No value picks today
```

**Esto es correcto!** Es mejor no apostar que forzar apuestas sin edge.

---

## 🎯 Caso de Uso 3: Testing de Componentes Individuales

### Test Scraper
```bash
python src/scrapers/triunfobet_scraper.py
```

**Salida:**
```
=== Testing TriunfoBet Scraper ===

Mock login successful for user: test_user

Total matches available: 10

=== Sample Matches ===

Premier League: Manchester City vs Liverpool
  Date: 2025-11-09T18:00:00
  Odds: {'home_win': 1.85, 'draw': 3.40, 'away_win': 3.10}

La Liga: Real Madrid vs Barcelona
  Date: 2025-11-09T22:00:00
  Odds: {'home_win': 1.92, 'draw': 3.50, 'away_win': 2.95}
```

### Test Stats Collector
```bash
python src/scrapers/stats_collector.py
```

**Salida:**
```
=== Testing Stats Collector ===

Real Madrid Stats:
  Form last 5: 2.65
  Goals scored avg: 2.18
  Last 5 results: WWDWW

Lakers Stats:
  Form last 5: 3.80
  Points scored avg: 112.4
  Offensive rating: 114.2

H2H Real Madrid vs Barcelona:
  Total matches: 12
  Real Madrid wins: 5
  Barcelona wins: 4
  Draws: 3
```

### Test Modelo ML
```bash
python src/models/train_model.py
```

**Salida:**
```
==================================================
TRAINING SOCCER MODEL
==================================================
Training xgboost model for soccer
Training on 1600 samples...
Training accuracy: 0.7125
Test accuracy: 0.6850

Classification Report (Test Set):
              precision    recall  f1-score   support
   away_win       0.64      0.62      0.63       128
       draw       0.68      0.71      0.69       144
   home_win       0.73      0.72      0.73       128
   accuracy                           0.69       400

Cross-validation accuracy: 0.6840 (+/- 0.0235)

Top 10 Most Important Features:
                        feature  importance
0           stat_differential    0.182
1      home_win_rate_last_10    0.145
2      away_win_rate_last_10    0.128
3          h2h_home_win_rate    0.112
...

==================================================
TRAINING NBA MODEL
==================================================
...
```

---

## 🎯 Caso de Uso 4: Consultar Base de Datos

### Ver Últimas Apuestas
```python
from src.utils.database import BettingDatabase

db = BettingDatabase()

# Últimas 10 apuestas
recent = db.get_recent_bets(10)

for bet in recent:
    print(f"Bet ID: {bet['id']}")
    print(f"Date: {bet['bet_date']}")
    print(f"Odds: {bet['total_odds']:.2f}")
    print(f"Stake: ${bet['stake']:.2f}")
    print(f"Status: {bet['status']}")
    print(f"Result: {bet['result']}")
    print(f"P/L: ${bet['profit_loss']:.2f}")
    print("-" * 50)
```

### Calcular Performance Metrics
```python
from src.utils.database import BettingDatabase

db = BettingDatabase()
metrics = db.calculate_performance_metrics()

print(f"Total Bets: {metrics['total_bets']}")
print(f"Wins: {metrics['wins']}")
print(f"Losses: {metrics['losses']}")
print(f"Win Rate: {metrics['win_rate']:.1f}%")
print(f"ROI: {metrics['roi']:.1f}%")
print(f"Total P/L: ${metrics['total_profit_loss']:.2f}")
```

**Salida:**
```
Total Bets: 25
Wins: 8
Losses: 17
Win Rate: 32.0%
ROI: 8.5%
Total P/L: $425.00
```

---

## 🎯 Caso de Uso 5: Ajustar Configuración

### Hacer el Bot Más Agresivo
Edita `config/config.yaml`:

```yaml
picks:
  min_probability: 0.60  # Reducido de 0.65
  min_edge: 0.03         # Reducido de 0.05
  min_odds: 1.40         # Reducido de 1.50
  max_odds: 2.50         # Aumentado de 2.20

parlay:
  min_picks: 2           # Reducido de 3
  max_picks: 6           # Aumentado de 5
```

### Hacer el Bot Más Conservador
```yaml
picks:
  min_probability: 0.70  # Aumentado de 0.65
  min_edge: 0.08         # Aumentado de 0.05
  min_odds: 1.60         # Aumentado de 1.50
  max_odds: 2.00         # Reducido de 2.20

bankroll:
  max_bet_percentage: 1.0  # Reducido de 2.0
  kelly_fraction: 0.05     # Reducido de 0.10
```

---

## 🎯 Caso de Uso 6: Simular Resultado de Apuesta

```python
from src.utils.database import BettingDatabase

db = BettingDatabase()

# Obtener última apuesta
recent_bets = db.get_recent_bets(1)
bet = recent_bets[0]

# Simular victoria
if bet['status'] == 'pending':
    new_bankroll = bet['bankroll_before'] + bet['potential_return']
    profit = bet['potential_return'] - bet['stake']

    db.update_bet_result(
        bet_id=bet['id'],
        result='won',
        profit_loss=profit,
        bankroll_after=new_bankroll
    )

    print(f"✅ Bet won! Profit: ${profit:.2f}")
    print(f"New bankroll: ${new_bankroll:.2f}")

# Simular derrota
# db.update_bet_result(
#     bet_id=bet['id'],
#     result='lost',
#     profit_loss=-bet['stake'],
#     bankroll_after=bet['bankroll_before'] - bet['stake']
# )
```

---

## 🎯 Caso de Uso 7: Automatización con Cron (Linux/Mac)

### Configurar ejecución diaria a las 10 AM

```bash
# Editar crontab
crontab -e

# Agregar línea:
0 10 * * * cd /home/user/apostacion && /home/user/apostacion/venv/bin/python daily_bot.py >> /home/user/apostacion/logs/cron.log 2>&1
```

### Ver logs del cron
```bash
tail -f logs/cron.log
```

---

## 🎯 Caso de Uso 8: Notificaciones por Telegram

### Configurar Bot de Telegram

1. **Crear bot:**
   - Habla con [@BotFather](https://t.me/botfather)
   - Envía `/newbot`
   - Sigue instrucciones
   - Copia el token

2. **Obtener Chat ID:**
   - Habla con [@userinfobot](https://t.me/userinfobot)
   - Copia tu ID

3. **Configurar en .env:**
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### Test de notificación
```python
from src.utils.notifications import TelegramNotifier

notifier = TelegramNotifier()
notifier.send_message("🤖 Test message from TriunfoBet Bot!")
```

---

## 🎯 Caso de Uso 9: Backtesting Manual

```python
from src.utils.database import BettingDatabase
import pandas as pd

db = BettingDatabase()

# Obtener todas las apuestas completadas
bets = db.get_recent_bets(100)
settled_bets = [b for b in bets if b['status'] == 'settled']

# Análisis
df = pd.DataFrame(settled_bets)

print("=== BACKTESTING RESULTS ===")
print(f"Total Bets: {len(df)}")
print(f"Win Rate: {(df['result'] == 'won').mean() * 100:.1f}%")
print(f"Average Odds: {df['total_odds'].mean():.2f}")
print(f"Total Staked: ${df['stake'].sum():.2f}")
print(f"Total Profit/Loss: ${df['profit_loss'].sum():.2f}")
print(f"ROI: {(df['profit_loss'].sum() / df['stake'].sum() * 100):.1f}%")

# Por número de picks
print("\n=== BY NUMBER OF PICKS ===")
print(df.groupby('num_picks').agg({
    'profit_loss': 'sum',
    'result': lambda x: (x == 'won').mean()
}))
```

---

## 🎯 Caso de Uso 10: Generar Datos de Entrenamiento Personalizados

```python
from src.utils.data_generator import generate_training_data

# Generar más datos para mejor modelo
soccer_data = generate_training_data("soccer", num_matches=5000)
nba_data = generate_training_data("nba", num_matches=5000)

# Guardar
soccer_data.to_csv("data/soccer_training.csv", index=False)
nba_data.to_csv("data/nba_training.csv", index=False)

# Re-entrenar modelos
from src.models.train_model import BettingModel

soccer_model = BettingModel("soccer", "xgboost")
soccer_model.train(soccer_data)
soccer_model.save("models/soccer_model.pkl")

nba_model = BettingModel("nba", "xgboost")
nba_model.train(nba_data)
nba_model.save("models/nba_model.pkl")
```

---

## 💡 Tips y Trucos

### 1. Revisar logs en tiempo real
```bash
# Windows
Get-Content logs\triunfobet_bot.log -Wait -Tail 50

# Linux/Mac
tail -f logs/triunfobet_bot.log
```

### 2. Backup de base de datos
```bash
# Crear backup
copy data\betting_history.db data\betting_history_backup.db

# Restaurar backup
copy data\betting_history_backup.db data\betting_history.db
```

### 3. Limpiar datos viejos
```python
from src.utils.database import BettingDatabase
import sqlite3

conn = sqlite3.connect("data/betting_history.db")
cursor = conn.cursor()

# Eliminar apuestas de hace más de 90 días
cursor.execute("""
    DELETE FROM bets
    WHERE created_at < date('now', '-90 days')
""")
conn.commit()
```

### 4. Exportar datos a Excel
```python
from src.utils.database import BettingDatabase
import pandas as pd

db = BettingDatabase()
bets = db.get_recent_bets(100)

df = pd.DataFrame(bets)
df.to_excel("betting_history.xlsx", index=False)
```

---

## 🚨 Errores Comunes y Soluciones

### Error: ModuleNotFoundError
**Solución:** Activa el entorno virtual
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Error: Permission denied en logs
**Solución:** Cierra otros procesos que usen los logs
```bash
# Crear nuevo directorio de logs
mkdir logs_new
# Actualizar config.yaml con nueva ruta
```

### Error: Model file not found
**Solución:** Entrena los modelos
```bash
python src/models/train_model.py
```

---

Estos ejemplos cubren los casos de uso más comunes. Para más detalles, consulta el README.md completo.
