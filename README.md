# 🤖 Sports Prediction Bot

Sistema automatizado de predicción deportiva multi-deporte con datos reales en vivo, desplegable en GitHub Actions.

## Deportes Soportados

| Deporte | Fuente de Datos | Status |
|---------|----------------|--------|
| MLB | ESPN + MLB Stats API + ScraperAPI | ✅ |
| NBA | ESPN + NBA CDN + ScraperAPI | ✅ |
| NFL | ESPN + ScraperAPI | ✅ |
| NHL | ESPN + ScraperAPI | ✅ |
| Soccer (Premier League) | ESPN + SofaScore + ScraperAPI | ✅ |
| MLS | ESPN + SofaScore | ✅ |
| Liga MX | ESPN + SofaScore | ✅ |

## Arquitectura

```
Datos en Vivo (ESPN/MLB API/NBA CDN/SofaScore)
        ↓
ScraperAPI (odds reales de Flashscore/OddsPortal)
        ↓
Motor de Predicción (Poisson + EV + Kelly)
        ↓
Filtro de Confianza (Edge > 3%, Kelly > 0)
        ↓
Deduplicación (no repetir picks del mismo día)
        ↓
Telegram (envío formateado)
        ↓
Historial (JSON auto-commit en GitHub)
```

## Setup Rápido

### 1. Fork/Clone este repositorio

```bash
git clone https://github.com/TU_USUARIO/sports-prediction-bot.git
cd sports-prediction-bot
```

### 2. Configurar GitHub Secrets

Ve a Settings → Secrets and variables → Actions → New repository secret:

| Secret | Descripción |
|--------|-------------|
| `SCRAPER_API_KEY` | Tu API key de [ScraperAPI](https://www.scraperapi.com/) |
| `TELEGRAM_BOT_TOKEN` | Token de tu bot de Telegram (via @BotFather) |
| `TELEGRAM_CHAT_ID` | ID del chat/canal donde enviar picks |

### 3. Activar GitHub Actions

Ve a la pestaña Actions y habilita los workflows.

### 4. (Opcional) Ejecutar manualmente

```bash
pip install -r requirements.txt
python main.py              # Todos los deportes
python main.py mlb nba      # Solo MLB y NBA
python main.py --results    # Verificar resultados de ayer
```

## Horarios de Ejecución (Automático)

| Hora (CST) | Acción |
|------------|--------|
| 8:00 AM | Verificar resultados de ayer + Picks matutinos |
| 12:00 PM | Picks del mediodía (nuevos partidos) |
| 4:00 PM | Picks de la tarde (últimos partidos) |

## Modelo de Predicción

- **Poisson Distribution**: Estima scoring esperado por equipo
- **Expected Value (+EV)**: Solo recomienda cuando hay edge real vs mercado
- **Kelly Criterion (0.25)**: Sizing conservador de apuestas
- **Filtro de confianza**: HIGH (>65% prob + >8% EV), MEDIUM (>55% + >5% EV)

## Fuentes de Datos (100% Gratuitas)

1. **ESPN API** — Scoreboard, standings, odds (sin API key)
2. **MLB Stats API** — Pitchers, records, stats oficiales (sin API key)
3. **NBA CDN** — Scoreboard en vivo oficial (sin API key)
4. **SofaScore API** — Fútbol mundial, eventos en vivo (sin API key)
5. **ScraperAPI** — Odds de Flashscore/OddsPortal (requiere key, plan gratuito disponible)

## Estructura de Archivos

```
sports-prediction-bot/
├── .github/workflows/
│   └── daily_predictions.yml    # Cron jobs automáticos
├── src/
│   ├── __init__.py
│   ├── scraper.py               # ScraperAPI para odds en vivo
│   ├── free_data.py             # Endpoints gratuitos (ESPN, MLB, NBA, SofaScore)
│   ├── predictor.py             # Modelo Poisson + EV + Kelly
│   ├── telegram_bot.py          # Envío de picks a Telegram
│   └── history.py               # Historial y aprendizaje
├── data/
│   ├── predictions_history.json # Historial acumulado
│   └── daily_picks.json         # Picks del día actual
├── config.py                    # Configuración centralizada
├── main.py                      # Orquestador principal
├── requirements.txt
└── README.md
```
