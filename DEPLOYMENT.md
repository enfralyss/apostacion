# Deployment Guide - Railway/Render

Este proyecto está listo para deployment en la nube. Aquí están las instrucciones completas.

---

## 🚀 Opción 1: Railway (Recomendado)

Railway es la opción más simple y tiene plan gratuito generoso.

### Paso 1: Preparar GitHub

```bash
# En tu carpeta del proyecto:
git init
git add .
git commit -m "Ready for deployment"

# Crear repo en GitHub y subir
git remote add origin https://github.com/TU_USUARIO/triunfobet-ml.git
git branch -M main
git push -u origin main
```

### Paso 2: Deploy en Railway

1. **Ir a** https://railway.app/
2. **Sign up** con GitHub
3. Click **"New Project"**
4. Seleccionar **"Deploy from GitHub repo"**
5. Elegir tu repositorio `triunfobet-ml`
6. Railway detectará automáticamente `railway.toml`

### Paso 3: Configurar Variables de Entorno

En Railway, ve a **Variables** y agrega:

```
ODDS_API_KEY=cad2c557594958b0115e472a4ff220f4
TELEGRAM_BOT_TOKEN=8348301159:AAGQDeis0iM4bl8EtrtBhnk_FFUypGZestI
TELEGRAM_CHAT_ID=274578704
```

### Paso 4: Deploy!

1. Railway automáticamente desplegará
2. En ~2-3 minutos estará corriendo
3. Los crons empezarán a ejecutarse automáticamente

### Monitoreo

- **Logs**: Railway Dashboard → Deployments → View Logs
- **Reinicios**: Railway auto-reinicia si el proceso falla
- **Telegram**: Recibirás notificaciones de cada cron

---

## 🎨 Opción 2: Render

Render también tiene plan gratuito.

### Paso 1: Subir a GitHub (igual que arriba)

### Paso 2: Deploy en Render

1. **Ir a** https://render.com/
2. **Sign up** con GitHub
3. Click **"New +"** → **"Background Worker"**
4. Conectar tu repo de GitHub
5. Configurar:
   - **Name**: `triunfobet-scheduler`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements_production.txt`
   - **Start Command**: `python scheduler.py`

### Paso 3: Variables de Entorno

En **Environment** → **Add Environment Variables**:

```
ODDS_API_KEY=cad2c557594958b0115e472a4ff220f4
TELEGRAM_BOT_TOKEN=8348301159:AAGQDeis0iM4bl8EtrtBhnk_FFUypGZestI
TELEGRAM_CHAT_ID=274578704
```

### Paso 4: Deploy!

Click **"Create Background Worker"**

---

## 🐳 Opción 3: Cualquier plataforma con Docker

Si prefieres DigitalOcean, AWS, Google Cloud, etc:

```bash
# Build image
docker build -t triunfobet-ml .

# Run container
docker run -d \
  --name triunfobet \
  --restart unless-stopped \
  -e ODDS_API_KEY=tu_api_key \
  -e TELEGRAM_BOT_TOKEN=tu_token \
  -e TELEGRAM_CHAT_ID=tu_chat_id \
  -v $(pwd)/data:/app/data \
  triunfobet-ml
```

---

## ✅ Verificar que funciona

Después del deployment:

### 1. Revisa los logs

Deberías ver:
```
🤖 Betting Scheduler initialized
✅ Scheduled: Capture odds daily at 14:00
✅ Scheduled: Update results every 6 hours
✅ Scheduled: Rebuild dataset & retrain models every Sunday at 03:00
✅ Scheduled: Generate picks daily at 08:00
🚀 Running initial odds capture...
📊 [CRON] Starting odds capture...
```

### 2. Verifica Telegram

Deberías recibir un mensaje:
```
📊 Odds Snapshot

✅ X partidos capturados
🎯 Y odds canónicas generadas
```

### 3. Espera a los crons programados

- **08:00 AM** → Recibirás picks del día
- **14:00 PM** → Snapshot de odds
- **Cada 6h** → Actualización de resultados
- **Domingos 03:00** → Re-entrenamiento

---

## 💰 Costos

### Railway (Hobby Plan)
- **Gratis**: $5 de crédito/mes
- Suficiente para este bot (usa ~$2-3/mes)
- Si necesitas más: $5/mes por $5 extra de crédito

### Render (Free Tier)
- **Gratis**: 750 horas/mes de background worker
- Suficiente (este bot usa ~720h/mes)
- Limitación: se duerme si no hay actividad (no aplica a workers)

### The Odds API
- **Gratis**: 500 requests/mes
- Con los crons configurados: ~120 requests/mes
- Plan pago: $49/mes = 10,000 requests

### **Total mínimo: $0/mes** (todo en planes gratuitos)

---

## 🔧 Troubleshooting

### "Build failed"
→ Verifica que `requirements_production.txt` esté en el repo
→ Revisa logs de build en Railway/Render

### "No recibo notificaciones"
→ Verifica variables de entorno en la plataforma
→ Revisa logs: `[TELEGRAM] Message sent successfully`

### "API not available"
→ Verifica que `ODDS_API_KEY` esté configurada
→ Revisa cuota de requests en https://the-odds-api.com/account/

### "Crons no se ejecutan"
→ Verifica que `scheduler.py` está corriendo (revisa logs)
→ Railway/Render deben mostrar "Running" status

---

## 📱 Comandos útiles post-deploy

### Ver logs en tiempo real
**Railway**: Dashboard → Logs
**Render**: Dashboard → Logs tab

### Reiniciar manualmente
**Railway**: Settings → Restart
**Render**: Manual Deploy → Deploy latest commit

### Actualizar código
```bash
git add .
git commit -m "Update"
git push
# Railway/Render auto-despliegan en ~2 minutos
```

---

## 🎯 Workflow completo desplegado

```
Sábado 14:00 → Cron captura odds de partidos del fin de semana
              → 📱 "23 partidos capturados"

Domingo 08:00 → Cron genera picks
              → 📱 "PICKS DE HOY: 3 partidos con edge >5%"

Tú           → Abres TriunfoBet y colocas las apuestas manualmente

Domingo 18:00 → Cron actualiza resultados (cada 6h)
Domingo 22:00 → Otro check de resultados
Lunes 00:00   → Otro check

Lunes 03:00   → Cron re-entrena modelo semanal
              → 📱 "Modelos re-entrenados: 45 partidos reales"

Lunes 08:00   → Picks para partidos del lunes
              → 📱 "PICKS DE HOY: ..."
```

**¡Todo automático! Solo colocas las apuestas cuando te llegue la notificación.**

---

## 🚨 Importante: .gitignore

Asegúrate de que `.env` NO se suba a GitHub:

Crea `.gitignore`:
```
.env
venv/
__pycache__/
*.pyc
.pytest_cache/
data/*.db
logs/
models/*.pkl
.DS_Store
```

Las credenciales se configuran directamente en Railway/Render, no en el repo.

---

¿Listo para deploy? 🚀
