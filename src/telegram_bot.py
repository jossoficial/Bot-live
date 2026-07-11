"""
Módulo de envío de picks a Telegram
Formatea y envía predicciones de cualquier deporte
"""

from typing import Dict, List

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramSender:
    """Envía picks formateados a Telegram"""

    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str) -> bool:
        """Envía mensaje a Telegram"""
        if not self.token or not self.chat_id:
            print("[TELEGRAM] No configurado, imprimiendo en consola:")
            print(text)
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                print("[TELEGRAM] Mensaje enviado OK")
                return True
            else:
                print(f"[TELEGRAM] Error: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"[TELEGRAM] Exception: {e}")
            return False

    def format_predictions(self, predictions: List[Dict], sport_name: str) -> str:
        """Formatea predicciones para enviar por Telegram"""
        emoji_map = {
            "HIGH": "🔥",
            "MEDIUM": "✅",
            "LOW": "⚠️",
        }

        lines = [
            f"🏆 <b>PICKS {sport_name.upper()} - HOY</b>",
            f"{'═' * 30}",
            "",
        ]

        pick_count = 0
        for pred in predictions:
            if not pred.get("picks"):
                continue

            lines.append(f"⚔️ <b>{pred['away_team']} @ {pred['home_team']}</b>")
            lines.append(
                f"   📊 Prob: H {pred['probabilities']['home_win']}% | "
                f"D {pred['probabilities']['draw']}% | "
                f"A {pred['probabilities']['away_win']}%"
            )
            lines.append(f"   🎯 Score: {pred['predicted_score']}")

            for pick in pred["picks"]:
                emoji = emoji_map.get(pick["confidence"], "")
                lines.append(f"   {emoji} <b>{pick['pick']}</b> ({pick['market']})")
                lines.append(
                    f"      Cuota: {pick['odds']:.2f} | "
                    f"EV: +{pick['ev']}% | "
                    f"Kelly: {pick['kelly_pct']}%"
                )
                pick_count += 1

            lines.append("")

        if pick_count == 0:
            lines.append("❌ No se encontraron picks con valor hoy.")
        else:
            lines.append(f"📈 Total picks con valor: {pick_count}")

        lines.append(f"\n{'═' * 30}")
        lines.append("🤖 Sports Prediction Bot v2.0")

        return "\n".join(lines)

    def format_parlay(self, parlay: Dict, sport_name: str) -> str:
        """Formatea parlay para Telegram"""
        if not parlay.get("legs"):
            return ""

        lines = [
            f"🎰 <b>PARLAY {sport_name.upper()}</b>",
            f"{'═' * 30}",
            f"📊 Cuota combinada: <b>{parlay['odds']}</b>",
            f"📈 Probabilidad: {parlay['probability']}%",
            f"💰 EV: {'+' if parlay['ev'] > 0 else ''}{parlay['ev']}%",
            "",
        ]

        for i, leg in enumerate(parlay["legs"], 1):
            conf_emoji = "🔥" if leg["confidence"] == "HIGH" else "✅"
            lines.append(
                f"  {i}. {conf_emoji} <b>{leg['pick']}</b> @ {leg['odds']:.2f}"
            )
            lines.append(f"     Prob: {leg['probability']}% | EV: +{leg['ev']}%")

        lines.append(f"\n{'═' * 30}")
        return "\n".join(lines)

    def send_picks(self, predictions: List[Dict], parlay: Dict, sport_name: str):
        """Envía picks + parlay completo"""
        # Enviar predicciones individuales
        msg = self.format_predictions(predictions, sport_name)
        if msg:
            self.send_message(msg)

        # Enviar parlay si tiene piernas
        if parlay and parlay.get("legs"):
            parlay_msg = self.format_parlay(parlay, sport_name)
            if parlay_msg:
                self.send_message(parlay_msg)

    def send_results_update(self, results: Dict):
        """Envía actualización de resultados del día anterior"""
        lines = [
            "📋 <b>RESULTADOS DE AYER</b>",
            f"{'═' * 30}",
            f"✅ Aciertos: {results.get('wins', 0)}",
            f"❌ Fallos: {results.get('losses', 0)}",
            f"📊 Win Rate: {results.get('win_rate', 0):.1f}%",
            f"💰 P/L: {'+'if results.get('pnl', 0) >= 0 else ''}{results.get('pnl', 0):.2f}u",
            f"📈 ROI acumulado: {results.get('total_roi', 0):.2f}%",
            f"🏦 Bankroll: ${results.get('bankroll', 1000):.2f}",
        ]
        self.send_message("\n".join(lines))
