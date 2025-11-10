# 🤖 Copilot Instructions for TriunfoBet Automated Betting Bot

## Project Overview

This project is an automated sports betting system using machine learning to identify value picks and build optimized parlays for NBA and soccer. It features scraping, ML prediction, bankroll management, Telegram notifications, and detailed logging. The codebase is modular, with clear separation between scraping, modeling, betting logic, and utilities.

## Key Components & Data Flow

- **Scraping**: `src/scrapers/` fetches odds and stats (see `api_odds_fetcher.py`, `stats_collector.py`).
- **Modeling**: `src/models/` handles training (`train_model.py`) and prediction (`predictor.py`). Models are stored in `models/`.
- **Betting Logic**: `src/betting/` selects picks (`pick_selector.py`), builds parlays (`parlay_builder.py`), and calculates stakes (`stake_calculator.py`).
- **Automation**: `src/automation/` (e.g., `bet_placer.py`) manages automated bet placement.
- **Utilities**: `src/utils/` provides logging, database, notifications, and data generation.
- **Configuration**: All parameters are set in `config/config.yaml` (bankroll, picks, parlay, paper trading, etc).
- **Entrypoints**: Main scripts include `daily_bot.py`, `app.py` (Streamlit UI), and `bot_real.py` (real betting).

## Developer Workflows

- **Setup**: Use a Python 3.10+ venv and install dependencies from `requirements.txt`.
- **Model Training**: Run `python src/models/train_model.py` to (re)train models.
- **Testing**: Each module can be tested standalone via `if __name__ == "__main__"`. Example: `python src/betting/pick_selector.py`.
- **Run Bot**: Use `python daily_bot.py` for full pipeline. For Streamlit UI, run `streamlit run app.py`.
- **Paper Trading**: Enabled by default in `config/config.yaml`.
- **Logs & Data**: Logs in `logs/`, models in `models/`, historical data in `data/`.

## Project-Specific Patterns & Conventions

- **Config-Driven**: All logic (thresholds, bankroll, parlay size, etc.) is controlled via `config/config.yaml`.
- **Modular Testing**: Each core file is executable for quick testing/debugging.
- **Database**: Uses SQLite via `src/utils/database.py` for bet tracking and metrics.
- **Notifications**: Telegram integration via `src/utils/notifications.py` (optional, .env required).
- **Paper Trading**: Strongly encouraged for at least 30 days before real betting.
- **Logging**: Use `src/utils/logger.py` for all logs; do not print directly in production code.

## Integration & External Dependencies

- **ML**: XGBoost, scikit-learn for modeling.
- **Scraping**: Requests/BeautifulSoup for odds and stats.
- **Notifications**: Telegram Bot API (optional).
- **Database**: SQLite (no external DB required).

## Examples

- To add a new betting strategy, create a new module in `src/betting/` and update the main pipeline in `daily_bot.py`.
- To adjust risk management, edit the bankroll section in `config/config.yaml`.
- To test a new scraper, run it directly: `python src/scrapers/triunfobet_scraper.py`.

## Quick References

- Start here for a full functionality map: `docs/AI_PROJECT_MAP.md` (architecture, data contracts, workflows).
- `README.md` for setup and user-level docs.
- `config/config.yaml` for all runtime parameters.
- `src/utils/database.py` for DB schema and metrics functions.

---

For questions or unclear patterns, review the README or ask for clarification. Please suggest improvements to this file if you find missing or outdated information.
