# TriunfoBet Bot – Functional Map for AI Agents

This file summarizes all core functionality so an AI assistant can work productively without re‑scanning the entire repo each time. It captures architecture, data flows, key modules/classes, input/output contracts, and developer workflows.

## Architecture & Data Flow
- Scraping (real/derived): `src/scrapers/`
  - `api_odds_fetcher.py::OddsAPIFetcher`
    - Pulls odds from The Odds API (decimal format, markets=h2h, regions=us,eu).
    - Averages odds across bookmakers; returns matches with fields:
      - `{'match_id','sport'(soccer|nba),'league','home_team','away_team','match_date','bookmakers_count', 'odds': {'home_win': float, 'away_win': float, ['draw': float]}}`
    - Rotates API keys using `src/utils/api_key_manager.py` (env: `ODDS_API_KEYS`, fallback `ODDS_API_KEY`).
  - `stats_collector.py::StatsCollector`
    - Provides team stats; mock by default.
  - `historical_odds_scraper.py`
    - Backfills historical odds (for backtesting/datasets).

- Modeling: `src/models/`
  - `train_model.py::BettingModel`
    - Trains and persists models (`models/soccer_model.pkl`, `models/nba_model.pkl`).
    - Uses engineered features from DB when available; falls back to synthetic generator.
  - `predictor.py::MatchPredictor`
    - Loads models; builds features via `BettingDatabase.calculate_match_features(match)`; predicts outcome label and `probabilities` per outcome.
    - Output schema:
      - `{'match_id','sport','league','home_team','away_team','match_date','prediction','confidence','probabilities': {'home_win': p, 'away_win': p, ['draw': p]}, 'odds': {...}}`

- Betting Logic: `src/betting/`
  - `pick_selector.py::PickSelector`
    - Evaluates each prediction with offered odds; calculates
      - implied probability = `1/odds`
      - edge = `predicted_prob - implied_prob`
      - EV = `stake * (p*(odds-1) - (1-p))` (stake=100 by default for ranking).
    - Filters by config thresholds `config/config.yaml -> picks` (min_probability, min_edge, min/max_odds, max_picks_per_league).
    - Output pick:
      - `{'match_id','sport','league','home_team','away_team','match_date','prediction','predicted_probability', 'odds', 'implied_probability','edge','edge_percentage','expected_value','has_value', 'criteria_met', 'rejection_reasons'}`
  - `parlay_builder.py::ParlayBuilder`
    - `calculate_parlay_odds(picks)` multiplies decimal odds.
    - `calculate_parlay_probability(picks)` multiplies predicted probabilities.
    - `calculate_parlay_edge(picks)` = combined_prob − `1/total_odds`.
    - Utility: `decimal_to_american(odds)` for display.
  - `stake_calculator_improved.py::StakeCalculator`
    - Kelly 1/4 with safety caps; also flat strategy.
    - `calculate_kelly_stake(prob, odds, bankroll)` returns stake; skips if edge < 2%.
    - `calculate_parlay_stake(picks, bankroll, strategy)` handles parlays.

- Automation: `src/automation/bet_placer.py::TriunfoBetPlacer`
  - Selenium automation (dry‑run by default). Methods: `login`, `place_parlay_bet`, `get_balance`, `take_screenshot`, `close`.
  - NOTE: Selectors in comments must be adapted to TriunfoBet DOM.

- Utilities: `src/utils/`
  - `database.py::BettingDatabase`
    - SQLite persistence: `bets`, `picks`, `bankroll_history`, `performance_metrics`, `raw_odds_snapshots`, `raw_match_results`, `canonical_odds`, `engineered_features`.
    - Key methods:
      - `save_odds_snapshot(matches)` – store raw odds; `build_canonical_odds_*` – normalize implied probs and remove margin.
      - `calculate_match_features(match)` – compute features used by models from current odds + historical DB.
      - `save_bet(bet_data, picks)`, `update_bet_result`, `update_bet_placement` (recompute CLV/edge and stake at placement), `get_recent_bets`, `get_picks_for_bet`.
      - `calculate_performance_metrics()` – returns win_rate, ROI, totals.
  - `notifications.py::TelegramNotifier`
    - Sends Markdown messages for daily picks/parlays and placement summaries.
  - `logger.py` – Loguru configuration.
  - `data_generator.py` – synthetic data for bootstrap.
  - `api_key_manager.py` – round‑robin API key rotation with usage tracking.
  - `clv_tracker.py` – closing line value helpers.

- Backtesting: `src/backtesting/`
  - `historical_data.py`, `backtest_engine.py` – simulate strategies on historical data (odds + model outputs).

- Entrypoints & Apps
  - `daily_bot.py` – end‑to‑end pipeline: fetch -> predict -> select -> build parlay -> stake -> save DB -> notify.
  - `app.py` (Streamlit) – UI for exploration/triggering runs.
  - `bot_real.py` – real betting flow, optionally invoking `TriunfoBetPlacer`.
  - `scheduler.py` – automation scheduling.

## Config Surface (`config/config.yaml`)
- `bankroll`: `initial`, `max_bet_percentage`, `kelly_fraction` (effective 1/4 Kelly in improved calculator), `stop_loss_percentage`.
- `picks`: thresholds `min_probability`, `min_edge`, `min_odds`, `max_odds`, `max_picks_per_league`.
- `parlay`: `min_picks`, `max_picks`, `min_total_odds`, `max_total_odds`.
- `paper_trading.enabled` and `duration_days`.

## Data Contracts (Quick Reference)
- Match (from scrapers): see `OddsAPIFetcher` above.
- Prediction: see `MatchPredictor` above.
- Pick (value selection): see `PickSelector` above.
- Parlay summary:
  - `{'picks':[Pick...], 'total_odds': float, 'combined_probability': float, 'edge': float, 'expected_value': float}`
- Bet (DB):
  - `bets` row uses: `bet_date, sport, bet_type, num_picks, total_odds, stake, potential_return, opening_odds, bankroll_before, notes, edge_at_recommendation, ...`

## Workflows (Commands)
- Train models: `python src/models/train_model.py`
- Run full pipeline: `python daily_bot.py`
- Streamlit UI: `streamlit run app.py`
- Test modules: run each file directly; most have `if __name__ == "__main__":` blocks.

## Conventions & Gotchas
- Odds use DECIMAL internally; convert to American only for display.
- Parlay total = product of decimal odds. Web boosts/promos aren’t modeled (could cause mismatch vs sportsbook).
- DB is the single source of truth for historical odds/results/features.
- Use `src/utils/logger.py` logging; avoid bare prints in production flows.
- Environment variables: `.env` with `ODDS_API_KEYS`, `TRIUNFOBET_USER`, `TRIUNFOBET_PASS`, Telegram tokens (optional).

## Extension Pointers
- Add a new strategy: implement in `src/betting/` and integrate in `daily_bot.py`.
- Add a new market/sport: extend `OddsAPIFetcher._fetch_sport_odds` and update feature engineering + models accordingly.
- Real betting: adjust selectors in `TriunfoBetPlacer` and switch `dry_run=False` once safe.

