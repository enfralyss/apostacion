"""
Notifications - Envía notificaciones vía Telegram
"""

import os
import requests
from typing import Dict, List
from datetime import datetime
from loguru import logger


class TelegramNotifier:
    """
    Enviador de notificaciones vía Telegram
    Soporta envío a múltiples usuarios (broadcast)
    """

    def __init__(self, bot_token: str = None, chat_ids: List[str] = None):
        """
        Args:
            bot_token: Token del bot de Telegram
            chat_ids: Lista de chat IDs o string separado por comas
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')

        # Soportar tanto lista como string separado por comas
        if chat_ids:
            if isinstance(chat_ids, list):
                self.chat_ids = chat_ids
            else:
                self.chat_ids = [c.strip() for c in str(chat_ids).split(',') if c.strip()]
        else:
            # Intentar cargar desde variable de entorno (soporta pool)
            chat_ids_env = os.getenv('TELEGRAM_CHAT_IDS', '') or os.getenv('TELEGRAM_CHAT_ID', '')
            self.chat_ids = [c.strip() for c in chat_ids_env.split(',') if c.strip()]

        self.enabled = bool(self.bot_token and self.chat_ids)

        if not self.enabled:
            logger.warning("Telegram notifications disabled - missing credentials")
        else:
            logger.info(f"Telegram notifier initialized for {len(self.chat_ids)} recipients")

    def send_message(self, message: str, chat_id: str = None) -> bool:
        """
        Envía un mensaje de texto (broadcast a todos los usuarios o a uno específico)

        Args:
            message: Mensaje a enviar
            chat_id: Chat ID específico (opcional). Si no se provee, envía a todos

        Returns:
            True si se envió exitosamente a al menos un usuario
        """
        if not self.enabled:
            logger.debug("Telegram disabled, message not sent")
            return False

        # Determinar a quién enviar
        target_chats = [chat_id] if chat_id else self.chat_ids

        success_count = 0
        fail_count = 0

        for chat in target_chats:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                data = {
                    'chat_id': chat,
                    'text': message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }

                response = requests.post(url, data=data, timeout=10)

                if response.status_code == 200:
                    logger.debug(f"[TELEGRAM] Message sent to {chat[:8]}...")
                    success_count += 1
                else:
                    logger.warning(f"[TELEGRAM] Failed to send to {chat[:8]}: {response.status_code}")
                    fail_count += 1

            except Exception as e:
                logger.error(f"Error sending Telegram message to {chat[:8]}: {e}")
                fail_count += 1

        # Retornar True si al menos uno fue exitoso
        if success_count > 0:
            logger.info(f"[TELEGRAM] Broadcast sent: {success_count} successful, {fail_count} failed")
            return True
        else:
            logger.error(f"[TELEGRAM] Broadcast failed completely: {fail_count} failures")
            return False

    def send_daily_picks(self, picks: List[Dict], parlay: Dict, stake: float,
                        bankroll: float, clv_stats: Dict = None) -> bool:
        """
        Envía notificación con los picks del día

        Args:
            picks: Lista de picks seleccionados
            parlay: Información del parlay
            stake: Monto a apostar
            bankroll: Bankroll actual
            clv_stats: Estadísticas de CLV (opcional)

        Returns:
            True si se envió exitosamente
        """
        if not picks:
            message = "🚫 *NO PICKS TODAY*\n\n"
            message += "No se encontraron apuestas con valor suficiente.\n"
            message += "Mejor no apostar hoy."
            return self.send_message(message)

        message = "🤖 *DAILY ANALYSIS*\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"

        message += f"💎 *Picks encontrados:* {len(picks)}\n\n"

        message += "🎯 *PARLAY RECOMENDADO*\n"
        message += "─" * 30 + "\n\n"

        for i, pick in enumerate(parlay['picks'], 1):
            message += f"{i}️⃣ *{pick['league']}*\n"
            message += f"   {pick['home_team']} vs {pick['away_team']}\n"
            message += f"   └ *{pick['prediction']}* @ {pick['odds']:.2f}\n"
            message += f"   └ Conf: {pick['predicted_probability']:.1%}, Edge: {pick['edge_percentage']:.1f}%\n\n"

        message += "─" * 30 + "\n"
        message += f"💰 *Cuota Total:* {parlay['total_odds']:.2f}x\n"
        message += f"🎲 *Probabilidad:* {parlay['combined_probability']:.1%}\n"
        message += f"💵 *Stake Recomendado:* ${stake:.2f}\n"
        message += f"🏆 *Retorno Potencial:* ${stake * parlay['total_odds']:.2f}\n"
        message += f"💎 *Ganancia Potencial:* ${stake * (parlay['total_odds'] - 1):.2f}\n\n"

        message += f"💼 *Bankroll:* ${bankroll:.2f}\n"
        message += f"📊 *% del Bankroll:* {stake/bankroll*100:.1f}%\n\n"

        # Agregar CLV stats si están disponibles
        if clv_stats and clv_stats.get('total_bets', 0) > 10:
            message += "📈 *CLV Performance*\n"
            message += f"   CLV Promedio: {clv_stats['avg_clv_percentage']:.2f}%\n"
            message += f"   Tasa Positivos: {clv_stats['positive_clv_rate']:.1f}%\n"
            
            # Badge según performance CLV
            avg_clv = clv_stats['avg_clv_percentage']
            if avg_clv > 5:
                message += "   Rating: ⭐⭐⭐⭐⭐ ELITE\n"
            elif avg_clv > 3:
                message += "   Rating: ⭐⭐⭐⭐ SHARP\n"
            elif avg_clv > 1:
                message += "   Rating: ⭐⭐⭐ BUENO\n"
            elif avg_clv > -1:
                message += "   Rating: ⭐⭐ NEUTRO\n"
            else:
                message += "   Rating: ⭐ NEGATIVO\n"
            message += "\n"

        message += "✅ *Apuesta lista para colocar*"

        return self.send_message(message)

    def send_placement_update(self, placement_info: Dict) -> bool:
        """Envía notificación cuando se registra la colocación real de una apuesta.

        Args:
            placement_info: Dict retornado por update_bet_placement

        Returns:
            True si se envía al menos a un destinatario
        """
        if not placement_info:
            return False
        msg = "📝 *PLACEMENT UPDATE*\n\n"
        msg += f"Apuesta ID: {placement_info['bet_id']}\n"
        rec_odds = placement_info.get('recommended_odds')
        if rec_odds:
            msg += f"Cuota recomendada: {rec_odds:.2f}\n"
        msg += f"Cuota colocada: {placement_info['placed_odds']:.2f}\n"
        msg += f"Stake ajustado: {placement_info['adjusted_stake']:.2f}\n"
        msg += f"Edge recomendado: {placement_info['edge_at_recommendation']*100:.2f}%\n"
        msg += f"Edge al placement: {placement_info['edge_at_placement']*100:.2f}%\n"
        stake_diff = placement_info.get('stake_diff', 0)
        if stake_diff != 0:
            msg += f"Δ Stake: {stake_diff:+.2f}\n"
        return self.send_message(msg)

    def send_bet_result(self, bet_result: str, profit_loss: float,
                       new_bankroll: float, win_rate: float) -> bool:
        """
        Envía notificación con resultado de apuesta

        Args:
            bet_result: 'won', 'lost', 'push'
            profit_loss: Ganancia/pérdida
            new_bankroll: Nuevo bankroll
            win_rate: Win rate actual

        Returns:
            True si se envió exitosamente
        """
        if bet_result == 'won':
            emoji = "🎉"
            status = "*GANAMOS*"
        elif bet_result == 'lost':
            emoji = "😞"
            status = "*PERDIMOS*"
        else:
            emoji = "🤝"
            status = "*EMPATE*"

        message = f"{emoji} *BET RESULT* {emoji}\n\n"
        message += f"{status}\n"
        message += f"P/L: ${profit_loss:+.2f}\n\n"
        message += f"💼 Nuevo Bankroll: ${new_bankroll:.2f}\n"
        message += f"📊 Win Rate: {win_rate:.1f}%\n"

        return self.send_message(message)

    def send_pick_result(self, pick: Dict) -> bool:
        """Envía notificación cuando un pick individual se resuelve.

        Espera un dict con:
          - league, home_team, away_team, prediction, odds, predicted_probability, edge
          - pick_result: 'won' | 'lost'
          - bet_id, bet_settled, bet_result (opcionales)
        """
        if not pick:
            return False
        outcome = pick.get('pick_result') or pick.get('result')
        emoji = '✅' if outcome == 'won' else ('❌' if outcome == 'lost' else 'ℹ️')
        msg = f"{emoji} *PICK RESULT*\n\n"
        league = pick.get('league', '')
        if league:
            msg += f"🏟️ {league}\n"
        ht = pick.get('home_team', 'Local')
        at = pick.get('away_team', 'Visitante')
        msg += f"{ht} vs {at}\n"
        pred = pick.get('prediction', '')
        if pred:
            msg += f"Pick: *{pred}*\n"
        odds = pick.get('odds')
        if odds:
            msg += f"Cuota: {float(odds):.2f}\n"
        prob = pick.get('predicted_probability')
        if prob is not None:
            msg += f"Confianza: {float(prob):.1%}\n"
        edge = pick.get('edge')
        if edge is not None:
            msg += f"Edge: {float(edge)*100:.1f}%\n"
        # Contexto de parlay
        if pick.get('bet_id'):
            if pick.get('bet_settled'):
                msg += f"\nParlay ID {pick['bet_id']} -> *{pick.get('bet_result','')}*\n"
            else:
                msg += f"\nParlay ID {pick['bet_id']} sigue en juego\n"
        return self.send_message(msg)

    def send_alert(self, alert_type: str, message: str) -> bool:
        """
        Envía alerta importante

        Args:
            alert_type: Tipo de alerta
            message: Mensaje de alerta

        Returns:
            True si se envió exitosamente
        """
        alert_message = f"🚨 *ALERT: {alert_type}*\n\n{message}"
        return self.send_message(alert_message)


# Mock para testing sin dependencias
from datetime import datetime


if __name__ == "__main__":
    # Test del notifier
    notifier = TelegramNotifier()

    print("=== Testing Telegram Notifier ===\n")

    # Test mensaje simple
    notifier.send_message("Test message from TriunfoBet Bot")

    # Test daily picks
    test_picks = [
        {
            'league': 'La Liga',
            'home_team': 'Real Madrid',
            'away_team': 'Barcelona',
            'prediction': 'home_win',
            'odds': 1.85,
            'predicted_probability': 0.712,
            'edge_percentage': 8.3
        }
    ]

    test_parlay = {
        'picks': test_picks,
        'total_odds': 12.38,
        'combined_probability': 0.238
    }

    notifier.send_daily_picks(test_picks, test_parlay, stake=95.0, bankroll=5000.0)

    # Test resultado
    notifier.send_bet_result('won', profit_loss=1081.10, new_bankroll=6081.10, win_rate=65.2)
