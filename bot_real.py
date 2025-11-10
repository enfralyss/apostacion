"""
TriunfoBet Bot - Versión con Datos Reales
Analiza partidos reales y genera recomendaciones
TÚ colocas las apuestas manualmente en TriunfoBet
"""

import os
import sys
from datetime import datetime
from loguru import logger

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.scrapers.api_odds_fetcher import OddsAPIFetcher
from src.models.predictor import MatchPredictor
from src.betting.pick_selector import PickSelector
from src.betting.parlay_builder import ParlayBuilder
from src.betting.stake_calculator import StakeCalculator
from src.utils.database import BettingDatabase
from src.utils.notifications import TelegramNotifier


class RealBettingBot:
    """Bot con datos reales - solo genera recomendaciones"""

    def __init__(self, bankroll: float = 3130.25):
        """
        Args:
            bankroll: Tu bankroll actual en VES
        """
        self.bankroll = bankroll

        # Inicializar componentes
        self.odds_fetcher = OddsAPIFetcher()
        self.predictor = MatchPredictor()
        self.selector = PickSelector()
        self.parlay_builder = ParlayBuilder()
        self.stake_calculator = StakeCalculator()
        self.db = BettingDatabase()
        self.notifier = TelegramNotifier()

        logger.info(f"Bot initialized - Bankroll: VES {self.bankroll:,.2f}")

    def run_analysis(self) -> dict:
        """
        Ejecuta el análisis completo con datos reales

        Returns:
            Diccionario con recomendaciones
        """
        print("\n" + "="*70)
        print("TRIUNFOBET BOT - ANÁLISIS CON DATOS REALES")
        print("="*70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Bankroll: VES {self.bankroll:,.2f}")
        print("="*70)

        # DEBUG: Mostrar criterios cargados
        print(f"\nCriterios de selección cargados:")
        print(f"  - min_probability: {self.selector.pick_criteria['min_probability']*100:.0f}%")
        print(f"  - min_edge: {self.selector.pick_criteria['min_edge']*100:.0f}%")
        print(f"  - min_odds: {self.selector.pick_criteria['min_odds']}")
        print(f"  - max_odds: {self.selector.pick_criteria['max_odds']}")

        # 1. Verificar API
        print("\nVerificando API...")
        status = self.odds_fetcher.check_api_status()

        if status['status'] != 'ok':
            print(f"Error con API: {status}")
            return {'success': False, 'error': 'API not available'}

        print(f"API OK - Requests restantes: {status.get('requests_remaining', 'unknown')}")

        # 2. Obtener partidos REALES (modo solo fútbol)
        print("\nObteniendo partidos reales (SOCCER ONLY MODE)...")
        print("   - Champions League")
        print("   - La Liga")
        print("   - Premier League")
        print("   - Serie A")
        print("   - Bundesliga")
        print("   - Europa League")

        # Solo soccer (API multi-deporte queda para futura extensión)
        matches = self.odds_fetcher.get_available_matches("soccer")

        if not matches:
            print("ERROR - No se encontraron partidos")
            return {'success': False, 'error': 'No matches found'}

        print(f"OK - {len(matches)} partidos encontrados")

        # Mostrar algunos ejemplos
        print("\nEjemplos de partidos:")
        for match in matches[:5]:
            print(f"   • {match['league']}: {match['home_team']} vs {match['away_team']}")
            print(f"     Odds: 1:{match['odds']['home_win']:.2f} X:{match['odds'].get('draw', 'N/A')} 2:{match['odds']['away_win']:.2f}")

        # 3. Analizar con ML
        print(f"\nAnalizando {len(matches)} partidos con ML...")
        predictions = self.predictor.predict_multiple_matches(matches)
        print(f"OK - {len(predictions)} predicciones generadas")

        if len(predictions) == 0:
            print("\n⚠️  WARNING: No se generaron predicciones del modelo ML")
            print("Posibles causas:")
            print("  1. Modelo no cargado correctamente")
            print("  2. Error en features del modelo")
            print("  3. Incompatibilidad entre datos y modelo")
            print("\nRevisa logs/triunfobet_bot.log para detalles del error")
            return {'success': False, 'error': 'Model failed to generate predictions'}

        # 4. Seleccionar picks con valor
        # Leer criterios dinámicamente del config
        min_prob = self.selector.pick_criteria['min_probability']
        min_edge = self.selector.pick_criteria['min_edge']
        min_odds = self.selector.pick_criteria['min_odds']
        max_odds = self.selector.pick_criteria['max_odds']

        print(f"\nBuscando picks con valor (edge > {min_edge*100:.0f}%)...")
        picks = self.selector.select_picks(predictions)

        if not picks:
            print("\nNO SE ENCONTRARON PICKS CON VALOR HOY")
            print(f"Criterios: Probabilidad > {min_prob*100:.0f}%, Edge > {min_edge*100:.0f}%, Odds {min_odds}-{max_odds}")
            print("\nMejor no apostar hoy que forzar apuestas sin ventaja")
            return {
                'success': True,
                'picks_found': 0,
                'message': 'No value picks today'
            }

        print(f"OK - {len(picks)} picks con valor encontrados")

        # 5. Construir parlay
        print("\nConstruyendo parlay óptimo...")
        parlay = self.parlay_builder.build_best_parlay(picks)

        if not parlay:
            print("No se pudo construir un parlay válido")
            return {'success': False, 'error': 'Could not build parlay'}

        # 6. Calcular stake
        stake_info = self.stake_calculator.calculate_recommended_stake(
            probability=parlay['combined_probability'],
            odds=parlay['total_odds'],
            bankroll=self.bankroll,
            strategy='kelly'
        )

        stake = stake_info['recommended_stake']
        potential_return = stake * parlay['total_odds']
        potential_profit = stake * (parlay['total_odds'] - 1)

        # 7. Mostrar recomendación
        self._display_recommendation(parlay, stake, potential_return, potential_profit)

        # 8. Guardar en base de datos (sport= 'soccer' en modo enfocado)
        bet_data = {
            'bet_date': datetime.now().isoformat(),
            'sport': 'soccer',
            'bet_type': 'parlay',
            'total_odds': parlay['total_odds'],
            'stake': stake,
            'potential_return': potential_return,
            'opening_odds': parlay['total_odds'],  # registra la cuota al crear la apuesta
            'edge_at_recommendation': parlay.get('edge'),
            'bankroll_before': self.bankroll,
            'notes': 'Manual placement - Real data'
        }

        bet_id = self.db.save_bet(bet_data, parlay['picks'])

        # Registrar odds por pick en CLV tracking (opening vs bet odds iguales inicialmente)
        try:
            from src.utils.clv_tracker import CLVTracker
            clv = CLVTracker()
            for pick in parlay['picks']:
                clv.save_bet_odds(
                    bet_id=bet_id,
                    match_id=pick.get('match_id', ''),
                    sport='soccer',
                    opening_odds=pick.get('odds'),
                    bet_odds=pick.get('odds')
                )
            clv.close()
        except Exception as e:
            logger.warning(f"No se pudo registrar CLV inicial para bet {bet_id}: {e}")
        print(f"\nRecomendación guardada (ID: {bet_id})")

        # 9. Enviar notificación
        if self.notifier.enabled:
            self.notifier.send_daily_picks(picks, parlay, stake, self.bankroll)
            print("Notificación enviada por Telegram")

        return {
            'success': True,
            'matches_analyzed': len(matches),
            'picks_found': len(picks),
            'parlay': parlay,
            'stake': stake,
            'potential_return': potential_return,
            'bet_id': bet_id
        }

    def _display_recommendation(self, parlay, stake, potential_return, potential_profit):
        """Muestra la recomendación final"""

        print("\n" + "="*70)
        print("RECOMENDACIÓN FINAL - APUESTA MANUAL")
        print("="*70)

        print(f"\nPARLAY DE {parlay['num_picks']} PICKS:")
        print("-"*70)

        for i, pick in enumerate(parlay['picks'], 1):
            print(f"\n{i}. {pick['league']}")
            print(f"   {pick['home_team']} vs {pick['away_team']}")

            # Traducir predicción
            pred_text = {
                'home_win': f"VICTORIA {pick['home_team']}",
                'away_win': f"VICTORIA {pick['away_team']}",
                'draw': 'EMPATE'
            }.get(pick['prediction'], pick['prediction'])

            print(f"   Apuesta: {pred_text}")
            print(f"   Cuota: {pick['odds']:.2f}")
            print(f"   Confianza: {pick['predicted_probability']:.1%}")
            print(f"   Edge: {pick['edge_percentage']:.1f}%")

        print("\n" + "-"*70)
        print(f"CUOTA TOTAL: {parlay['total_odds']:.2f}x")
        print(f"Probabilidad Combinada: {parlay['combined_probability']:.1%}")
        print(f"Edge del Parlay: {parlay['edge_percentage']:.2f}%")

        print("\n" + "-"*70)
        print(f"STAKE RECOMENDADO: VES {stake:.2f}")
        print(f"   ({stake/self.bankroll*100:.1f}% del bankroll)")
        print(f"RETORNO POTENCIAL: VES {potential_return:.2f}")
        print(f"GANANCIA POTENCIAL: VES {potential_profit:.2f}")
        print("="*70)

        print("\nINSTRUCCIONES PARA APOSTAR EN TRIUNFOBET:")
        print("-"*70)
        print("1. Abre https://www.triunfobet.com")
        print("2. Busca cada uno de los partidos listados arriba")
        print("3. Agrega al cupón la opción indicada (Victoria Local/Visitante/Empate)")
        print("4. Ingresa el monto recomendado: VES {:.2f}".format(stake))
        print("5. Verifica que la cuota total sea aproximadamente {:.2f}".format(parlay['total_odds']))
        print("6. Confirma la apuesta")
        print("-"*70)

        print("\nRECORDATORIOS IMPORTANTES:")
        print("   • Verifica que las cuotas no hayan cambiado mucho")
        print("   • Si una cuota bajó significativamente, reconsidera ese pick")
        print("   • Nunca apuestes más del 2% de tu bankroll")
        print("   • Es mejor no apostar que forzar una apuesta sin valor")


def main():
    """Función principal"""

    # Leer bankroll actual (puedes cambiarlo)
    bankroll = 3130.25  # Tu saldo actual en VES

    bot = RealBettingBot(bankroll=bankroll)

    try:
        result = bot.run_analysis()

        if result['success']:
            if result.get('picks_found', 0) > 0:
                print("\nANÁLISIS COMPLETADO - RECOMENDACIÓN LISTA")
            else:
                print("\nANÁLISIS COMPLETADO - NO HAY PICKS HOY")
        else:
            print(f"\nERROR: {result.get('error', 'Unknown error')}")

    except KeyboardInterrupt:
        print("\n\nAnálisis cancelado por el usuario")
    except Exception as e:
        print(f"\nERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
