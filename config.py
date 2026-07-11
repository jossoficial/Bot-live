"""
Configuración centralizada del Sports Prediction Bot
Adaptable a cualquier deporte con datos reales en vivo
"""

import os

# ═══════════════════════════════════════════════════════════════
# API KEYS (GitHub Secrets)
# ═══════════════════════════════════════════════════════════════
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PREDICCIÓN
# ═══════════════════════════════════════════════════════════════
MIN_EDGE_PCT = 3.0
KELLY_FRACTION = 0.25
MIN_CONFIDENCE = 0.55
MAX_BET_SIZE_PCT = 5.0
HOME_ADVANTAGE = 0.04  # 4% ventaja local genérica

# ═══════════════════════════════════════════════════════════════
# ENDPOINTS GRATUITOS EN VIVO (sin API key)
# ═══════════════════════════════════════════════════════════════
LIVE_ENDPOINTS = {
    "espn_scoreboard": "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard",
    "espn_teams": "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams",
    "espn_standings": "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/standings",
    "mlb_stats": "https://statsapi.mlb.com/api/v1",
    "nba_today": "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
    "sofascore": "https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{date}",
}

# ═══════════════════════════════════════════════════════════════
# DEPORTES SOPORTADOS
# ═══════════════════════════════════════════════════════════════
SPORTS_CONFIG = {
    "mlb": {
        "name": "MLB Baseball",
        "espn_sport": "baseball",
        "espn_league": "mlb",
        "sofascore_sport": "baseball",
        "scoring_type": "runs",
        "avg_total": 8.5,
    },
    "nba": {
        "name": "NBA Basketball",
        "espn_sport": "basketball",
        "espn_league": "nba",
        "sofascore_sport": "basketball",
        "scoring_type": "points",
        "avg_total": 224.5,
    },
    "nfl": {
        "name": "NFL Football",
        "espn_sport": "football",
        "espn_league": "nfl",
        "sofascore_sport": "american-football",
        "scoring_type": "points",
        "avg_total": 45.5,
    },
    "soccer": {
        "name": "Soccer",
        "espn_sport": "soccer",
        "espn_league": "eng.1",
        "sofascore_sport": "football",
        "scoring_type": "goals",
        "avg_total": 2.5,
    },
    "nhl": {
        "name": "NHL Hockey",
        "espn_sport": "hockey",
        "espn_league": "nhl",
        "sofascore_sport": "ice-hockey",
        "scoring_type": "goals",
        "avg_total": 6.0,
    },
    "mls": {
        "name": "MLS Soccer",
        "espn_sport": "soccer",
        "espn_league": "usa.1",
        "sofascore_sport": "football",
        "scoring_type": "goals",
        "avg_total": 2.8,
    },
    "liga_mx": {
        "name": "Liga MX",
        "espn_sport": "soccer",
        "espn_league": "mex.1",
        "sofascore_sport": "football",
        "scoring_type": "goals",
        "avg_total": 2.4,
    },
}

# ═══════════════════════════════════════════════════════════════
# ARCHIVOS
# ═══════════════════════════════════════════════════════════════
HISTORY_FILE = "data/predictions_history.json"
DAILY_PICKS_FILE = "data/daily_picks.json"
