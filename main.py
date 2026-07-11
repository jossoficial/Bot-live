"""
Sports Prediction Bot - Main Orchestrator
Ejecuta el pipeline completo: datos → predicción → filtro → telegram
Adaptable a cualquier deporte con datos reales en vivo
"""

import json
import sys
from datetime import datetime

from config import SPORTS_CONFIG
from src.free_data import FreeDataProvider
from src.history import HistoryManager
from src.predictor import SportPredictor
from src.scraper import LiveScraper
from src.telegram_bot import TelegramSender


def run_predictions(sports: list = None):
    """
    Pipeline principal de predicciones.
    sports: lista de deportes a analizar (default: todos los activos hoy)
    """
    print(f"\n{'═' * 60}")
    print(f"  🤖 SPORTS PREDICTION BOT - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * 60}\n")

    # Inicializar componentes
    data_provider = FreeDataProvider()
    scraper = LiveScraper()
    telegram = TelegramSender()
    history = HistoryManager()

    # Si no se especifican deportes, intentar todos
    if sports is None:
        sports = list(SPORTS_CONFIG.keys())

    all_predictions = {}

    for sport_key in sports:
        sport_name = SPORTS_CONFIG[sport_key]["name"]
        print(f"\n{'─' * 40}")
        print(f"  📡 Obteniendo datos: {sport_name}")
        print(f"{'─' * 40}")

        # 1. OBTENER DATOS EN VIVO (endpoints gratuitos)
        games = data_provider.get_today_games(sport_key)

        if not games:
            print(f"  ❌ No hay partidos de {sport_name} hoy")
            continue

        print(f"  ✅ {len(games)} partidos encontrados")

        # 2. ENRIQUECER CON SCRAPER (odds reales si disponible)
        try:
            scraped_odds = scraper.get_odds_flashscore(sport_key)
            if scraped_odds:
                print(f"  📊 {len(scraped_odds)} odds scrapeadas de Flashscore")
                # Merge odds scrapeadas con datos de ESPN
                for game in games:
                    for odds in scraped_odds:
                        if (
                            odds.get("home", "").lower()
                            in game.get("home_team", "").lower()
                            or game.get("home_team", "").lower()
                            in odds.get("home", "").lower()
                        ):
                            if not game.get("home_ml") and odds.get("odds_home"):
                                game["home_ml"] = self._decimal_to_ml(odds["odds_home"])
                                game["away_ml"] = self._decimal_to_ml(odds["odds_away"])
                            break
        except Exception as e:
            print(f"  ⚠️ Scraper no disponible: {e}")

        # 3. PREDECIR CADA PARTIDO
        predictor = SportPredictor(sport_key)
        predictions = []

        for game in games:
            try:
                pred = predictor.predict_match(game)
                if pred.get("picks"):  # Solo si hay picks con valor
                    predictions.append(pred)
            except Exception as e:
                print(f"  ⚠️ Error prediciendo {game.get('home_team')}: {e}")

        print(f"  🎯 {len(predictions)} partidos con picks de valor")

        # 4. GENERAR PARLAY
        parlay = predictor.generate_parlay(predictions, target_odds=5.0)
        if parlay.get("legs"):
            print(f"  🎰 Parlay: {parlay['num_legs']} piernas, cuota {parlay['odds']}")

        # 5. DEDUPLICAR (no enviar picks repetidos)
        new_predictions = []
        for pred in predictions:
            new_picks = []
            for pick in pred.get("picks", []):
                if not history.is_duplicate(pred["home_team"], pick["pick"]):
                    new_picks.append(pick)
            if new_picks:
                pred["picks"] = new_picks
                new_predictions.append(pred)

        # 6. ENVIAR A TELEGRAM
        if new_predictions:
            telegram.send_picks(new_predictions, parlay, sport_name)
            print(f"  📤 Enviado a Telegram")
        else:
            print(f"  ℹ️ Sin picks nuevos (ya enviados o sin valor)")

        # 7. GUARDAR EN HISTORIAL
        history.save_daily_picks(predictions, parlay)

        all_predictions[sport_key] = {
            "games_found": len(games),
            "picks_generated": len(predictions),
            "parlay": parlay,
        }

    # Resumen final
    print(f"\n{'═' * 60}")
    print(f"  ✅ PIPELINE COMPLETADO")
    for sport, info in all_predictions.items():
        print(
            f"     {sport}: {info['games_found']} juegos, {info['picks_generated']} picks"
        )
    print(f"{'═' * 60}\n")

    return all_predictions


def check_yesterday_results(sports: list = None):
    """Verifica resultados de ayer y actualiza historial"""
    print(f"\n{'═' * 60}")
    print(f"  📋 VERIFICANDO RESULTADOS DE AYER")
    print(f"{'═' * 60}\n")

    data_provider = FreeDataProvider()
    history = HistoryManager()
    telegram = TelegramSender()

    if sports is None:
        sports = list(SPORTS_CONFIG.keys())

    all_results = []
    for sport_key in sports:
        results = data_provider.get_yesterday_results(sport_key)
        if results:
            all_results.extend(results)
            print(f"  {sport_key}: {len(results)} resultados obtenidos")

    if all_results:
        summary = history.check_results(all_results)
        telegram.send_results_update(summary)
        print(
            f"  📊 W: {summary['wins']} | L: {summary['losses']} | P/L: {summary['pnl']}"
        )
    else:
        print("  ❌ No se pudieron obtener resultados de ayer")


def _decimal_to_ml(decimal_odds: float) -> int:
    """Convierte cuota decimal a moneyline americano"""
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))


if __name__ == "__main__":
    # Determinar qué deportes analizar
    if len(sys.argv) > 1:
        if sys.argv[1] == "--results":
            # Modo: verificar resultados de ayer
            sports_arg = sys.argv[2:] if len(sys.argv) > 2 else None
            check_yesterday_results(sports_arg)
        else:
            # Modo: predicciones para deportes específicos
            run_predictions(sys.argv[1:])
    else:
        # Modo: todos los deportes
        run_predictions()
