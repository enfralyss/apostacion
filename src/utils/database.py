"""
Database manager - Maneja el almacenamiento de datos históricos y apuestas
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json
from loguru import logger
import os


class BettingDatabase:
    """Gestor de base de datos para el sistema de apuestas"""

    def __init__(self, db_path: str = "data/betting_history.db"):
        """
        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = None
        self.create_tables()

    def connect(self):
        """Establece conexión con la base de datos"""
        if self.conn is None:
            # Permitir uso seguro desde múltiples hilos (jobs/cron/streamlit callbacks)
            # Nota: SQLite no es full concurrent; por eso activamos WAL y usamos commits cortos.
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self.conn.row_factory = sqlite3.Row
            try:
                self.conn.execute("PRAGMA journal_mode=WAL;")
                self.conn.execute("PRAGMA synchronous=NORMAL;")
                self.conn.execute("PRAGMA foreign_keys=ON;")
            except Exception:
                pass

    def close(self):
        """Cierra conexión con la base de datos"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        """Crea las tablas necesarias si no existen"""
        self.connect()
        cursor = self.conn.cursor()
        # Tabla de parámetros clave-valor
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS parameters (
                param_name TEXT PRIMARY KEY,
                param_value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Historial de cambios de parámetros
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS parameter_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Tabla de apuestas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bet_date TEXT NOT NULL,
                sport TEXT NOT NULL,
                bet_type TEXT NOT NULL,
                num_picks INTEGER,
                total_odds REAL,
                stake REAL,
                potential_return REAL,
                opening_odds REAL,
                closing_odds REAL,
                clv_percentage REAL,
                placed_odds REAL,
                adjusted_stake REAL,
                edge_at_recommendation REAL,
                edge_at_placement REAL,
                status TEXT DEFAULT 'pending',
                result TEXT,
                profit_loss REAL,
                bankroll_before REAL,
                bankroll_after REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                settled_at TEXT,
                notes TEXT
            )
        ''')
        # Intentar agregar columnas nuevas si tabla ya existía
        for alter in [
            "ALTER TABLE bets ADD COLUMN opening_odds REAL",
            "ALTER TABLE bets ADD COLUMN closing_odds REAL",
            "ALTER TABLE bets ADD COLUMN clv_percentage REAL",
            "ALTER TABLE bets ADD COLUMN placed_odds REAL",
            "ALTER TABLE bets ADD COLUMN adjusted_stake REAL",
            "ALTER TABLE bets ADD COLUMN edge_at_recommendation REAL",
            "ALTER TABLE bets ADD COLUMN edge_at_placement REAL"
        ]:
            try:
                cursor.execute(alter)
            except Exception:
                pass

        # Tabla de picks individuales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bet_id INTEGER,
                match_id TEXT,
                sport TEXT,
                league TEXT,
                home_team TEXT,
                away_team TEXT,
                match_date TEXT,
                prediction TEXT,
                odds REAL,
                predicted_probability REAL,
                edge REAL,
                result TEXT,
                settled_at TEXT,
                result_source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bet_id) REFERENCES bets (id)
            )
        ''')

        # Tabla de bankroll histórico
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bankroll_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                bankroll REAL NOT NULL,
                change REAL,
                change_percentage REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de performance metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_bets INTEGER,
                wins INTEGER,
                losses INTEGER,
                pending INTEGER,
                win_rate REAL,
                roi REAL,
                profit_loss REAL,
                avg_odds REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Snapshot de odds crudas provenientes de la API
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_odds_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT,
                sport TEXT,
                league TEXT,
                home_team TEXT,
                away_team TEXT,
                match_date TEXT,
                snapshot_time TEXT DEFAULT CURRENT_TIMESTAMP,
                bookmakers_count INTEGER,
                home_win_odds REAL,
                away_win_odds REAL,
                draw_odds REAL,
                source TEXT DEFAULT 'the_odds_api'
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_odds_match ON raw_odds_snapshots(match_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_odds_snapshot_time ON raw_odds_snapshots(snapshot_time)')

        # Resultados finales del partido (stub: se puede ampliar con marcadores)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_match_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT,
                sport TEXT,
                league TEXT,
                home_team TEXT,
                away_team TEXT,
                match_date TEXT,
                result_label TEXT,  -- 'home_win','away_win','draw'
                home_score INTEGER,
                away_score INTEGER,
                result_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_match ON raw_match_results(match_id)')

        # Odds canónicas (último snapshot antes de inicio + sin margen)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS canonical_odds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT UNIQUE,
                sport TEXT,
                league TEXT,
                home_team TEXT,
                away_team TEXT,
                match_date TEXT,
                snapshot_time TEXT,
                home_win_odds REAL,
                away_win_odds REAL,
                draw_odds REAL,
                implied_home REAL,
                implied_away REAL,
                implied_draw REAL,
                margin REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_canonical_match ON canonical_odds(match_id)')

        # Features ingenierizados por partido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engineered_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT UNIQUE,
                sport TEXT,
                league TEXT,
                home_team TEXT,
                away_team TEXT,
                match_date TEXT,
                win_pct_home_last5 REAL,
                win_pct_away_last5 REAL,
                rest_days_home REAL,
                rest_days_away REAL,
                avg_home_odds_last5 REAL,
                avg_away_odds_last5 REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feat_match ON engineered_features(match_id)')

        self.conn.commit()
        logger.info("Database tables created/verified")

    # --- Parámetros clave-valor ---
    def _parse_param_value(self, value: str):
        try:
            if value.lower() in ("true", "false"):
                return value.lower() == "true"
            if value.isdigit():
                return int(value)
            if any(ch.isdigit() for ch in value) and value.count('.') == 1:
                return float(value)
            return value
        except Exception:
            return value

    def get_parameter(self, name: str, default=None):
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('SELECT param_value FROM parameters WHERE param_name=?', (name,))
        row = cursor.fetchone()
        if row:
            return self._parse_param_value(row['param_value'])
        return default

    def set_parameter(self, name: str, value):
        """Inserta o actualiza un parámetro y registra el cambio en el historial si difiere del anterior."""
        self.connect()
        cursor = self.conn.cursor()
        value_str = str(value)
        # Obtener valor previo
        cursor.execute('SELECT param_value FROM parameters WHERE param_name=?', (name,))
        prev = cursor.fetchone()
        old_value = prev['param_value'] if prev else None
        cursor.execute(
            '''INSERT INTO parameters (param_name, param_value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(param_name) DO UPDATE SET param_value=excluded.param_value, updated_at=CURRENT_TIMESTAMP''',
            (name, value_str)
        )
        # Registrar historial si cambió
        if old_value is not None and old_value != value_str:
            cursor.execute('INSERT INTO parameter_history (name, old_value, new_value) VALUES (?,?,?)', (name, old_value, value_str))
        self.conn.commit()
        logger.info(f"Parameter '{name}' set to {value_str} (old={old_value})")

    def get_all_parameters(self):
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('SELECT param_name, param_value, updated_at FROM parameters')
        rows = cursor.fetchall()
        out = []
        for r in rows:
            out.append({'name': r['param_name'], 'value': self._parse_param_value(r['param_value']), 'updated_at': r['updated_at']})
        return out

    def get_parameter_history(self, limit: int = 50):
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''SELECT name, old_value, new_value, changed_at FROM parameter_history ORDER BY changed_at DESC LIMIT ?''', (limit,))
        return [dict(r) for r in cursor.fetchall()]

    def save_bet(self, bet_data: Dict, picks: List[Dict]) -> int:
        """
        Guarda una apuesta en la base de datos

        Args:
            bet_data: Datos de la apuesta
            picks: Lista de picks de la apuesta

        Returns:
            ID de la apuesta guardada
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO bets (
                bet_date, sport, bet_type, num_picks, total_odds,
                stake, potential_return, opening_odds, bankroll_before, notes,
                edge_at_recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bet_data.get('bet_date', datetime.now().isoformat()),
            bet_data.get('sport', 'mixed'),
            bet_data.get('bet_type', 'parlay'),
            bet_data.get('num_picks', len(picks)),
            bet_data.get('total_odds'),
            bet_data.get('stake'),
            bet_data.get('potential_return'),
            bet_data.get('opening_odds', bet_data.get('total_odds')),  # abrir con total actual
            bet_data.get('bankroll_before'),
            bet_data.get('notes', ''),
            bet_data.get('edge_at_recommendation')
        ))

        bet_id = cursor.lastrowid

        # Guardar picks individuales
        for pick in picks:
            cursor.execute('''
                INSERT INTO picks (
                    bet_id, match_id, sport, league, home_team, away_team,
                    match_date, prediction, odds, predicted_probability, edge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bet_id,
                pick.get('match_id'),
                pick.get('sport'),
                pick.get('league'),
                pick.get('home_team'),
                pick.get('away_team'),
                pick.get('match_date'),
                pick.get('prediction'),
                pick.get('odds'),
                pick.get('predicted_probability'),
                pick.get('edge')
            ))

        self.conn.commit()
        logger.info(f"Bet saved with ID: {bet_id}")

        return bet_id

    def update_bet_result(self, bet_id: int, result: str, profit_loss: float,
                         bankroll_after: float):
        """
        Actualiza el resultado de una apuesta

        Args:
            bet_id: ID de la apuesta
            result: 'won', 'lost', 'push'
            profit_loss: Ganancia/pérdida
            bankroll_after: Bankroll después de la apuesta
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE bets
            SET status = 'settled',
                result = ?,
                profit_loss = ?,
                bankroll_after = ?,
                settled_at = ?
            WHERE id = ?
        ''', (result, profit_loss, bankroll_after, datetime.now().isoformat(), bet_id))

        self.conn.commit()
        logger.info(f"Bet {bet_id} updated: {result}, P/L: ${profit_loss:.2f}")

    def update_pick_result(self, pick_id: int, final_result: str, source: str = 'raw_match_results') -> Optional[Dict]:
        """Actualiza el resultado de un pick individual y si todos los picks del bet están resueltos, liquida la apuesta.

        Args:
            pick_id: ID del pick
            final_result: 'won' | 'lost'
            source: origen del resultado (para auditoría)

        Returns:
            Dict con info del pick y estado del bet tras actualización o None si error
        """
        try:
            self.connect()
            c = self.conn.cursor()
            # Recuperar pick y bet asociado
            c.execute('SELECT id, bet_id, prediction, odds, edge FROM picks WHERE id=?', (pick_id,))
            prow = c.fetchone()
            if not prow:
                logger.warning(f"Pick {pick_id} no encontrado")
                return None
            bet_id = prow['bet_id']
            # Marcar pick
            c.execute('''UPDATE picks SET result=?, settled_at=?, result_source=? WHERE id=?''', (
                final_result, datetime.now().isoformat(), source, pick_id
            ))
            # Verificar si todos los picks están resueltos
            c.execute('SELECT result FROM picks WHERE bet_id=?', (bet_id,))
            all_results = [r['result'] for r in c.fetchall()]
            pending_left = any(r is None or r == '' for r in all_results)
            bet_settled = False
            bet_result = None
            profit_loss = 0.0
            bankroll_after = None
            if not pending_left:
                # Calcular resultado del parlay: gana si todos ganaron
                all_won = all(r == 'won' for r in all_results)
                bet_result = 'won' if all_won else 'lost'
                # Obtener stake y total_odds
                c.execute('SELECT stake, total_odds, bankroll_before FROM bets WHERE id=?', (bet_id,))
                brow = c.fetchone()
                if brow:
                    stake = brow['stake'] or 0
                    total_odds = brow['total_odds'] or 0
                    bankroll_before = brow['bankroll_before'] or 0
                    if bet_result == 'won':
                        profit_loss = stake * (total_odds - 1)
                    else:
                        profit_loss = -stake
                    bankroll_after = bankroll_before + profit_loss
                    self.update_bet_result(bet_id, bet_result, profit_loss, bankroll_after)
                    bet_settled = True
            self.conn.commit()
            info = {
                'pick_id': pick_id,
                'bet_id': bet_id,
                'pick_result': final_result,
                'bet_settled': bet_settled,
                'bet_result': bet_result,
                'profit_loss': profit_loss,
                'bankroll_after': bankroll_after
            }
            return info
        except Exception as e:
            logger.error(f"Error actualizando pick {pick_id}: {e}")
            return None

    def resolve_pending_picks(self) -> List[Dict]:
        """Resuelve picks pendientes comparando su match_id con raw_match_results.
        Retorna lista de dicts con info de picks actualizados.
        """
        self.connect()
        c = self.conn.cursor()
        # Obtener picks sin resultado
        c.execute('SELECT id, match_id, prediction FROM picks WHERE result IS NULL OR result=""')
        picks = c.fetchall()
        if not picks:
            return []
        resolved = []
        for p in picks:
            match_id = p['match_id']
            c.execute('SELECT result_label FROM raw_match_results WHERE match_id=?', (match_id,))
            row = c.fetchone()
            if not row:
                continue
            actual = row['result_label']
            prediction = p['prediction']
            pick_outcome = 'won' if actual == prediction else 'lost'
            info = self.update_pick_result(p['id'], pick_outcome)
            if info:
                resolved.append(info)
        return resolved

    def update_bet_closing_odds(self, bet_id: int, closing_odds: float):
        """Actualiza closing odds y calcula CLV%"""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('SELECT opening_odds FROM bets WHERE id=?', (bet_id,))
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Bet {bet_id} not found for closing odds update")
            return False
        opening_odds = row['opening_odds'] or 0
        if opening_odds <= 0:
            logger.warning(f"Opening odds invalid for bet {bet_id}")
            return False
        clv_pct = (closing_odds / opening_odds) - 1
        cursor.execute('''
            UPDATE bets SET closing_odds=?, clv_percentage=? WHERE id=?
        ''', (closing_odds, clv_pct, bet_id))
        self.conn.commit()
        logger.info(f"Bet {bet_id} CLV updated: closing={closing_odds} clv={clv_pct*100:.2f}%")
        return True

    def update_bet_placement(self, bet_id: int, placed_odds: float, combined_probability: Optional[float] = None) -> Optional[Dict]:
        """Registra las odds reales a las que se colocó la apuesta y recalcula stake y edge.

        Args:
            bet_id: ID de la apuesta
            placed_odds: Cuota final obtenida en la casa al colocar
            combined_probability: Probabilidad combinada del parlay (si None se calcula con picks)

        Returns:
            Dict con info actualizada (placed_odds, adjusted_stake, edge_at_placement, stake_diff) o None si error
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute('SELECT total_odds, stake, edge_at_recommendation FROM bets WHERE id=?', (bet_id,))
            bet_row = cursor.fetchone()
            if not bet_row:
                logger.warning(f"Bet {bet_id} not found for placement update")
                return None
            recommended_odds = bet_row['total_odds']
            original_stake = bet_row['stake']
            edge_recommendation = bet_row['edge_at_recommendation']

            # Obtener probabilidad combinada si no viene
            if combined_probability is None:
                picks = self.get_bet_picks(bet_id)
                combined_probability = 1.0
                for p in picks:
                    combined_probability *= p.get('predicted_probability', 0)

            if placed_odds <= 1.0:
                logger.warning("Placed odds inválidas")
                return None

            implied_prob_placement = 1 / placed_odds
            edge_placement = combined_probability - implied_prob_placement

            # Recalcular stake usando Kelly fraccional del StakeCalculator
            try:
                from src.betting.stake_calculator import StakeCalculator
                sc = StakeCalculator()
                stake_info = sc.calculate_recommended_stake(
                    probability=combined_probability,
                    odds=placed_odds,
                    bankroll= self.get_latest_bankroll() or 0,
                    strategy='kelly'
                )
                adjusted_stake = stake_info['recommended_stake']
            except Exception as e:
                logger.warning(f"Kelly recalculation failed: {e}")
                adjusted_stake = original_stake

            stake_diff = adjusted_stake - original_stake

            cursor.execute('''
                UPDATE bets SET placed_odds=?, adjusted_stake=?, edge_at_placement=? WHERE id=?
            ''', (placed_odds, adjusted_stake, edge_placement, bet_id))
            self.conn.commit()
            logger.info(f"Bet {bet_id} placement recorded. Odds {placed_odds:.2f} (was {recommended_odds:.2f}), edge rec {edge_recommendation:.4f} -> placement {edge_placement:.4f}, stake adj {original_stake:.2f} -> {adjusted_stake:.2f}")
            return {
                'bet_id': bet_id,
                'placed_odds': placed_odds,
                'adjusted_stake': adjusted_stake,
                'edge_at_placement': edge_placement,
                'edge_at_recommendation': edge_recommendation,
                'stake_diff': stake_diff,
                'recommended_odds': recommended_odds
            }
        except Exception as e:
            logger.error(f"Error updating bet placement: {e}")
            return None

    def get_latest_bankroll(self) -> Optional[float]:
        """Retorna el último bankroll registrado (si existe)"""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('SELECT bankroll FROM bankroll_history ORDER BY created_at DESC LIMIT 1')
        row = cursor.fetchone()
        return row['bankroll'] if row else None

    def get_recent_bets(self, limit: int = 20) -> List[Dict]:
        """Obtiene las últimas apuestas"""
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM bets
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        bets = [dict(row) for row in rows]

        return bets

    def get_bet_picks(self, bet_id: int) -> List[Dict]:
        """Obtiene los picks de una apuesta específica"""
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM picks
            WHERE bet_id = ?
        ''', (bet_id,))

        rows = cursor.fetchall()
        picks = [dict(row) for row in rows]

        return picks

    def calculate_performance_metrics(self) -> Dict:
        """Calcula métricas de performance"""
        self.connect()
        cursor = self.conn.cursor()

        # Total de apuestas
        cursor.execute("SELECT COUNT(*) as total FROM bets WHERE status = 'settled'")
        total_bets = cursor.fetchone()['total']

        # Victorias
        cursor.execute("SELECT COUNT(*) as wins FROM bets WHERE result = 'won'")
        wins = cursor.fetchone()['wins']

        # Derrotas
        cursor.execute("SELECT COUNT(*) as losses FROM bets WHERE result = 'lost'")
        losses = cursor.fetchone()['losses']

        # Pendientes
        cursor.execute("SELECT COUNT(*) as pending FROM bets WHERE status = 'pending'")
        pending = cursor.fetchone()['pending']

        # Profit/Loss total
        cursor.execute("SELECT SUM(profit_loss) as total_pl FROM bets WHERE status = 'settled'")
        total_pl = cursor.fetchone()['total_pl'] or 0

        # Monto total apostado
        cursor.execute("SELECT SUM(stake) as total_staked FROM bets WHERE status = 'settled'")
        total_staked = cursor.fetchone()['total_staked'] or 0

        # Calcular métricas
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        roi = (total_pl / total_staked * 100) if total_staked > 0 else 0

        # Odds promedio
        cursor.execute("SELECT AVG(total_odds) as avg_odds FROM bets WHERE status = 'settled'")
        avg_odds = cursor.fetchone()['avg_odds'] or 0

        metrics = {
            'total_bets': total_bets,
            'wins': wins,
            'losses': losses,
            'pending': pending,
            'win_rate': win_rate,
            'roi': roi,
            'total_profit_loss': total_pl,
            'total_staked': total_staked,
            'avg_odds': avg_odds
        }

        return metrics

    def save_bankroll_snapshot(self, bankroll: float, change: float = 0, notes: str = ""):
        """Guarda un snapshot del bankroll"""
        self.connect()
        cursor = self.conn.cursor()

        change_pct = (change / (bankroll - change) * 100) if bankroll - change > 0 else 0

        cursor.execute('''
            INSERT INTO bankroll_history (date, bankroll, change, change_percentage, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), bankroll, change, change_pct, notes))

        self.conn.commit()

    def get_bankroll_history(self, days: int = 30) -> List[Dict]:
        """Obtiene historial de bankroll"""
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM bankroll_history
            ORDER BY created_at DESC
            LIMIT ?
        ''', (days,))

        rows = cursor.fetchall()
        history = [dict(row) for row in rows]

        return history

    # ------------------ INGESTION & NORMALIZATION ------------------ #

    def save_odds_snapshot(self, matches: List[Dict]):
        """Guarda un snapshot de odds provenientes de la API.

        Args:
            matches: lista de dicts devueltos por OddsAPIFetcher.get_available_matches
        """
        if not matches:
            return 0
        self.connect()
        cursor = self.conn.cursor()
        inserted = 0
        for m in matches:
            try:
                odds = m.get('odds', {})
                cursor.execute('''
                    INSERT INTO raw_odds_snapshots (
                        match_id,sport,league,home_team,away_team,match_date,bookmakers_count,
                        home_win_odds,away_win_odds,draw_odds,source
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    m.get('match_id'), m.get('sport'), m.get('league'), m.get('home_team'), m.get('away_team'),
                    m.get('match_date'), m.get('bookmakers_count', 0),
                    odds.get('home_win'), odds.get('away_win'), odds.get('draw'), 'the_odds_api'
                ))
                inserted += 1
            except Exception as e:
                logger.warning(f"No se pudo insertar snapshot para match {m.get('match_id')}: {e}")
        self.conn.commit()
        logger.info(f"Inserted {inserted} raw odds snapshots")
        return inserted

    def save_match_result(self, result: Dict):
        """Guarda resultado final del partido (stub para integración real)."""
        self.connect()
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO raw_match_results (
                    match_id,sport,league,home_team,away_team,match_date,
                    result_label,home_score,away_score
                ) VALUES (?,?,?,?,?,?,?,?,?)
            ''', (
                result.get('match_id'), result.get('sport'), result.get('league'), result.get('home_team'),
                result.get('away_team'), result.get('match_date'), result.get('result_label'),
                result.get('home_score'), result.get('away_score')
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error guardando resultado: {e}")

    def build_canonical_odds_for_match(self, match_id: str):
        """Construye odds canónicas tomando el último snapshot previo al inicio y removiendo margen.

        Si ya existen odds canónicas para el match se omite.
        """
        self.connect()
        cursor = self.conn.cursor()
        # Verificar existencia
        cursor.execute('SELECT 1 FROM canonical_odds WHERE match_id=?', (match_id,))
        if cursor.fetchone():
            return False
        # Obtener snapshots ordenados por tiempo descendente
        cursor.execute('''
            SELECT * FROM raw_odds_snapshots WHERE match_id=? ORDER BY snapshot_time DESC
        ''', (match_id,))
        row = cursor.fetchone()
        if not row:
            return False
        # Calcular implied probabilities y margen
        home_odds = row['home_win_odds']
        away_odds = row['away_win_odds']
        draw_odds = row['draw_odds']
        implied_home = 1/home_odds if home_odds else 0
        implied_away = 1/away_odds if away_odds else 0
        implied_draw = 1/draw_odds if draw_odds else 0
        margin = implied_home + implied_away + implied_draw
        if margin == 0:
            logger.warning(f"Margen cero para {match_id}, odds inválidas")
            return False
        # Normalizar (remover margen)
        implied_home_n = implied_home / margin
        implied_away_n = implied_away / margin
        implied_draw_n = implied_draw / margin if draw_odds else None
        cursor.execute('''
            INSERT INTO canonical_odds (
                match_id,sport,league,home_team,away_team,match_date,snapshot_time,
                home_win_odds,away_win_odds,draw_odds,implied_home,implied_away,implied_draw,margin
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            row['match_id'], row['sport'], row['league'], row['home_team'], row['away_team'], row['match_date'],
            row['snapshot_time'], home_odds, away_odds, draw_odds,
            implied_home_n, implied_away_n, implied_draw_n, margin
        ))
        self.conn.commit()
        return True

    def build_canonical_odds_bulk(self):
        """Construye odds canónicas para todos los partidos que aún no las tengan."""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''SELECT DISTINCT match_id FROM raw_odds_snapshots''')
        match_ids = [r['match_id'] for r in cursor.fetchall()]
        built = 0
        for mid in match_ids:
            if self.build_canonical_odds_for_match(mid):
                built += 1
        logger.info(f"Canonical odds built for {built} matches")
        return built

    def build_basic_features(self):
        """Ingeniería de características simple basada en últimos 5 partidos y días de descanso.
        Para MVP: usa resultados y canonical_odds ya almacenados.
        """
        self.connect()
        cursor = self.conn.cursor()
        # Obtener lista de partidos ordenados por fecha
        cursor.execute('''SELECT match_id, sport, league, home_team, away_team, match_date FROM canonical_odds ORDER BY match_date ASC''')
        rows = [dict(r) for r in cursor.fetchall()]
        inserted = 0
        for r in rows:
            mid = r['match_id']
            # Skip si ya existe
            cursor.execute('SELECT 1 FROM engineered_features WHERE match_id=?', (mid,))
            if cursor.fetchone():
                continue
            # Últimos 5 partidos home
            cursor.execute('''SELECT result_label FROM raw_match_results WHERE home_team=? OR away_team=? ORDER BY match_date DESC LIMIT 5''', (r['home_team'], r['home_team']))
            recent_home = [x['result_label'] for x in cursor.fetchall()]
            cursor.execute('''SELECT result_label FROM raw_match_results WHERE home_team=? OR away_team=? ORDER BY match_date DESC LIMIT 5''', (r['away_team'], r['away_team']))
            recent_away = [x['result_label'] for x in cursor.fetchall()]
            def win_pct(team_results, team_name):
                if not team_results:
                    return 0.0
                wins = 0
                for lab in team_results:
                    if lab == 'home_win' and team_name == 'home':
                        wins += 1
                    if lab == 'away_win' and team_name == 'away':
                        wins += 1
                return wins/len(team_results)
            win_pct_home = win_pct(recent_home, 'home')
            win_pct_away = win_pct(recent_away, 'away')
            # Rest days (stub: diferencia fija)
            rest_home = 3.0  # Placeholder
            rest_away = 3.0
            # Average odds last5
            cursor.execute('''SELECT home_win_odds FROM canonical_odds WHERE home_team=? ORDER BY match_date DESC LIMIT 5''', (r['home_team'],))
            avg_home_odds_rows = [x['home_win_odds'] for x in cursor.fetchall() if x['home_win_odds']]
            cursor.execute('''SELECT away_win_odds FROM canonical_odds WHERE away_team=? ORDER BY match_date DESC LIMIT 5''', (r['away_team'],))
            avg_away_odds_rows = [x['away_win_odds'] for x in cursor.fetchall() if x['away_win_odds']]
            avg_home_odds = sum(avg_home_odds_rows)/len(avg_home_odds_rows) if avg_home_odds_rows else None
            avg_away_odds = sum(avg_away_odds_rows)/len(avg_away_odds_rows) if avg_away_odds_rows else None
            cursor.execute('''INSERT INTO engineered_features (match_id,sport,league,home_team,away_team,match_date,win_pct_home_last5,win_pct_away_last5,rest_days_home,rest_days_away,avg_home_odds_last5,avg_away_odds_last5) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (
                mid,r['sport'],r['league'],r['home_team'],r['away_team'],r['match_date'],win_pct_home,win_pct_away,rest_home,rest_away,avg_home_odds,avg_away_odds
            ))
            inserted += 1
        self.conn.commit()
        logger.info(f"Inserted engineered features for {inserted} matches")
        return inserted

    def build_training_dataset(self, min_rows: int = 50):
        """Construye dataset de entrenamiento juntando canonical_odds + resultados + features.
        Retorna DataFrame listo o None si insuficiente.
        """
        import pandas as pd
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.match_id, c.sport, c.league, c.home_team, c.away_team, c.match_date,
                   c.home_win_odds, c.away_win_odds, c.draw_odds, c.implied_home, c.implied_away, c.implied_draw,
                   f.win_pct_home_last5, f.win_pct_away_last5, f.rest_days_home, f.rest_days_away,
                   f.avg_home_odds_last5, f.avg_away_odds_last5, r.result_label
            FROM canonical_odds c
            JOIN engineered_features f ON c.match_id=f.match_id
            JOIN raw_match_results r ON c.match_id=r.match_id
        ''')
        rows = cursor.fetchall()
        if not rows or len(rows) < min_rows:
            logger.warning("Dataset real insuficiente, usar fallback sintético.")
            return None
        df = pd.DataFrame([dict(r) for r in rows])
        # Limpiar NAs simples
        df = df.fillna(0)
        # Mapear resultado a columna 'result'
        df = df.rename(columns={'result_label': 'result'})
        logger.info(f"Training dataset real construido con {len(df)} filas")
        return df

    # ------------------ ODDS HELPERS PARA CLV ------------------ #

    def get_opening_odds_for_match(self, match_id: str, prediction: str) -> Optional[float]:
        """Obtiene las primeras odds registradas para el partido según el tipo de pick.
        prediction: 'home_win' | 'away_win' | 'draw'
        """
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''SELECT home_win_odds, away_win_odds, draw_odds FROM raw_odds_snapshots
                          WHERE match_id=? ORDER BY snapshot_time ASC LIMIT 1''', (match_id,))
        row = cursor.fetchone()
        if not row:
            return None
        if prediction == 'home_win':
            return row['home_win_odds']
        if prediction == 'away_win':
            return row['away_win_odds']
        if prediction == 'draw':
            return row['draw_odds']
        return None

    def get_latest_odds_for_match(self, match_id: str, prediction: str) -> Optional[float]:
        """Obtiene las últimas odds snapshot para el partido según tipo de pick."""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''SELECT home_win_odds, away_win_odds, draw_odds FROM raw_odds_snapshots
                          WHERE match_id=? ORDER BY snapshot_time DESC LIMIT 1''', (match_id,))
        row = cursor.fetchone()
        if not row:
            return None
        if prediction == 'home_win':
            return row['home_win_odds']
        if prediction == 'away_win':
            return row['away_win_odds']
        if prediction == 'draw':
            return row['draw_odds']
        return None

    def get_pending_bets(self) -> List[Dict]:
        """Devuelve apuestas pendientes (sin resultado)"""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bets WHERE status='pending'")
        return [dict(r) for r in cursor.fetchall()]

    def get_picks_for_bet(self, bet_id: int) -> List[Dict]:
        return self.get_bet_picks(bet_id)

    def calculate_match_features(self, match: Dict) -> Optional[Dict]:
        """
        Calcula features para un partido nuevo usando datos históricos de la DB.
        Retorna dict con las mismas features que usa el modelo entrenado.

        Args:
            match: Dict con 'home_team', 'away_team', 'sport', 'league', 'odds' (dict con home_win, away_win, draw)

        Returns:
            Dict con features o None si no hay suficientes datos históricos
        """
        self.connect()
        cursor = self.conn.cursor()

        home_team = match['home_team']
        away_team = match['away_team']
        sport = match.get('sport', 'soccer')
        odds = match.get('odds', {})

        # Features basados en odds actuales
        home_win_odds = odds.get('home_win', 0)
        away_win_odds = odds.get('away_win', 0)
        draw_odds = odds.get('draw', 0)

        if home_win_odds == 0 or away_win_odds == 0:
            logger.warning(f"Missing odds for {home_team} vs {away_team}")
            return None

        # Implied probabilities
        implied_home = 1 / home_win_odds if home_win_odds > 0 else 0
        implied_away = 1 / away_win_odds if away_win_odds > 0 else 0
        implied_draw = 1 / draw_odds if draw_odds > 0 else 0

        # Win percentage last 5 matches (from historical results)
        cursor.execute('''
            SELECT result_label FROM raw_match_results
            WHERE (home_team=? OR away_team=?)
            ORDER BY match_date DESC LIMIT 5
        ''', (home_team, home_team))
        recent_home = [row['result_label'] for row in cursor.fetchall()]

        cursor.execute('''
            SELECT result_label FROM raw_match_results
            WHERE (home_team=? OR away_team=?)
            ORDER BY match_date DESC LIMIT 5
        ''', (away_team, away_team))
        recent_away = [row['result_label'] for row in cursor.fetchall()]

        def calculate_win_pct(results, is_home_team=True):
            """Calculate win percentage for a team from their last results"""
            if not results:
                return 0.5  # Default if no history
            wins = 0
            for result in results:
                if is_home_team and result == 'home_win':
                    wins += 1
                elif not is_home_team and result == 'away_win':
                    wins += 1
            return wins / len(results) if results else 0.5

        win_pct_home_last5 = calculate_win_pct(recent_home, is_home_team=True)
        win_pct_away_last5 = calculate_win_pct(recent_away, is_home_team=False)

        # Rest days (placeholder - we don't have actual match dates history yet)
        rest_days_home = 3.0
        rest_days_away = 3.0

        # Average odds last 5 matches
        cursor.execute('''
            SELECT home_win_odds FROM canonical_odds
            WHERE home_team=?
            ORDER BY match_date DESC LIMIT 5
        ''', (home_team,))
        avg_home_odds_rows = [row['home_win_odds'] for row in cursor.fetchall() if row['home_win_odds']]

        cursor.execute('''
            SELECT away_win_odds FROM canonical_odds
            WHERE away_team=?
            ORDER BY match_date DESC LIMIT 5
        ''', (away_team,))
        avg_away_odds_rows = [row['away_win_odds'] for row in cursor.fetchall() if row['away_win_odds']]

        avg_home_odds_last5 = sum(avg_home_odds_rows) / len(avg_home_odds_rows) if avg_home_odds_rows else home_win_odds
        avg_away_odds_last5 = sum(avg_away_odds_rows) / len(avg_away_odds_rows) if avg_away_odds_rows else away_win_odds

        features = {
            'home_win_odds': home_win_odds,
            'away_win_odds': away_win_odds,
            'draw_odds': draw_odds,
            'implied_home': implied_home,
            'implied_away': implied_away,
            'implied_draw': implied_draw,
            'win_pct_home_last5': win_pct_home_last5,
            'win_pct_away_last5': win_pct_away_last5,
            'rest_days_home': rest_days_home,
            'rest_days_away': rest_days_away,
            'avg_home_odds_last5': avg_home_odds_last5,
            'avg_away_odds_last5': avg_away_odds_last5
        }

        return features


if __name__ == "__main__":
    # Test de la base de datos
    db = BettingDatabase()

    print("=== Testing Database ===\n")

    # Guardar una apuesta de ejemplo
    bet_data = {
        'bet_date': datetime.now().isoformat(),
        'sport': 'mixed',
        'bet_type': 'parlay',
        'total_odds': 12.38,
        'stake': 95.0,
        'potential_return': 1176.10,
        'bankroll_before': 5000.0,
        'notes': 'Test bet'
    }

    picks = [
        {
            'match_id': 'SOC001',
            'sport': 'soccer',
            'league': 'La Liga',
            'home_team': 'Real Madrid',
            'away_team': 'Barcelona',
            'match_date': datetime.now().isoformat(),
            'prediction': 'home_win',
            'odds': 1.85,
            'predicted_probability': 0.712,
            'edge': 0.083
        }
    ]

    bet_id = db.save_bet(bet_data, picks)
    print(f"Saved bet with ID: {bet_id}")

    # Obtener apuestas recientes
    recent_bets = db.get_recent_bets(5)
    print(f"\nRecent bets: {len(recent_bets)}")

    # Calcular métricas
    metrics = db.calculate_performance_metrics()
    print(f"\nPerformance Metrics:")
    print(f"  Total Bets: {metrics['total_bets']}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  ROI: {metrics['roi']:.1f}%")

    db.close()
