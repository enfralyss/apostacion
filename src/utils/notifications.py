"""
Notifications - Envía notificaciones vía Telegram
"""

import os
import requests
from typing import Dict, List
from datetime import datetime
from loguru import logger


class TelegramNotifier:
    """Enviador de notificaciones vía Telegram"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Args:
            bot_token: Token del bot de Telegram
            chat_id: ID del chat para enviar mensajes
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.warning("Telegram notifications disabled - missing credentials")

    def send_message(self, message: str) -> bool:
        """
        Envía un mensaje de texto

        Args:
            message: Mensaje a enviar

        Returns:
            True si se envió exitosamente
        """
        if not self.enabled:
            logger.debug("Telegram disabled, message not sent")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"[TELEGRAM] Message sent successfully")
                return True
            else:
                logger.error(f"[TELEGRAM] Failed to send: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def send_daily_picks(self, picks: List[Dict], parlay: Dict, stake: float,
                        bankroll: float) -> bool:
        """
        Envía notificación con los picks del día

        Args:
            picks: Lista de picks seleccionados
            parlay: Información del parlay
            stake: Monto a apostar
            bankroll: Bankroll actual

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

        message += "✅ *Apuesta lista para colocar*"

        return self.send_message(message)

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
