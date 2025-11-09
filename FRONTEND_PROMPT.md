# Prompt para Frontend del Bot de Apuestas TriunfoBet

## Contexto del Proyecto

Necesito crear un **frontend web moderno y profesional** para mi bot de apuestas deportivas que actualmente funciona en línea de comandos. El bot analiza partidos de fútbol europeo (Champions League, La Liga, Premier League, Serie A, Bundesliga) y NBA usando Machine Learning (XGBoost) para identificar apuestas con valor positivo.

## Arquitectura Actual del Backend

### Tecnologías Backend
- **Python 3.13**
- **Machine Learning**: XGBoost, scikit-learn, pandas, numpy
- **APIs**: The Odds API (500 requests/mes gratis)
- **Database**: SQLite (con SQLAlchemy)
- **Automatización**: Selenium WebDriver
- **Logging**: Loguru

### Estructura del Proyecto
```
apostacion/
├── bot_real.py                 # Script principal del bot
├── config/
│   └── config.yaml             # Configuración (bankroll, Kelly, etc.)
├── src/
│   ├── models/
│   │   ├── train_model.py      # Entrenamiento XGBoost
│   │   └── predictor.py        # Predictor de partidos
│   ├── betting/
│   │   ├── pick_selector.py    # Selección de picks con valor
│   │   ├── parlay_builder.py   # Construcción de parlays
│   │   └── stake_calculator.py # Kelly Criterion
│   ├── scrapers/
│   │   ├── api_odds_fetcher.py # Obtención de odds reales
│   │   └── stats_collector.py  # Estadísticas de equipos
│   ├── automation/
│   │   └── bet_placer.py       # Automatización Selenium
│   └── utils/
│       ├── database.py         # SQLite ORM
│       └── notifications.py    # Telegram bot
├── models/
│   ├── soccer_model.pkl        # Modelo entrenado fútbol
│   └── nba_model.pkl          # Modelo entrenado NBA
└── data/
    └── betting.db              # Base de datos SQLite
```

### Funcionalidad Actual del Bot

1. **Obtención de Datos**: Consulta The Odds API y obtiene ~110 partidos con odds reales
2. **Análisis ML**: Predice resultados con modelos XGBoost (55-58% accuracy)
3. **Selección de Picks**: Identifica apuestas con:
   - Probabilidad > 65%
   - Edge > 5% (ventaja sobre odds)
   - Odds entre 1.50 - 2.20
4. **Construcción de Parlay**: Combina 3-5 picks óptimos
5. **Cálculo de Stake**: Kelly Criterion (10% fraccionario) sobre bankroll
6. **Output**: Recomendaciones manuales para colocar en TriunfoBet.com

### Configuración Actual (config.yaml)
```yaml
bankroll:
  initial: 3130.25  # VES (Bolívares venezolanos)
  max_bet_percentage: 2.0
  kelly_fraction: 0.10
  stop_loss_percentage: 20.0

picks:
  min_probability: 0.65
  min_edge: 0.05
  min_odds: 1.50
  max_odds: 2.20

parlay:
  min_picks: 3
  max_picks: 5
  min_combined_probability: 0.30
  max_combined_odds: 10.0
```

---

## Especificaciones del Frontend Deseado

### Stack Tecnológico Recomendado

**Opción 1: React + FastAPI (RECOMENDADA)**
- **Frontend**: React 18 + TypeScript + Vite
- **UI Framework**: Tailwind CSS + shadcn/ui
- **Charts**: Recharts o Chart.js
- **State Management**: Zustand o React Query
- **Backend API**: FastAPI (Python) para exponer endpoints
- **Deployment**: Vercel (frontend) + Railway/Render (backend)

**Opción 2: Next.js Full-Stack**
- **Framework**: Next.js 14 (App Router) + TypeScript
- **UI**: Tailwind CSS + Radix UI
- **API Routes**: Next.js API routes que llaman a Python via subprocess
- **Charts**: Recharts
- **Deployment**: Vercel

**Opción 3: Streamlit (Rápido para MVP)**
- **Framework**: Streamlit (Python nativo)
- **Pros**: Desarrollo ultra-rápido, integración directa con código Python
- **Contras**: Menos personalización visual, no tan profesional

---

## Características y Pantallas del Frontend

### 1. Dashboard Principal

**Vista General**
- **Métricas clave en cards**:
  - Bankroll actual: VES 3,130.25
  - ROI total: +X%
  - Apuestas ganadas/perdidas: X/Y (Z% win rate)
  - Racha actual: X ganadas/perdidas
  - Profit total: +VES X

- **Gráfico de progreso del bankroll**:
  - Línea temporal mostrando evolución del bankroll
  - Marcadores de apuestas ganadoras (verde) y perdidas (rojo)

- **Picks de hoy**:
  - Card con número de picks encontrados hoy
  - Botón "Ver Recomendaciones"

**Diseño**:
```
┌─────────────────────────────────────────────────────────┐
│  TriunfoBet ML Bot              🔔  ⚙️  👤             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📊 MÉTRICAS CLAVE                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Bankroll │ │   ROI    │ │ Win Rate │ │  Profit  │  │
│  │ 3,130.25 │ │  +12.5%  │ │   58%    │ │  +350    │  │
│  │   VES    │ │          │ │  (23/40) │ │   VES    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                          │
│  📈 EVOLUCIÓN BANKROLL                                   │
│  ┌────────────────────────────────────────────────────┐ │
│  │     [Gráfico de línea con marcadores]              │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  🎯 PICKS DE HOY                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │  5 picks encontrados con valor positivo            │ │
│  │  [VER RECOMENDACIONES →]                           │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

### 2. Página de Recomendaciones Diarias

**Funcionalidad**:
- Botón "EJECUTAR ANÁLISIS" que:
  1. Llama a `bot_real.py` via API
  2. Muestra loading spinner con progreso:
     - "Verificando API..."
     - "Obteniendo 110 partidos..."
     - "Analizando con ML..."
     - "Buscando picks con valor..."
  3. Muestra resultados

**Resultados**:
Si hay picks:
```
┌─────────────────────────────────────────────────────────┐
│  PARLAY RECOMENDADO - 4 PICKS                           │
│  Cuota Total: 3.45x | Probabilidad: 42.3% | Edge: 8.2% │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1️⃣ CHAMPIONS LEAGUE                                    │
│     Real Madrid vs Manchester City                      │
│     ✅ VICTORIA REAL MADRID                             │
│     Cuota: 1.85 | Confianza: 68% | Edge: 9.2%         │
│     [AGREGAR AL CUPÓN]                                  │
│                                                          │
│  2️⃣ PREMIER LEAGUE                                      │
│     Liverpool vs Arsenal                                │
│     ✅ VICTORIA LIVERPOOL                               │
│     Cuota: 1.70 | Confianza: 71% | Edge: 7.1%         │
│     [AGREGAR AL CUPÓN]                                  │
│                                                          │
│  ... (más picks)                                        │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  💰 STAKE RECOMENDADO                                   │
│  VES 62.60 (2.0% del bankroll)                         │
│  Retorno Potencial: VES 216.00                         │
│  Ganancia Potencial: VES 153.40                        │
│                                                          │
│  [📋 COPIAR CUPÓN] [✅ MARCAR COMO APOSTADO]           │
└─────────────────────────────────────────────────────────┘
```

Si NO hay picks:
```
┌─────────────────────────────────────────────────────────┐
│  ❌ NO HAY PICKS CON VALOR HOY                          │
│                                                          │
│  Analizados: 110 partidos                               │
│  Criterios: Prob > 65%, Edge > 5%, Odds 1.50-2.20      │
│                                                          │
│  💡 Mejor no apostar que forzar apuestas sin ventaja    │
└─────────────────────────────────────────────────────────┘
```

---

### 3. Historial de Apuestas

**Tabla con todas las apuestas**:
- Filtros: Fecha, Deporte, Resultado (Ganada/Perdida/Pendiente)
- Columnas:
  - ID | Fecha | Deporte | Tipo | Picks | Cuota | Stake | Resultado | Profit/Loss

**Detalle de apuesta (modal)**:
```
┌─────────────────────────────────────────────────────────┐
│  APUESTA #42 - GANADA ✅                                │
│  Fecha: 2025-11-08 | Tipo: Parlay | Cuota: 3.20x      │
├─────────────────────────────────────────────────────────┤
│  PICKS:                                                 │
│  ✅ Real Madrid vs Barcelona - VICTORIA REAL MADRID    │
│     Cuota: 1.85 | Resultado: 2-1 ✓                    │
│                                                          │
│  ✅ Lakers vs Celtics - VICTORIA LAKERS                │
│     Cuota: 1.75 | Resultado: 112-108 ✓                │
│                                                          │
│  FINANCIERO:                                            │
│  Stake: VES 50.00                                       │
│  Retorno: VES 160.00                                    │
│  Profit: +VES 110.00 (+220%)                           │
│                                                          │
│  BANKROLL:                                              │
│  Antes: VES 3,020.25                                    │
│  Después: VES 3,130.25                                  │
└─────────────────────────────────────────────────────────┘
```

---

### 4. Análisis y Estadísticas

**Métricas avanzadas**:
- **Por deporte**:
  - Win rate Soccer: 62% (18/29)
  - Win rate NBA: 54% (5/11)

- **Por liga**:
  - Champions: 70% (7/10)
  - La Liga: 58% (7/12)
  - Premier: 60% (6/10)
  - etc.

- **Por tamaño de parlay**:
  - 3-picks: 65% win rate
  - 4-picks: 55% win rate
  - 5-picks: 40% win rate

- **Kelly vs Real Stake**:
  - Gráfico comparando stakes recomendados vs apostados

- **Distribution of Edges**:
  - Histograma de edges de picks ganadores vs perdedores

**Gráficos**:
- Evolución de bankroll (línea)
- Win rate por mes (barras)
- ROI por deporte (pie chart)
- Distribución de odds ganadores (histograma)

---

### 5. Configuración

**Editable en UI**:
```yaml
BANKROLL MANAGEMENT
┌─────────────────────────────────────────────────────────┐
│  Bankroll Inicial:     [3130.25] VES                    │
│  Max Bet %:            [2.0] %                          │
│  Kelly Fraction:       [0.10] (Conservador)            │
│  Stop Loss:            [20.0] %                         │
└─────────────────────────────────────────────────────────┘

CRITERIOS DE PICKS
┌─────────────────────────────────────────────────────────┐
│  Probabilidad Mínima:  [65] %                           │
│  Edge Mínimo:          [5.0] %                          │
│  Odds Mínimas:         [1.50]                           │
│  Odds Máximas:         [2.20]                           │
└─────────────────────────────────────────────────────────┘

PARLAY SETTINGS
┌─────────────────────────────────────────────────────────┐
│  Picks Mínimos:        [3]                              │
│  Picks Máximos:        [5]                              │
│  Prob. Combinada Min:  [30] %                           │
│  Cuota Máxima Total:   [10.0]                           │
└─────────────────────────────────────────────────────────┘

API KEYS
┌─────────────────────────────────────────────────────────┐
│  The Odds API:         [cad2c557...] [TEST API]        │
│  Requests Restantes:   476/500                          │
│                                                          │
│  Telegram Bot Token:   [No configurado] [CONFIGURAR]    │
└─────────────────────────────────────────────────────────┘

[GUARDAR CAMBIOS]
```

---

### 6. Explorador de Partidos (Opcional pero Útil)

**Tabla de todos los partidos disponibles**:
```
PARTIDOS DISPONIBLES HOY (110)
┌────────────────────────────────────────────────────────────────────┐
│ Liga            │ Partido              │ 1    │ X    │ 2    │ ML  │
├────────────────────────────────────────────────────────────────────┤
│ Champions       │ Real vs City         │ 1.85 │ 3.50 │ 3.80 │ 68% │
│ Premier League  │ Liverpool vs Arsenal │ 1.70 │ 3.90 │ 4.20 │ 71% │
│ ...             │ ...                  │ ...  │ ...  │ ...  │ ... │
└────────────────────────────────────────────────────────────────────┘

Columnas:
- ML = Predicción ML (probabilidad del resultado más probable)
- Verde = Pick recomendado
- Amarillo = Valor marginal
- Rojo = Sin valor
```

---

## API Endpoints Necesarios (Backend FastAPI)

### 1. Ejecutar Análisis
```python
POST /api/analyze
Body: { "bankroll": 3130.25 }
Response: {
  "success": true,
  "matches_analyzed": 110,
  "picks_found": 5,
  "parlay": {
    "num_picks": 4,
    "total_odds": 3.45,
    "combined_probability": 0.423,
    "edge_percentage": 8.2,
    "picks": [...]
  },
  "stake": 62.60,
  "potential_return": 216.00,
  "potential_profit": 153.40
}
```

### 2. Obtener Historial
```python
GET /api/bets?limit=50&offset=0&sport=all&result=all
Response: {
  "bets": [
    {
      "id": 42,
      "date": "2025-11-08T14:30:00",
      "sport": "mixed",
      "type": "parlay",
      "picks": [...],
      "odds": 3.20,
      "stake": 50.00,
      "result": "won",
      "profit": 110.00
    },
    ...
  ],
  "total": 150
}
```

### 3. Guardar Apuesta
```python
POST /api/bets
Body: {
  "picks": [...],
  "stake": 62.60,
  "total_odds": 3.45,
  "notes": "Apuesta manual"
}
Response: { "bet_id": 43 }
```

### 4. Actualizar Resultado
```python
PUT /api/bets/{bet_id}
Body: { "result": "won" | "lost" | "push" }
Response: { "success": true }
```

### 5. Estadísticas
```python
GET /api/stats
Response: {
  "bankroll": {
    "current": 3130.25,
    "initial": 3000.00,
    "peak": 3200.00,
    "roi": 12.5
  },
  "bets": {
    "total": 40,
    "won": 23,
    "lost": 15,
    "pending": 2,
    "win_rate": 0.58
  },
  "by_sport": {...},
  "by_league": {...},
  "by_parlay_size": {...}
}
```

### 6. Obtener Partidos
```python
GET /api/matches?sport=all
Response: {
  "matches": [
    {
      "id": "abc123",
      "league": "Champions League",
      "home_team": "Real Madrid",
      "away_team": "Manchester City",
      "match_date": "2025-11-10T20:00:00",
      "odds": {
        "home_win": 1.85,
        "draw": 3.50,
        "away_win": 3.80
      },
      "ml_prediction": {
        "predicted_outcome": "home_win",
        "probability": 0.68,
        "edge": 0.092
      }
    },
    ...
  ]
}
```

### 7. Verificar API Status
```python
GET /api/status
Response: {
  "api_status": "ok",
  "requests_remaining": 476,
  "requests_used": 24,
  "models_loaded": true,
  "database_ok": true
}
```

### 8. Configuración
```python
GET /api/config
PUT /api/config
Body: { "bankroll": {...}, "picks": {...}, "parlay": {...} }
```

---

## Diseño Visual y UX

### Paleta de Colores Sugerida
```
Primary: #10b981 (Verde éxito)
Secondary: #3b82f6 (Azul información)
Danger: #ef4444 (Rojo pérdida)
Warning: #f59e0b (Amarillo advertencia)
Background: #0f172a (Slate oscuro)
Surface: #1e293b (Slate medio)
Text: #f1f5f9 (Blanco/gris claro)
```

**Tema**: Oscuro (dark mode by default) con opción de light mode

### Iconos
- 🎯 Picks
- 💰 Bankroll
- 📊 Estadísticas
- ⚙️ Configuración
- 🏆 Ganadas
- ❌ Perdidas
- ⏳ Pendientes
- 🔔 Notificaciones

### Responsive Design
- Desktop: 3 columnas (sidebar + main + stats)
- Tablet: 2 columnas (collapsible sidebar)
- Mobile: 1 columna (bottom nav)

---

## Funcionalidades Adicionales

### 1. Notificaciones Push
- Notificar cuando se encuentren nuevos picks
- Alertas de apuestas próximas a iniciar
- Resultados de apuestas completadas

### 2. Modo Paper Trading
- Toggle para activar/desactivar
- Simular apuestas sin afectar bankroll real
- Comparar rendimiento real vs simulado

### 3. Alertas de Bankroll
- Alerta si bankroll cae X% (stop loss)
- Alerta si racha perdedora > Y apuestas
- Sugerencia de ajustar stakes

### 4. Exportar Data
- Exportar historial a CSV/Excel
- Generar reportes PDF mensuales
- Backup de base de datos

### 5. Comparación de Modelos
- Ver accuracy de cada modelo
- A/B testing entre diferentes configuraciones
- Backtesting con datos históricos

---

## Prioridades de Desarrollo

### MVP (Versión 1.0) - Crítico
1. ✅ Dashboard con métricas básicas
2. ✅ Página de recomendaciones diarias
3. ✅ Historial de apuestas
4. ✅ Configuración básica
5. ✅ API endpoints esenciales

### V2.0 - Importante
6. 📊 Estadísticas avanzadas
7. 📈 Gráficos interactivos
8. 🔔 Notificaciones
9. 📱 Responsive mobile

### V3.0 - Nice to Have
10. 🤖 Modo automatizado (Selenium)
11. 📤 Exportar reportes
12. 🔄 Backtesting UI
13. 🌐 Multi-idioma

---

## Consideraciones de Deployment

### Frontend (Vercel)
```bash
# package.json
{
  "name": "triunfobet-frontend",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  }
}
```

### Backend (Railway/Render)
```python
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
python-dotenv==1.0.0

# Existing dependencies
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
xgboost>=1.7.0
# ... etc
```

### Dockerfile (Backend)
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Prompt Específico para Iniciar

**Prompt sugerido**:

```
Necesito crear un frontend web moderno para mi bot de apuestas deportivas en Python.

CONTEXTO:
- Backend: Python 3.13 con bot_real.py que analiza partidos y recomienda apuestas
- ML: XGBoost para predicciones
- Database: SQLite
- Bankroll actual: VES 3,130.25

STACK DESEADO:
- Frontend: React 18 + TypeScript + Vite
- UI: Tailwind CSS + shadcn/ui
- Backend API: FastAPI para exponer endpoints Python
- Charts: Recharts

PANTALLAS NECESARIAS:
1. Dashboard con métricas (bankroll, ROI, win rate)
2. Recomendaciones diarias (ejecutar bot y mostrar picks)
3. Historial de apuestas
4. Estadísticas y gráficos
5. Configuración

EMPECEMOS POR:
1. Crear estructura de FastAPI (api/main.py) con endpoints básicos
2. Crear proyecto React con Vite
3. Implementar Dashboard básico con cards de métricas
4. Conectar frontend con API

ARCHIVOS BACKEND EXISTENTES:
- bot_real.py (script principal)
- src/utils/database.py (SQLite ORM)
- config/config.yaml (configuración)

Por favor, genera:
1. Estructura de carpetas completa
2. api/main.py con endpoints FastAPI
3. Frontend básico con React + Tailwind
4. Instrucciones de setup y deployment
```

---

## Checklist de Implementación

### Backend API
- [ ] Crear `api/main.py` con FastAPI
- [ ] Endpoint POST /api/analyze (ejecutar bot_real.py)
- [ ] Endpoint GET /api/bets (historial)
- [ ] Endpoint GET /api/stats (métricas)
- [ ] Endpoint GET /api/matches (partidos disponibles)
- [ ] Endpoint PUT /api/config (guardar configuración)
- [ ] CORS configurado para frontend
- [ ] Error handling y logging

### Frontend
- [ ] Setup Vite + React + TypeScript
- [ ] Instalar Tailwind CSS + shadcn/ui
- [ ] Crear layout base (navbar, sidebar)
- [ ] Dashboard page con cards de métricas
- [ ] Recommendations page con botón "Ejecutar"
- [ ] History page con tabla
- [ ] Stats page con gráficos
- [ ] Settings page con forms
- [ ] React Query para API calls
- [ ] Loading states y error handling

### Database
- [ ] Migrar betting.db a PostgreSQL (opcional para producción)
- [ ] Agregar campos necesarios (si faltan)
- [ ] Crear índices para queries rápidos

### Testing
- [ ] Tests unitarios API (pytest)
- [ ] Tests E2E frontend (Playwright)
- [ ] Verificar cálculos de Kelly Criterion
- [ ] Validar odds vs probabilidades

### Deployment
- [ ] Dockerizar backend
- [ ] Deploy backend en Railway/Render
- [ ] Deploy frontend en Vercel
- [ ] Configurar variables de entorno
- [ ] Setup CI/CD (GitHub Actions)

---

## Próximos Pasos Inmediatos

1. **Crear FastAPI wrapper** para bot_real.py
2. **Inicializar proyecto React** con Vite
3. **Implementar dashboard básico** con datos mock
4. **Conectar API** y reemplazar datos mock
5. **Iterar** agregando features progresivamente

¿Listo para empezar? 🚀
