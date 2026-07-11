"""
Gestión de historial de predicciones y aprendizaje
Guarda picks, verifica resultados, calcula PnL
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config import DAILY_PICKS_FILE, HISTORY_FILE


class HistoryManager:
    """Gestiona el historial de predicciones y resultados"""

    def __init__(self):
        self.history_file = HISTORY_FILE
        self.daily_file = DAILY_PICKS_FILE
        self._ensure_files()

    def _ensure_files(self):
        """Crea archivos y directorios si no existen"""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            self._save_json(
                self.history_file,
                {
                    "predictions": [],
                    "stats": {
                        "total_picks": 0,
                        "wins": 0,
                        "losses": 0,
                        "pending": 0,
                        "total_pnl": 0.0,
                        "bankroll": 1000.0,
                        "best_streak": 0,
                        "current_streak": 0,
                    },
                    "daily_log": [],
                },
            )
        if not os.path.exists(self.daily_file):
            self._save_json(self.daily_file, {"date": "", "picks": []})

    def _load_json(self, filepath: str) -> Dict:
        """Carga archivo JSON"""
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_json(self, filepath: str, data: Dict):
        """Guarda archivo JSON"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def save_daily_picks(self, predictions: List[Dict], parlay: Dict = None):
        """Guarda los picks del día"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily = self._load_json(self.daily_file)

        # Si es un día nuevo, limpiar
        if daily.get("date") != today:
            daily = {"date": today, "picks": [], "parlays": []}

        # Agregar picks nuevos (deduplicar)
        existing_keys = {
            f"{p['home_team']}_{p['pick']}" for p in daily.get("picks", [])
        }

        for pred in predictions:
            for pick in pred.get("picks", []):
                key = f"{pred['home_team']}_{pick['pick']}"
                if key not in existing_keys:
                    daily.setdefault("picks", []).append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "home_team": pred["home_team"],
                            "away_team": pred["away_team"],
                            "sport": pred.get("sport"),
                            **pick,
                            "result": "pending",
                        }
                    )
                    existing_keys.add(key)

        if parlay and parlay.get("legs"):
            daily.setdefault("parlays", []).append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "legs": parlay["legs"],
                    "odds": parlay["odds"],
                    "probability": parlay["probability"],
                    "result": "pending",
                }
            )

        self._save_json(self.daily_file, daily)
        print(f"[HISTORY] Guardados {len(daily['picks'])} picks para {today}")

    def check_results(self, results: List[Dict]) -> Dict:
        """
        Verifica resultados de ayer contra predicciones guardadas.
        results: lista de partidos finalizados con scores
        """
        history = self._load_json(self.history_file)
        daily = self._load_json(self.daily_file)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        wins = 0
        losses = 0
        pnl = 0.0

        for pick in daily.get("picks", []):
            if pick.get("result") != "pending":
                continue

            # Buscar resultado del partido
            matched_result = None
            for result in results:
                if pick.get("home_team") in result.get("home_team", "") or result.get(
                    "home_team", ""
                ) in pick.get("home_team", ""):
                    matched_result = result
                    break

            if not matched_result:
                continue

            # Determinar si ganó o perdió
            won = self._evaluate_pick(pick, matched_result)
            pick["result"] = "win" if won else "loss"

            if won:
                wins += 1
                profit = (pick["odds"] - 1) * (pick["kelly_pct"] / 100) * 10  # Unidades
                pnl += profit
            else:
                losses += 1
                loss = (pick["kelly_pct"] / 100) * 10
                pnl -= loss

        # Actualizar stats globales
        stats = history.get("stats", {})
        stats["total_picks"] = stats.get("total_picks", 0) + wins + losses
        stats["wins"] = stats.get("wins", 0) + wins
        stats["losses"] = stats.get("losses", 0) + losses
        stats["total_pnl"] = stats.get("total_pnl", 0) + pnl
        stats["bankroll"] = stats.get("bankroll", 1000) + pnl

        if wins > 0:
            stats["current_streak"] = stats.get("current_streak", 0) + wins
            stats["best_streak"] = max(
                stats.get("best_streak", 0), stats["current_streak"]
            )
        if losses > 0:
            stats["current_streak"] = 0

        total = stats["wins"] + stats["losses"]
        win_rate = (stats["wins"] / total * 100) if total > 0 else 0

        # Guardar al historial
        history["stats"] = stats
        history.setdefault("daily_log", []).append(
            {
                "date": yesterday,
                "wins": wins,
                "losses": losses,
                "pnl": round(pnl, 2),
                "win_rate": round(win_rate, 1),
            }
        )

        # Mover picks al historial
        history.setdefault("predictions", []).extend(daily.get("picks", []))

        self._save_json(self.history_file, history)
        self._save_json(self.daily_file, {"date": "", "picks": []})

        return {
            "wins": wins,
            "losses": losses,
            "pnl": round(pnl, 2),
            "win_rate": round(win_rate, 1),
            "total_roi": round(stats["total_pnl"] / 10, 2),  # ROI en %
            "bankroll": round(stats["bankroll"], 2),
        }

    def _evaluate_pick(self, pick: Dict, result: Dict) -> bool:
        """Evalúa si un pick fue ganador basado en el resultado"""
        market = pick.get("market", "")
        home_score = int(result.get("home_score", 0))
        away_score = int(result.get("away_score", 0))

        if market == "moneyline":
            picked_team = pick.get("pick", "")
            if picked_team in result.get("home_team", ""):
                return home_score > away_score
            else:
                return away_score > home_score

        elif market == "total":
            total = home_score + away_score
            pick_text = pick.get("pick", "")
            if "Over" in pick_text:
                line = float(pick_text.split("Over ")[-1])
                return total > line
            elif "Under" in pick_text:
                line = float(pick_text.split("Under ")[-1])
                return total < line

        elif market == "spread":
            # Simplificado
            return False  # TODO: implementar evaluación de spread

        return False

    def get_stats(self) -> Dict:
        """Retorna estadísticas globales"""
        history = self._load_json(self.history_file)
        return history.get("stats", {})

    def is_duplicate(self, home_team: str, pick: str) -> bool:
        """Verifica si un pick ya fue enviado hoy (anti-spam)"""
        daily = self._load_json(self.daily_file)
        today = datetime.now().strftime("%Y-%m-%d")
        if daily.get("date") != today:
            return False
        for p in daily.get("picks", []):
            if p.get("home_team") == home_team and p.get("pick") == pick:
                return True
        return False
