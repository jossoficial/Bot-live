"""
Scraper de datos en vivo usando ScraperAPI
Obtiene odds reales de múltiples fuentes web
"""

import json
import re
import time
from typing import Dict, List, Optional

import requests

from config import SCRAPER_API_KEY


class LiveScraper:
    """Scraper de odds y datos deportivos en vivo via ScraperAPI"""

    BASE_URL = "http://api.scraperapi.com"

    def __init__(self):
        self.api_key = SCRAPER_API_KEY
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def _fetch(self, url: str, render_js: bool = False) -> Optional[str]:
        """Fetch URL via ScraperAPI proxy"""
        if not self.api_key:
            print("[SCRAPER] No SCRAPER_API_KEY configurada, saltando scraping")
            return None
        params = {
            "api_key": self.api_key,
            "url": url,
            "render": "true" if render_js else "false",
        }
        try:
            resp = self.session.get(self.BASE_URL, params=params, timeout=60)
            if resp.status_code == 200:
                return resp.text
            print(f"[SCRAPER] Error {resp.status_code} para {url}")
            return None
        except Exception as e:
            print(f"[SCRAPER] Exception: {e}")
            return None

    def get_odds_flashscore(self, sport: str = "soccer") -> List[Dict]:
        """Scrape odds en vivo de Flashscore"""
        sport_map = {
            "soccer": "football",
            "mlb": "baseball",
            "nba": "basketball",
            "nhl": "hockey",
            "nfl": "american-football",
        }
        fs_sport = sport_map.get(sport, sport)
        url = f"https://www.flashscore.com/{fs_sport}/"
        html = self._fetch(url, render_js=True)
        if not html:
            return []
        matches = self._parse_flashscore(html)
        return matches

    def get_odds_oddsportal(
        self, sport: str = "soccer", league: str = ""
    ) -> List[Dict]:
        """Scrape odds de OddsPortal"""
        sport_map = {
            "soccer": "soccer",
            "mlb": "baseball",
            "nba": "basketball",
            "nhl": "hockey",
            "nfl": "american-football",
        }
        op_sport = sport_map.get(sport, sport)
        url = f"https://www.oddsportal.com/{op_sport}/{league}/"
        html = self._fetch(url, render_js=True)
        if not html:
            return []
        odds = self._parse_oddsportal(html)
        return odds

    def get_live_scores(self, sport: str = "soccer") -> List[Dict]:
        """Obtiene scores en vivo via scraping"""
        url = f"https://www.flashscore.com/{sport}/"
        html = self._fetch(url)
        if not html:
            return []
        return self._parse_live_scores(html)

    def _parse_flashscore(self, html: str) -> List[Dict]:
        """Parsea HTML de Flashscore para extraer partidos y odds"""
        matches = []
        # Regex para extraer datos de partidos
        pattern = r'class="event__participant[^"]*"[^>]*>([^<]+)'
        teams = re.findall(pattern, html)
        odds_pattern = r'class="odds__val[^"]*"[^>]*>([^<]+)'
        odds_vals = re.findall(odds_pattern, html)

        for i in range(0, len(teams) - 1, 2):
            match = {
                "home": teams[i].strip() if i < len(teams) else "Unknown",
                "away": teams[i + 1].strip() if i + 1 < len(teams) else "Unknown",
                "source": "flashscore",
            }
            odds_idx = (i // 2) * 3
            if odds_idx + 2 < len(odds_vals):
                try:
                    match["odds_home"] = float(odds_vals[odds_idx])
                    match["odds_draw"] = float(odds_vals[odds_idx + 1])
                    match["odds_away"] = float(odds_vals[odds_idx + 2])
                except ValueError:
                    pass
            if "odds_home" in match:
                matches.append(match)
        return matches

    def _parse_oddsportal(self, html: str) -> List[Dict]:
        """Parsea HTML de OddsPortal para extraer odds"""
        matches = []
        # Buscar bloques de partidos
        event_pattern = r'class="[^"]*eventRow[^"]*"[^>]*>(.*?)</div>'
        blocks = re.findall(event_pattern, html, re.DOTALL)

        for block in blocks:
            team_pattern = r'class="[^"]*participant[^"]*"[^>]*>([^<]+)'
            teams = re.findall(team_pattern, block)
            odds_pattern = r'class="[^"]*odds-val[^"]*"[^>]*>([0-9.]+)'
            odds = re.findall(odds_pattern, block)

            if len(teams) >= 2 and len(odds) >= 2:
                match = {
                    "home": teams[0].strip(),
                    "away": teams[1].strip(),
                    "odds_home": float(odds[0]) if odds[0] else None,
                    "odds_away": float(odds[-1]) if odds[-1] else None,
                    "source": "oddsportal",
                }
                if len(odds) >= 3:
                    match["odds_draw"] = float(odds[1])
                matches.append(match)
        return matches

    def _parse_live_scores(self, html: str) -> List[Dict]:
        """Parsea scores en vivo"""
        scores = []
        score_pattern = r'class="event__score[^"]*"[^>]*>([^<]+)'
        found = re.findall(score_pattern, html)
        for i in range(0, len(found) - 1, 2):
            scores.append(
                {
                    "home_score": found[i].strip(),
                    "away_score": found[i + 1].strip(),
                }
            )
        return scores

    def scrape_custom_url(self, url: str) -> Optional[str]:
        """Scrape cualquier URL personalizada via ScraperAPI"""
        return self._fetch(url, render_js=True)
