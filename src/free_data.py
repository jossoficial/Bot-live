"""
Módulo de datos en vivo usando endpoints GRATUITOS (sin API key)
ESPN, MLB Stats API, NBA CDN, SofaScore
Adaptable a cualquier deporte
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from config import LIVE_ENDPOINTS, SPORTS_CONFIG


class FreeDataProvider:
    """Proveedor de datos deportivos en vivo usando APIs gratuitas"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
        )

    # ═══════════════════════════════════════════════════════════
    # ESPN API (Gratuita, sin key, todos los deportes)
    # ═══════════════════════════════════════════════════════════

    def get_espn_scoreboard(self, sport_key: str, date: str = None) -> List[Dict]:
        """
        Obtiene partidos del día de ESPN (GRATIS, datos reales en vivo)
        sport_key: mlb, nba, nfl, soccer, nhl, mls, liga_mx
        date: YYYYMMDD (opcional, default=hoy)
        """
        config = SPORTS_CONFIG.get(sport_key)
        if not config:
            print(f"[DATA] Deporte '{sport_key}' no soportado")
            return []

        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        url = LIVE_ENDPOINTS["espn_scoreboard"].format(
            sport=config["espn_sport"], league=config["espn_league"]
        )
        params = {"dates": date}

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_espn_events(data, sport_key)
        except Exception as e:
            print(f"[DATA] Error ESPN {sport_key}: {e}")
            return []

    def _parse_espn_events(self, data: dict, sport_key: str) -> List[Dict]:
        """Parsea eventos de ESPN en formato unificado"""
        events = []
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])

            if len(competitors) < 2:
                continue

            home = next(
                (c for c in competitors if c.get("homeAway") == "home"), competitors[0]
            )
            away = next(
                (c for c in competitors if c.get("homeAway") == "away"), competitors[1]
            )

            home_team = home.get("team", {})
            away_team = away.get("team", {})

            # Records (W-L)
            home_record = (
                home.get("records", [{}])[0].get("summary", "0-0")
                if home.get("records")
                else "0-0"
            )
            away_record = (
                away.get("records", [{}])[0].get("summary", "0-0")
                if away.get("records")
                else "0-0"
            )

            # Score actual (si está en vivo o terminó)
            home_score = home.get("score", "0")
            away_score = away.get("score", "0")

            # Status
            status = (
                event.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
            )

            # Odds si están disponibles
            odds_data = competition.get("odds", [{}])
            odds_info = odds_data[0] if odds_data else {}

            parsed = {
                "sport": sport_key,
                "event_id": event.get("id"),
                "date": event.get("date"),
                "status": status,
                "home_team": home_team.get("displayName", "Unknown"),
                "home_abbr": home_team.get("abbreviation", ""),
                "home_record": home_record,
                "home_score": home_score,
                "away_team": away_team.get("displayName", "Unknown"),
                "away_abbr": away_team.get("abbreviation", ""),
                "away_record": away_record,
                "away_score": away_score,
                "venue": competition.get("venue", {}).get("fullName", ""),
                "broadcast": event.get("competitions", [{}])[0].get("broadcasts", [{}]),
            }

            # Agregar odds si existen
            if odds_info:
                parsed["spread"] = odds_info.get("spread", None)
                parsed["over_under"] = odds_info.get("overUnder", None)
                parsed["home_ml"] = odds_info.get("homeTeamOdds", {}).get(
                    "moneyLine", None
                )
                parsed["away_ml"] = odds_info.get("awayTeamOdds", {}).get(
                    "moneyLine", None
                )

            # Extraer W y L del record
            try:
                hw, hl = home_record.split("-")[:2]
                aw, al = away_record.split("-")[:2]
                parsed["home_wins"] = int(hw)
                parsed["home_losses"] = int(hl)
                parsed["away_wins"] = int(aw)
                parsed["away_losses"] = int(al)
                parsed["home_win_pct"] = int(hw) / max(int(hw) + int(hl), 1)
                parsed["away_win_pct"] = int(aw) / max(int(aw) + int(al), 1)
            except (ValueError, IndexError):
                parsed["home_win_pct"] = 0.5
                parsed["away_win_pct"] = 0.5

            events.append(parsed)
        return events

    # ═══════════════════════════════════════════════════════════
    # ESPN STANDINGS (Gratuito)
    # ═══════════════════════════════════════════════════════════

    def get_espn_standings(self, sport_key: str) -> Dict:
        """Obtiene standings/clasificación en vivo"""
        config = SPORTS_CONFIG.get(sport_key)
        if not config:
            return {}

        url = LIVE_ENDPOINTS["espn_standings"].format(
            sport=config["espn_sport"], league=config["espn_league"]
        )
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[DATA] Error standings {sport_key}: {e}")
            return {}

    # ═══════════════════════════════════════════════════════════
    # MLB STATS API (Gratuita, datos oficiales)
    # ═══════════════════════════════════════════════════════════

    def get_mlb_schedule(self, date: str = None) -> List[Dict]:
        """Obtiene schedule MLB con pitchers abridores"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        url = f"{LIVE_ENDPOINTS['mlb_stats']}/schedule"
        params = {
            "sportId": 1,
            "date": date,
            "hydrate": "probablePitcher,team,linescore",
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            games = []
            for date_entry in data.get("dates", []):
                for game in date_entry.get("games", []):
                    away = game.get("teams", {}).get("away", {})
                    home = game.get("teams", {}).get("home", {})
                    games.append(
                        {
                            "game_id": game.get("gamePk"),
                            "status": game.get("status", {}).get("detailedState"),
                            "home_team": home.get("team", {}).get("name"),
                            "away_team": away.get("team", {}).get("name"),
                            "home_record": f"{home.get('leagueRecord', {}).get('wins', 0)}-{home.get('leagueRecord', {}).get('losses', 0)}",
                            "away_record": f"{away.get('leagueRecord', {}).get('wins', 0)}-{away.get('leagueRecord', {}).get('losses', 0)}",
                            "home_pitcher": home.get("probablePitcher", {}).get(
                                "fullName", "TBD"
                            ),
                            "away_pitcher": away.get("probablePitcher", {}).get(
                                "fullName", "TBD"
                            ),
                            "home_pitcher_era": home.get("probablePitcher", {}).get(
                                "era", "0.00"
                            ),
                            "away_pitcher_era": away.get("probablePitcher", {}).get(
                                "era", "0.00"
                            ),
                            "venue": game.get("venue", {}).get("name"),
                        }
                    )
            return games
        except Exception as e:
            print(f"[DATA] Error MLB Stats API: {e}")
            return []

    def get_mlb_team_stats(self, team_id: int, season: int = 2026) -> Dict:
        """Obtiene estadísticas de equipo MLB"""
        url = f"{LIVE_ENDPOINTS['mlb_stats']}/teams/{team_id}/stats"
        params = {"stats": "season", "group": "hitting,pitching", "season": season}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[DATA] Error team stats: {e}")
            return {}

    # ═══════════════════════════════════════════════════════════
    # NBA CDN (Gratuito, datos oficiales en vivo)
    # ═══════════════════════════════════════════════════════════

    def get_nba_today(self) -> List[Dict]:
        """Obtiene scoreboard NBA del día (CDN oficial gratuito)"""
        url = LIVE_ENDPOINTS["nba_today"]
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            games = []
            for game in data.get("scoreboard", {}).get("games", []):
                games.append(
                    {
                        "game_id": game.get("gameId"),
                        "status": game.get("gameStatusText"),
                        "home_team": game.get("homeTeam", {}).get("teamName"),
                        "home_score": game.get("homeTeam", {}).get("score", 0),
                        "home_record": f"{game.get('homeTeam', {}).get('wins', 0)}-{game.get('homeTeam', {}).get('losses', 0)}",
                        "away_team": game.get("awayTeam", {}).get("teamName"),
                        "away_score": game.get("awayTeam", {}).get("score", 0),
                        "away_record": f"{game.get('awayTeam', {}).get('wins', 0)}-{game.get('awayTeam', {}).get('losses', 0)}",
                    }
                )
            return games
        except Exception as e:
            print(f"[DATA] Error NBA CDN: {e}")
            return []

    # ═══════════════════════════════════════════════════════════
    # SOFASCORE API (Gratuita, fútbol mundial)
    # ═══════════════════════════════════════════════════════════

    def get_sofascore_events(
        self, sport: str = "football", date: str = None
    ) -> List[Dict]:
        """Obtiene eventos de SofaScore (fútbol, basketball, etc.)"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        url = LIVE_ENDPOINTS["sofascore"].format(sport=sport, date=date)
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            events = []
            for event in data.get("events", [])[:50]:  # Limitar a 50
                tournament = event.get("tournament", {})
                home = event.get("homeTeam", {})
                away = event.get("awayTeam", {})
                events.append(
                    {
                        "event_id": event.get("id"),
                        "tournament": tournament.get("name"),
                        "country": tournament.get("category", {}).get("name"),
                        "home_team": home.get("name"),
                        "away_team": away.get("name"),
                        "start_time": event.get("startTimestamp"),
                        "status": event.get("status", {}).get("type"),
                        "home_score": event.get("homeScore", {}).get("current"),
                        "away_score": event.get("awayScore", {}).get("current"),
                    }
                )
            return events
        except Exception as e:
            print(f"[DATA] Error SofaScore: {e}")
            return []

    # ═══════════════════════════════════════════════════════════
    # MÉTODO UNIVERSAL: Obtener partidos de cualquier deporte
    # ═══════════════════════════════════════════════════════════

    def get_today_games(self, sport_key: str) -> List[Dict]:
        """
        Método universal para obtener partidos de hoy de cualquier deporte.
        Combina múltiples fuentes para máxima cobertura.
        """
        games = []

        # Fuente 1: ESPN (funciona para todos los deportes)
        espn_games = self.get_espn_scoreboard(sport_key)
        if espn_games:
            games.extend(espn_games)
            print(f"[DATA] ESPN: {len(espn_games)} partidos de {sport_key}")

        # Fuente 2: APIs específicas por deporte
        if sport_key == "mlb":
            mlb_games = self.get_mlb_schedule()
            if mlb_games:
                # Enriquecer con datos de pitchers
                for game in games:
                    for mlb_g in mlb_games:
                        if mlb_g["home_team"] in game.get("home_team", ""):
                            game["home_pitcher"] = mlb_g.get("home_pitcher")
                            game["away_pitcher"] = mlb_g.get("away_pitcher")
                            game["home_pitcher_era"] = mlb_g.get("home_pitcher_era")
                            game["away_pitcher_era"] = mlb_g.get("away_pitcher_era")
                            break

        elif sport_key == "nba":
            nba_games = self.get_nba_today()
            if nba_games and not games:
                for g in nba_games:
                    games.append(
                        {
                            "sport": "nba",
                            "home_team": g["home_team"],
                            "away_team": g["away_team"],
                            "home_record": g["home_record"],
                            "away_record": g["away_record"],
                            "status": g["status"],
                        }
                    )

        elif sport_key in ["soccer", "mls", "liga_mx"]:
            sofa_events = self.get_sofascore_events("football")
            if sofa_events:
                print(f"[DATA] SofaScore: {len(sofa_events)} eventos de fútbol")

        # Filtrar solo partidos programados (no finalizados)
        scheduled = [
            g
            for g in games
            if g.get("status")
            in [
                "STATUS_SCHEDULED",
                "STATUS_IN_PROGRESS",
                "Scheduled",
                "Pre-Game",
                "Warmup",
                None,
                "notstarted",
            ]
        ]

        return scheduled if scheduled else games

    def get_yesterday_results(self, sport_key: str) -> List[Dict]:
        """Obtiene resultados de ayer para verificar predicciones"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        games = self.get_espn_scoreboard(sport_key, date=yesterday)
        # Filtrar solo finalizados
        return [g for g in games if g.get("status") == "STATUS_FINAL"]
