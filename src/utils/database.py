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
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

    def close(self):
        """Cierra conexión con la base de datos"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        """Crea las tablas necesarias si no existen"""
        self.connect()
        cursor = self.conn.cursor()

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

        self.conn.commit()
        logger.info("Database tables created/verified")

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
                stake, potential_return, bankroll_before, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bet_data.get('bet_date', datetime.now().isoformat()),
            bet_data.get('sport', 'mixed'),
            bet_data.get('bet_type', 'parlay'),
            bet_data.get('num_picks', len(picks)),
            bet_data.get('total_odds'),
            bet_data.get('stake'),
            bet_data.get('potential_return'),
            bet_data.get('bankroll_before'),
            bet_data.get('notes', '')
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
