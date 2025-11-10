"""
Initialization script - Run this once after deployment
Creates necessary directories and initializes the database
"""

import os
import sys
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.database import BettingDatabase


def initialize():
    """Initialize the application"""
    
    logger.info("🚀 Initializing TriunfoBet ML Bot...")
    
    # Create directories
    directories = ['data', 'models', 'logs', 'config']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✅ Directory created/verified: {directory}")
    
    # Initialize database
    logger.info("📊 Initializing database...")
    db = BettingDatabase()
    db.create_tables()
    logger.info("✅ Database initialized")
    
    # Check environment variables
    logger.info("🔍 Checking environment variables...")
    required_vars = [
        'ODDS_API_KEY',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
            logger.warning(f"❌ Missing: {var}")
        else:
            logger.info(f"✅ Found: {var}")
    
    if missing:
        logger.warning(f"⚠️  Missing environment variables: {', '.join(missing)}")
        logger.warning("The bot will run but some features may be disabled")
    else:
        logger.info("✅ All environment variables configured")
    
    # Test API connection
    from src.scrapers.api_odds_fetcher import OddsAPIFetcher
    logger.info("🔌 Testing API connection...")
    fetcher = OddsAPIFetcher()
    status = fetcher.check_api_status()
    
    if status.get('status') == 'ok':
        logger.info(f"✅ API connected - Requests remaining: {status.get('requests_remaining')}")
    else:
        logger.warning(f"⚠️  API connection issue: {status.get('message')}")
    
    # Test Telegram
    from src.utils.notifications import TelegramNotifier
    logger.info("📱 Testing Telegram connection...")
    notifier = TelegramNotifier()
    
    if notifier.enabled:
        success = notifier.send_message("🤖 *TriunfoBet ML Bot Initialized*\n\nSystem is ready!")
        if success:
            logger.info("✅ Telegram notification sent successfully")
        else:
            logger.warning("⚠️  Failed to send Telegram notification")
    else:
        logger.warning("⚠️  Telegram notifications disabled (missing credentials)")
    
    logger.info("\n" + "="*50)
    logger.info("✅ INITIALIZATION COMPLETE")
    logger.info("="*50)
    logger.info("\nYou can now:")
    logger.info("  - Run scheduler: python scheduler.py")
    logger.info("  - Run dashboard: streamlit run app.py")
    logger.info("  - Run analysis: python bot_real.py")


if __name__ == "__main__":
    initialize()
