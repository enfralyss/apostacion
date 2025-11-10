# Configuración de Telegram Bot

Para recibir notificaciones automáticas, necesitas configurar un bot de Telegram.

## 📱 Paso 1: Crear tu Bot de Telegram

1. **Abre Telegram** y busca `@BotFather`
2. Envíale el comando: `/newbot`
3. Dale un nombre a tu bot: `TriunfoBet ML Bot`
4. Dale un username: `triunfobet_ml_bot` (debe terminar en `_bot`)
5. **BotFather te dará un TOKEN** como este:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
6. **Guarda este token** - lo necesitarás

## 🆔 Paso 2: Obtener tu Chat ID

**Opción A: Usando un bot helper**
1. Busca `@userinfobot` en Telegram
2. Envíale cualquier mensaje
3. Te responderá con tu **Chat ID** (número como `123456789`)

**Opción B: Manual**
1. Envía un mensaje a tu bot (el que acabas de crear)
2. Abre en tu navegador:
   ```
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   ```
3. Busca `"chat":{"id": NUMERO}` - ese es tu Chat ID

## ⚙️ Paso 3: Configurar en el proyecto

Edita tu archivo `.env` y agrega:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

## ✅ Paso 4: Probar que funciona

Ejecuta este script de prueba:

```python
python -c "from src.utils.notifications import TelegramNotifier; n = TelegramNotifier(); n.send_message('🤖 TriunfoBet Bot activado!')"
```

Deberías recibir un mensaje en Telegram!

## 📨 Tipos de notificaciones que recibirás:

### 1. Picks diarios (8:00 AM)
```
🎯 PICKS DE HOY

💰 Bankroll: VES 3,130.25
💵 Stake: VES 95.00
📊 Cuota Total: 12.38
🎁 Retorno Potencial: VES 1,176.10

Partidos (3):

1. Premier League
   Arsenal vs Chelsea
   ✅ Pick: home_win
   📈 Odds: 1.85 | Prob: 71.2% | Edge: 8.3%
```

### 2. Snapshots de odds (14:00 PM)
```
📊 Odds Snapshot

✅ 23 partidos capturados
🎯 18 odds canónicas generadas
⏭️ 4 partidos omitidos por calidad
```

### 3. Resultados actualizados (cada 6h)
```
🏆 Resultados Actualizados

✅ 15 partidos finalizados registrados
📊 Dataset listo para actualizar
```

### 4. Re-entrenamiento semanal (Domingos 3 AM)
```
🧠 Modelos Re-entrenados

📊 Soccer: 245 partidos reales
🏀 NBA: 138 partidos reales
✅ Entrenamiento exitoso
```

## 🔕 Desactivar notificaciones

Si quieres desactivar Telegram temporalmente:
- Comenta o elimina las líneas de `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`
- El sistema seguirá funcionando, solo no enviará mensajes

## 🆘 Troubleshooting

**"Telegram disabled, message not sent"**
→ Verifica que tu `.env` tenga TOKEN y CHAT_ID correctos

**"Failed to send: 401 Unauthorized"**
→ Token inválido, verifica que lo copiaste completo

**"Failed to send: 400 Bad Request"**
→ Chat ID incorrecto, verifica que sea solo números

**No recibo mensajes**
→ Asegúrate de haber enviado al menos 1 mensaje a tu bot primero
