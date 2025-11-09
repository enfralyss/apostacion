# 🚀 Guía Rápida de Inicio

## Instalación en 5 Minutos

### Windows

1. **Ejecuta el script de instalación:**
   ```cmd
   setup.bat
   ```

2. **Configura tus credenciales (opcional):**
   - Edita el archivo `.env`
   - Agrega tus credenciales de TriunfoBet
   - Agrega token de Telegram (opcional)

3. **Ejecuta el bot:**
   ```cmd
   run_bot.bat
   ```

### Linux/Mac

1. **Instalación manual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

2. **Edita configuración:**
   ```bash
   nano .env
   ```

3. **Ejecuta:**
   ```bash
   python daily_bot.py
   ```

## Verificar Instalación

Ejecuta el script de pruebas:

```bash
python test_all.py
```

Deberías ver:

```
✅ ALL TESTS COMPLETED
```

## Primera Ejecución

El bot hará automáticamente:

1. ✅ Entrenar modelos ML (si no existen)
2. ✅ Crear base de datos SQLite
3. ✅ Obtener partidos disponibles (datos mock)
4. ✅ Predecir resultados
5. ✅ Seleccionar picks con valor
6. ✅ Construir parlay óptimo
7. ✅ Calcular stake con Kelly Criterion
8. ✅ Guardar en base de datos
9. ✅ Mostrar recomendación

## Configuración Inicial Recomendada

Edita `config/config.yaml`:

```yaml
# Configura tu bankroll inicial
bankroll:
  initial: 5000.0  # Cambia esto a tu bankroll real

# Mantén paper trading activado al inicio
paper_trading:
  enabled: true
  duration_days: 30
```

## Entender la Salida

```
🎯 RECOMMENDED PARLAY - 4 PICKS
================================================================================

1. La Liga: Real Madrid vs Barcelona
   └─ home_win @ 1.85
      (Confidence: 71.2%, Edge: 8.3%)
```

- **Confidence**: Probabilidad que el modelo da a ese resultado
- **Edge**: Ventaja sobre las odds de la casa (edge > 5% = valor)
- **@ 1.85**: Cuota ofrecida por la casa

```
💰 Total Odds: 12.38x
🎲 Combined Probability: 23.8%
💸 RECOMMENDED STAKE: $95.00
```

- **Total Odds**: Cuota total del parlay (producto de odds individuales)
- **Combined Probability**: Probabilidad de que gane el parlay completo
- **Recommended Stake**: Calculado con Kelly Criterion al 10%

## Comandos Útiles

### Ver estadísticas
```python
python -c "from src.utils.database import BettingDatabase; db = BettingDatabase(); print(db.calculate_performance_metrics())"
```

### Testear componente específico
```bash
python src/betting/pick_selector.py
python src/betting/parlay_builder.py
python src/models/predictor.py
```

### Re-entrenar modelos
```bash
python src/models/train_model.py
```

## Problemas Comunes

### "ModuleNotFoundError: No module named 'src'"

Asegúrate de estar en la raíz del proyecto:
```bash
cd apostacion
python daily_bot.py
```

### "FileNotFoundError: models/soccer_model.pkl"

Los modelos se entrenan automáticamente en la primera ejecución. Si no:
```bash
python src/models/train_model.py
```

### El bot no encuentra picks con valor

Es normal. No todos los días hay apuestas con valor suficiente. El bot mostrará:
```
🚫 NO PICKS TODAY
No se encontraron apuestas con valor suficiente.
```

Esto es **correcto** - es mejor no apostar que forzar apuestas sin edge.

## Próximos Pasos

1. **Ejecuta en paper trading por 30 días**
   - Esto te dará idea del ROI esperado
   - Verifica win rate y drawdown

2. **Revisa logs diarios**
   - Están en `logs/triunfobet_bot.log`
   - Analiza qué tipos de picks funcionan mejor

3. **Ajusta configuración**
   - Si el bot es muy conservador: reduce `min_edge` de 0.05 a 0.03
   - Si pierde mucho: aumenta `min_probability` de 0.65 a 0.70

4. **Automatiza ejecución diaria**
   - Windows: Task Scheduler
   - Linux: cron job

5. **Cuando estés listo para dinero real:**
   - Cambia `paper_trading: enabled: false` en config.yaml
   - Empieza con bankroll pequeño
   - NUNCA excedas el 2% por apuesta

## Soporte

- Lee el README.md completo para más detalles
- Revisa los logs en `logs/` para debugging
- Cada módulo tiene tests propios que puedes ejecutar

## Recordatorios Importantes

- ⚠️ Empieza SIEMPRE con paper trading
- 💰 Nunca apuestes más del 2% de tu bankroll
- 📊 El edge > 5% es esencial
- 🛑 Respeta el stop loss (20% drawdown)
- 📈 ROI realista: 5-15% mensual (si tienes suerte)

---

**¡Buena suerte y apuesta responsablemente!** 🍀
