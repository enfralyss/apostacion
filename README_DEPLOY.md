# 🤖 TriunfoBet ML Bot - Automated Sports Betting Assistant

Sistema automatizado de análisis ML para apuestas deportivas con pipeline completo de datos reales, entrenamiento automático y notificaciones via Telegram.

## 🎯 Características

### ✅ Pipeline de Datos Reales
- **Captura automática** de odds desde The Odds API
- **Normalización de odds** (remoción de margen de casas de apuestas)
- **Registro automático de resultados**
- **Feature engineering** (rolling stats, win %, rest days)
- **Entrenamiento con datos reales** (con fallback a sintéticos)

### 🤖 Scheduler Automatizado
- **Cron 1**: Captura odds diaria (14:00)
- **Cron 2**: Actualiza resultados cada 6h
- **Cron 3**: Re-entrena modelos semanalmente (Domingos 03:00)
- **Cron 4**: Genera picks diarios (08:00)

### 📱 Notificaciones Telegram
- Picks diarios con odds, probabilidad y edge
- Alertas de snapshots de odds capturados
- Resultados de re-entrenamiento
- Métricas de modelo actualizadas

### 📊 Dashboard Streamlit
- Métricas en tiempo real
- Evolución de bankroll
- Backtesting de estrategias
- Monitoreo de modelos
- Control manual de pipeline de datos

## 🚀 Quick Start

### 1. Clonar e instalar

```bash
git clone https://github.com/TU_USUARIO/triunfobet-ml.git
cd triunfobet-ml
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements_production.txt
```

### 2. Configurar credenciales

Crea archivo `.env`:

```env
ODDS_API_KEY=tu_api_key_de_theoddsapi
TELEGRAM_BOT_TOKEN=tu_bot_token
TELEGRAM_CHAT_ID=tu_chat_id
```

**Obtener API keys:**
- The Odds API: https://the-odds-api.com/ (500 requests/mes gratis)
- Telegram Bot: Ver [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)

### 3. Inicializar

```bash
python init.py
```

Esto crea directorios, inicializa DB y verifica configuración.

### 4. Elegir modo de uso

**Opción A: Scheduler automatizado (Recomendado para deploy)**
```bash
python scheduler.py
```

**Opción B: Dashboard manual (Para desarrollo local)**
```bash
streamlit run app.py
```

**Opción C: Análisis único**
```bash
python bot_real.py
```

## 📂 Estructura del Proyecto

```
apostacion/
├── src/
│   ├── scrapers/          # Fetchers de odds (The Odds API)
│   ├── models/            # Modelos ML (XGBoost/GradientBoosting)
│   ├── betting/           # Selección de picks y parlays
│   ├── backtesting/       # Engine de backtesting
│   └── utils/             # DB, logger, notificaciones
├── data/                  # SQLite DB y datasets
├── models/                # Modelos entrenados (.pkl)
├── config/                # Configuración YAML
├── app.py                 # Dashboard Streamlit
├── scheduler.py           # Scheduler con crons
├── bot_real.py            # Script principal de análisis
└── init.py                # Inicialización
```

## 🎓 Guías Completas

- **[GUIA_DATOS_REALES.md](GUIA_DATOS_REALES.md)** - Cómo funciona el pipeline de datos
- **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)** - Configurar notificaciones
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deploy en Railway/Render/Docker
- **[QUICK_START.md](QUICK_START.md)** - Inicio rápido
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Solución de problemas

## ☁️ Deploy en la Nube

### Railway (Más fácil - 1 click)

```bash
# Push a GitHub
git add .
git commit -m "Ready for deploy"
git push

# En Railway:
# 1. New Project → Deploy from GitHub
# 2. Agregar variables de entorno
# 3. Deploy automático
```

Ver guía completa: [DEPLOYMENT.md](DEPLOYMENT.md)

### Costos estimados
- **Railway/Render**: $0-5/mes (plan gratuito suficiente)
- **The Odds API**: $0/mes (plan gratuito) o $49/mes (10K requests)
- **Telegram**: Gratis
- **Total**: **$0/mes** posible

## 🔔 Workflow Automatizado

Una vez desplegado en la nube:

```
08:00 AM → 📱 "PICKS DE HOY: 3 partidos"
         → Tú abres TriunfoBet y colocas las apuestas

14:00 PM → 📱 "Snapshot: 25 partidos capturados"
         → Sistema guarda odds automáticamente

18:00 PM → 📱 "Resultados: 10 partidos finalizados"
         → Sistema registra automáticamente

Domingo  → 📱 "Modelos re-entrenados: 68% accuracy"
03:00 AM → Entrenamiento semanal automático
```

**Tú solo colocas las apuestas. El bot hace todo lo demás.**

## 🧪 Testing

```bash
# Test completo
pytest

# Test específico
pytest tests/test_predictor.py

# Con coverage
pytest --cov=src
```

## 📊 Métricas de Ejemplo

Con datos sintéticos (inicial):
- **Accuracy**: ~70%
- **Win Rate**: 65-75%
- **ROI**: 10-15%

Con datos reales (después de 2-4 semanas):
- **Accuracy**: 60-68%
- **Win Rate**: 55-65%
- **ROI**: 5-12%

## 🛠️ Tech Stack

- **ML**: scikit-learn, XGBoost, pandas, numpy
- **API**: The Odds API (odds reales)
- **Scheduler**: APScheduler
- **Notificaciones**: Telegram Bot API
- **Dashboard**: Streamlit, Plotly
- **Database**: SQLite
- **Deploy**: Railway/Render, Docker

## 📝 Licencia

MIT License - Uso libre con atribución

## ⚠️ Disclaimer

Este bot es para fines educacionales y de investigación. Las apuestas deportivas conllevan riesgo. Apuesta de manera responsable y solo lo que puedas permitirte perder.

## 🤝 Contribuciones

PRs bienvenidos! Para cambios mayores, abre un issue primero.

## 📧 Soporte

- Issues: GitHub Issues
- Documentación: Ver carpeta `/docs`
- Telegram: (Configurar grupo de soporte si es necesario)

---

**Hecho con ❤️ para apostadores inteligentes**
