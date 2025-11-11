"""
CLV Tracker - Closing Line Value Tracking
El mejor indicador de rentabilidad a largo plazo en apuestas deportivas
"""

from typing import Dict, List
from datetime import datetime
from loguru import logger
import sqlite3


class CLVTracker:
    """
    Rastrea el Closing Line Value (CLV) de tus apuestas
    
    CLV = (Closing Odds / Your Odds) - 1
    
    CLV positivo = Apostaste a mejores odds que el mercado al cierre
    CLV > 3% consistente = Eres un sharp bettor rentable
    """

    def __init__(self, db_path: str = "data/betting_history.db"):
        self.db_path = db_path
        self.conn = None
        self.create_clv_tables()

    def connect(self):
        """Conecta a la base de datos"""
        if self.conn is None:
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
        """Cierra conexión"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_clv_tables(self):
        """Crea tabla para trackear CLV"""
        self.connect()
        cursor = self.conn.cursor()

        # Extender tabla de bets para incluir CLV
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clv_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bet_id INTEGER,
                match_id TEXT,
                sport TEXT,
                opening_odds REAL,
                bet_odds REAL,
                closing_odds REAL,
                bet_time TEXT,
                closing_time TEXT,
                clv_percentage REAL,
                clv_dollars REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bet_id) REFERENCES bets (id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clv_bet_id ON clv_tracking(bet_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clv_match_id ON clv_tracking(match_id)
        """)

        self.conn.commit()
        logger.info("CLV tracking tables created/verified")

    def save_bet_odds(self, bet_id: int, match_id: str, sport: str, 
                      opening_odds: float, bet_odds: float):
        """
        Guarda las odds al momento de la apuesta

        Args:
            bet_id: ID de la apuesta
            match_id: ID del partido
            sport: Deporte
            opening_odds: Odds de apertura (primera captura)
            bet_odds: Odds al momento de apostar
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO clv_tracking (
                bet_id, match_id, sport, opening_odds, bet_odds, bet_time
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (bet_id, match_id, sport, opening_odds, bet_odds, datetime.now().isoformat()))

        self.conn.commit()
        logger.info(f"Saved bet odds for bet_id={bet_id}: opening={opening_odds}, bet={bet_odds}")

    def update_closing_odds(self, match_id: str, closing_odds: float):
        """
        Actualiza las odds de cierre y calcula CLV

        Args:
            match_id: ID del partido
            closing_odds: Odds finales antes del inicio del partido
        """
        self.connect()
        cursor = self.conn.cursor()

        # Obtener todos los bets de este match
        cursor.execute("""
            SELECT id, bet_id, bet_odds FROM clv_tracking 
            WHERE match_id = ? AND closing_odds IS NULL
        """, (match_id,))

        rows = cursor.fetchall()

        for row in rows:
            clv_id = row['id']
            bet_id = row['bet_id']
            bet_odds = row['bet_odds']

            # Calcular CLV
            clv_percentage = (closing_odds / bet_odds) - 1
            
            # CLV en dólares (asumiendo stake de $100 para comparación)
            clv_dollars = 100 * clv_percentage

            # Actualizar
            cursor.execute("""
                UPDATE clv_tracking
                SET closing_odds = ?,
                    closing_time = ?,
                    clv_percentage = ?,
                    clv_dollars = ?
                WHERE id = ?
            """, (closing_odds, datetime.now().isoformat(), clv_percentage, clv_dollars, clv_id))

            logger.info(f"CLV calculated for bet_id={bet_id}: "
                       f"bet_odds={bet_odds}, closing={closing_odds}, "
                       f"CLV={clv_percentage*100:.2f}%")

        self.conn.commit()

    def get_clv_stats(self, days: int = 30) -> Dict:
        """
        Obtiene estadísticas de CLV

        Args:
            days: Número de días hacia atrás

        Returns:
            Dict con estadísticas de CLV
        """
        self.connect()
        cursor = self.conn.cursor()

        # CLV promedio
        cursor.execute("""
            SELECT AVG(clv_percentage) as avg_clv,
                   COUNT(*) as total_bets,
                   SUM(CASE WHEN clv_percentage > 0 THEN 1 ELSE 0 END) as positive_clv_count,
                   MAX(clv_percentage) as max_clv,
                   MIN(clv_percentage) as min_clv
            FROM clv_tracking
            WHERE closing_odds IS NOT NULL
            AND datetime(created_at) >= datetime('now', '-' || ? || ' days')
        """, (days,))

        row = cursor.fetchone()

        if row['total_bets'] == 0:
            # Retornar estructura completa con ceros para evitar KeyError aguas arriba
            return {
                'avg_clv': 0.0,
                'avg_clv_percentage': 0.0,
                'total_bets': 0,
                'positive_clv_count': 0,
                'positive_clv_rate': 0.0,
                'max_clv': 0.0,
                'max_clv_percentage': 0.0,
                'min_clv': 0.0,
                'min_clv_percentage': 0.0
            }

        return {
            'avg_clv': row['avg_clv'] or 0,
            'avg_clv_percentage': (row['avg_clv'] or 0) * 100,
            'total_bets': row['total_bets'],
            'positive_clv_count': row['positive_clv_count'],
            'positive_clv_rate': (row['positive_clv_count'] / row['total_bets'] * 100) if row['total_bets'] > 0 else 0,
            'max_clv': row['max_clv'] or 0,
            'max_clv_percentage': (row['max_clv'] or 0) * 100,
            'min_clv': row['min_clv'] or 0,
            'min_clv_percentage': (row['min_clv'] or 0) * 100
        }

    def get_clv_history(self, limit: int = 50) -> List[Dict]:
        """
        Obtiene historial de CLV

        Args:
            limit: Número máximo de registros

        Returns:
            Lista de registros CLV
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM clv_tracking
            WHERE closing_odds IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def analyze_clv_performance(self) -> Dict:
        """
        Análisis profundo de performance CLV

        Returns:
            Análisis completo
        """
        stats = self.get_clv_stats(days=90)  # Últimos 90 días

        # Interpretar resultados
        interpretation = ""
        rating = ""
        # Manejo defensivo ante ausencia de datos/claves
        avg_clv = stats.get('avg_clv_percentage', 0.0)

        if avg_clv > 5:
            rating = "⭐⭐⭐⭐⭐ ELITE"
            interpretation = "CLV excepcional! Estás batiendo consistentemente al mercado."
        elif avg_clv > 3:
            rating = "⭐⭐⭐⭐ SHARP"
            interpretation = "Muy buen CLV. Eres un apostador con ventaja real."
        elif avg_clv > 1:
            rating = "⭐⭐⭐ BUENO"
            interpretation = "CLV positivo. Vas por buen camino."
        elif avg_clv > -1:
            rating = "⭐⭐ NEUTRO"
            interpretation = "CLV cercano a cero. Mejora la selección de odds."
        else:
            rating = "⭐ NEGATIVO"
            interpretation = "CLV negativo consistente. Revisa tu timing de apuestas."

        return {
            **stats,
            'rating': rating,
            'interpretation': interpretation
        }


if __name__ == "__main__":
    # Test del CLV Tracker
    tracker = CLVTracker()

    print("=== CLV Tracker Test ===\n")

    # Simular una apuesta
    bet_id = 1
    match_id = "TEST_MATCH_001"
    sport = "soccer"
    opening_odds = 2.00
    bet_odds = 2.10  # Apostamos a 2.10

    tracker.save_bet_odds(bet_id, match_id, sport, opening_odds, bet_odds)
    print(f"✅ Apuesta registrada: Odds {bet_odds}")

    # Simular closing odds (odds justo antes del partido)
    closing_odds = 1.95  # El mercado cerró en 1.95

    tracker.update_closing_odds(match_id, closing_odds)
    print(f"✅ Closing odds registradas: {closing_odds}")

    # Calcular CLV
    clv = (closing_odds / bet_odds) - 1
    print(f"\n📊 CLV: {clv*100:.2f}%")

    if clv > 0:
        print("✅ CLV POSITIVO - ¡Apostaste mejor que el mercado!")
    else:
        print("❌ CLV NEGATIVO - El mercado cerró con peores odds")

    # Estadísticas
    stats = tracker.get_clv_stats()
    print(f"\n📈 Estadísticas CLV:")
    print(f"  Total apuestas: {stats['total_bets']}")
    print(f"  CLV promedio: {stats['avg_clv_percentage']:.2f}%")
    print(f"  Tasa CLV positivo: {stats['positive_clv_rate']:.1f}%")

    # Análisis
    analysis = tracker.analyze_clv_performance()
    print(f"\n{analysis['rating']}")
    print(f"{analysis['interpretation']}")

    tracker.close()
