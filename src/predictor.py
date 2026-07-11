"""
Motor de predicción multi-deporte
Poisson + EV + Kelly Criterion + Filtro de confianza
Adaptable a cualquier deporte con datos reales
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import poisson

from config import (HOME_ADVANTAGE, KELLY_FRACTION, MAX_BET_SIZE_PCT,
                    MIN_CONFIDENCE, MIN_EDGE_PCT, SPORTS_CONFIG)


class SportPredictor:
    """Predictor universal para cualquier deporte"""

    def __init__(self, sport_key: str):
        self.sport_key = sport_key
        self.config = SPORTS_CONFIG.get(sport_key, {})
        self.avg_total = self.config.get("avg_total", 2.5)
        self.scoring_type = self.config.get("scoring_type", "goals")

    def predict_match(self, game: Dict) -> Dict:
        """
        Genera predicción completa para un partido.
        Usa datos reales del game dict (records, odds, pitchers, etc.)
        """
        # Calcular fuerza relativa de cada equipo
        home_strength = self._calculate_strength(game, "home")
        away_strength = self._calculate_strength(game, "away")

        # Ajustar por ventaja local
        home_strength *= 1 + HOME_ADVANTAGE

        # Calcular lambdas (scoring esperado)
        total_strength = home_strength + away_strength
        if total_strength == 0:
            total_strength = 1

        home_lambda = self.avg_total * (home_strength / total_strength)
        away_lambda = self.avg_total * (away_strength / total_strength)

        # Simulación Poisson (10,000 iteraciones)
        n_sims = 10000
        home_scores = np.random.poisson(home_lambda, n_sims)
        away_scores = np.random.poisson(away_lambda, n_sims)

        # Probabilidades
        home_win_prob = np.mean(home_scores > away_scores)
        draw_prob = np.mean(home_scores == away_scores)
        away_win_prob = np.mean(home_scores < away_scores)

        # Over/Under
        total_scores = home_scores + away_scores
        over_prob = np.mean(total_scores > self.avg_total)
        under_prob = np.mean(total_scores <= self.avg_total)

        # BTTS (ambos anotan)
        btts_yes = np.mean((home_scores > 0) & (away_scores > 0))

        # Score más probable
        from collections import Counter

        score_pairs = list(zip(home_scores, away_scores))
        most_common_score = Counter(score_pairs).most_common(1)[0]

        # Calcular EV y Kelly para cada mercado
        picks = []

        # Moneyline
        if game.get("home_ml"):
            home_odds = self._ml_to_decimal(game["home_ml"])
            away_odds = (
                self._ml_to_decimal(game["away_ml"]) if game.get("away_ml") else None
            )

            home_ev = self._calc_ev(home_win_prob, home_odds)
            if home_ev > MIN_EDGE_PCT / 100:
                kelly = self._kelly(home_win_prob, home_odds)
                picks.append(
                    {
                        "market": "moneyline",
                        "pick": game["home_team"],
                        "odds": home_odds,
                        "ml_odds": game["home_ml"],
                        "probability": round(home_win_prob * 100, 1),
                        "ev": round(home_ev * 100, 2),
                        "kelly_pct": round(kelly * 100, 2),
                        "confidence": self._confidence_level(home_win_prob, home_ev),
                    }
                )

            if away_odds:
                away_ev = self._calc_ev(away_win_prob, away_odds)
                if away_ev > MIN_EDGE_PCT / 100:
                    kelly = self._kelly(away_win_prob, away_odds)
                    picks.append(
                        {
                            "market": "moneyline",
                            "pick": game["away_team"],
                            "odds": away_odds,
                            "ml_odds": game["away_ml"],
                            "probability": round(away_win_prob * 100, 1),
                            "ev": round(away_ev * 100, 2),
                            "kelly_pct": round(kelly * 100, 2),
                            "confidence": self._confidence_level(
                                away_win_prob, away_ev
                            ),
                        }
                    )

        # Over/Under
        if game.get("over_under"):
            ou_line = float(game["over_under"])
            over_sim = np.mean(total_scores > ou_line)
            under_sim = np.mean(total_scores <= ou_line)
            # Asumimos cuotas estándar -110 (1.91)
            over_ev = self._calc_ev(over_sim, 1.91)
            under_ev = self._calc_ev(under_sim, 1.91)

            if over_ev > MIN_EDGE_PCT / 100:
                picks.append(
                    {
                        "market": "total",
                        "pick": f"Over {ou_line}",
                        "odds": 1.91,
                        "probability": round(over_sim * 100, 1),
                        "ev": round(over_ev * 100, 2),
                        "kelly_pct": round(self._kelly(over_sim, 1.91) * 100, 2),
                        "confidence": self._confidence_level(over_sim, over_ev),
                    }
                )
            if under_ev > MIN_EDGE_PCT / 100:
                picks.append(
                    {
                        "market": "total",
                        "pick": f"Under {ou_line}",
                        "odds": 1.91,
                        "probability": round(under_sim * 100, 1),
                        "ev": round(under_ev * 100, 2),
                        "kelly_pct": round(self._kelly(under_sim, 1.91) * 100, 2),
                        "confidence": self._confidence_level(under_sim, under_ev),
                    }
                )

        # Spread
        if game.get("spread"):
            try:
                spread_val = float(game["spread"])
                home_cover = np.mean((home_scores - away_scores) > abs(spread_val))
                spread_ev = self._calc_ev(home_cover, 1.91)
                if spread_ev > MIN_EDGE_PCT / 100:
                    picks.append(
                        {
                            "market": "spread",
                            "pick": f"{game['home_team']} {spread_val}",
                            "odds": 1.91,
                            "probability": round(home_cover * 100, 1),
                            "ev": round(spread_ev * 100, 2),
                            "kelly_pct": round(self._kelly(home_cover, 1.91) * 100, 2),
                            "confidence": self._confidence_level(home_cover, spread_ev),
                        }
                    )
            except (ValueError, TypeError):
                pass

        # Resultado final
        prediction = {
            "sport": self.sport_key,
            "home_team": game.get("home_team"),
            "away_team": game.get("away_team"),
            "home_lambda": round(home_lambda, 2),
            "away_lambda": round(away_lambda, 2),
            "probabilities": {
                "home_win": round(home_win_prob * 100, 1),
                "draw": round(draw_prob * 100, 1),
                "away_win": round(away_win_prob * 100, 1),
            },
            "over_under": {
                "line": self.avg_total,
                "over_prob": round(over_prob * 100, 1),
                "under_prob": round(under_prob * 100, 1),
            },
            "btts": round(btts_yes * 100, 1),
            "predicted_score": f"{most_common_score[0][0]}-{most_common_score[0][1]}",
            "score_probability": round(most_common_score[1] / n_sims * 100, 1),
            "picks": picks,
            "raw_data": {
                "home_strength": round(home_strength, 3),
                "away_strength": round(away_strength, 3),
                "home_record": game.get("home_record"),
                "away_record": game.get("away_record"),
            },
        }
        return prediction

    def _calculate_strength(self, game: Dict, side: str) -> float:
        """Calcula fuerza del equipo basado en datos reales disponibles"""
        strength = 0.5  # Base neutral

        # Factor 1: Win percentage del record
        win_pct = game.get(f"{side}_win_pct", 0.5)
        strength = win_pct

        # Factor 2: Pitcher ERA (solo MLB)
        era = game.get(f"{side}_pitcher_era")
        if era and era != "TBD":
            try:
                era_val = float(era)
                # ERA baja = mejor, normalizar inversamente
                era_factor = max(
                    0, 1 - (era_val / 9.0)
                )  # ERA 0=1.0, ERA 4.5=0.5, ERA 9=0
                strength = strength * 0.6 + era_factor * 0.4
            except (ValueError, TypeError):
                pass

        # Factor 3: Odds implícitas del mercado (si disponibles)
        ml = game.get(f"{side}_ml")
        if ml:
            implied_prob = self._ml_to_implied_prob(ml)
            if implied_prob:
                # Mezclar modelo con mercado (60% modelo, 40% mercado)
                strength = strength * 0.6 + implied_prob * 0.4

        return max(0.1, min(0.9, strength))

    def _ml_to_decimal(self, ml: int) -> float:
        """Convierte moneyline americano a cuota decimal"""
        if ml is None:
            return 2.0
        ml = int(ml)
        if ml > 0:
            return (ml / 100) + 1
        else:
            return (100 / abs(ml)) + 1

    def _ml_to_implied_prob(self, ml: int) -> Optional[float]:
        """Convierte moneyline a probabilidad implícita"""
        if ml is None:
            return None
        ml = int(ml)
        if ml > 0:
            return 100 / (ml + 100)
        else:
            return abs(ml) / (abs(ml) + 100)

    def _calc_ev(self, prob: float, odds: float) -> float:
        """Calcula Expected Value"""
        return (prob * odds) - 1

    def _kelly(self, prob: float, odds: float) -> float:
        """Kelly Criterion fraccional"""
        b = odds - 1
        q = 1 - prob
        if b <= 0:
            return 0
        kelly_full = (b * prob - q) / b
        kelly_frac = kelly_full * KELLY_FRACTION
        return max(0, min(kelly_frac, MAX_BET_SIZE_PCT / 100))

    def _confidence_level(self, prob: float, ev: float) -> str:
        """Determina nivel de confianza del pick"""
        if prob >= 0.65 and ev >= 0.08:
            return "HIGH"
        elif prob >= 0.55 and ev >= 0.05:
            return "MEDIUM"
        else:
            return "LOW"

    def generate_parlay(
        self, predictions: List[Dict], target_odds: float = 5.0
    ) -> Dict:
        """
        Genera el mejor parlay posible con las predicciones del día.
        target_odds: cuota objetivo del parlay
        """
        # Recolectar todos los picks con confianza MEDIUM o HIGH
        all_picks = []
        for pred in predictions:
            for pick in pred.get("picks", []):
                if pick["confidence"] in ["HIGH", "MEDIUM"]:
                    all_picks.append(
                        {
                            **pick,
                            "home_team": pred["home_team"],
                            "away_team": pred["away_team"],
                        }
                    )

        # Ordenar por EV descendente
        all_picks.sort(key=lambda x: x["ev"], reverse=True)

        # Construir parlay acumulando hasta la cuota objetivo
        parlay_legs = []
        cumulative_odds = 1.0

        for pick in all_picks:
            if cumulative_odds >= target_odds:
                break
            if len(parlay_legs) >= 5:  # Máximo 5 piernas
                break
            cumulative_odds *= pick["odds"]
            parlay_legs.append(pick)

        if not parlay_legs:
            return {"legs": [], "odds": 0, "probability": 0}

        # Probabilidad conjunta (independencia asumida)
        joint_prob = 1.0
        for leg in parlay_legs:
            joint_prob *= leg["probability"] / 100

        parlay_ev = (joint_prob * cumulative_odds) - 1

        return {
            "legs": parlay_legs,
            "odds": round(cumulative_odds, 2),
            "probability": round(joint_prob * 100, 2),
            "ev": round(parlay_ev * 100, 2),
            "num_legs": len(parlay_legs),
        }
