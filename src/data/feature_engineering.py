"""
Advanced Feature Engineering for Betting Models
CRÍTICO: TIME-AWARE - Sin data leakage - solo usa datos del pasado
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from loguru import logger


class AdvancedFeatureEngine:
    """
    Motor de feature engineering avanzado con:
    - ELO Rating dinámico
    - Form con decay exponencial
    - H2H profundo
    - Market efficiency signals
    """

    def __init__(self, db, initial_elo: int = 1500, k_factor: int = 32):
        """
        Args:
            db: BettingDatabase instance
            initial_elo: ELO inicial para equipos nuevos
            k_factor: Factor K para actualización de ELO (16-40, típico 32)
        """
        self.db = db
        self.initial_elo = initial_elo
        self.k_factor = k_factor

        # Cache de ELOs por equipo (se actualiza dinámicamente)
        self.elo_cache = {}

    def calculate_elo_rating(
        self,
        team: str,
        sport: str,
        before_date: datetime,
        league: Optional[str] = None
    ) -> float:
        """
        Calcula ELO rating de un equipo en una fecha específica
        TIME-AWARE: Solo considera partidos ANTES de la fecha

        Args:
            team: Nombre del equipo
            sport: Deporte (soccer/nba)
            before_date: Fecha límite (solo partidos antes de esta)
            league: Liga específica (opcional, para league-specific ELO)

        Returns:
            ELO rating del equipo
        """
        # Cache key
        cache_key = f"{team}_{sport}_{before_date.date()}"
        if cache_key in self.elo_cache:
            return self.elo_cache[cache_key]

        # Obtener histórico del equipo
        self.db.connect()
        cursor = self.db.conn.cursor()

        query = """
        SELECT
            r.home_team, r.away_team, r.result_label, r.match_date
        FROM raw_match_results r
        WHERE r.sport = ?
        AND (r.home_team = ? OR r.away_team = ?)
        AND datetime(r.match_date) < datetime(?)
        ORDER BY r.match_date ASC
        """

        params = [sport, team, team, before_date.isoformat()]

        if league:
            query = query.replace("WHERE r.sport", "WHERE r.league = ? AND r.sport")
            params = [league] + params

        cursor.execute(query, params)
        matches = cursor.fetchall()

        # Inicializar ELO
        elo = self.initial_elo

        # Actualizar ELO partido por partido
        for match in matches:
            is_home = match['home_team'] == team
            opponent = match['away_team'] if is_home else match['home_team']
            result = match['result_label']

            # Determinar score del equipo (1.0 = win, 0.5 = draw, 0.0 = loss)
            if is_home:
                if result == 'home_win':
                    score = 1.0
                elif result == 'draw':
                    score = 0.5
                else:
                    score = 0.0
            else:
                if result == 'away_win':
                    score = 1.0
                elif result == 'draw':
                    score = 0.5
                else:
                    score = 0.0

            # ELO del oponente (simplificación: usar ELO inicial)
            # En implementación completa: calcular ELO del oponente recursivamente
            opponent_elo = self.initial_elo

            # Expected score según ELO
            expected = 1 / (1 + 10 ** ((opponent_elo - elo) / 400))

            # Actualizar ELO
            elo = elo + self.k_factor * (score - expected)

        # Guardar en cache
        self.elo_cache[cache_key] = elo

        return elo

    def calculate_form_with_decay(
        self,
        team: str,
        sport: str,
        before_date: datetime,
        n_matches: int = 5
    ) -> float:
        """
        Calcula form reciente con decay exponencial
        Partidos más recientes pesan más

        Args:
            team: Nombre del equipo
            sport: Deporte
            before_date: Fecha límite
            n_matches: Número de partidos a considerar

        Returns:
            Form score (0.0-1.0, 1.0 = forma perfecta)
        """
        # Obtener últimos N partidos del equipo
        self.db.connect()
        cursor = self.db.conn.cursor()

        cursor.execute("""
        SELECT
            r.home_team, r.away_team, r.result_label
        FROM raw_match_results r
        WHERE r.sport = ?
        AND (r.home_team = ? OR r.away_team = ?)
        AND datetime(r.match_date) < datetime(?)
        ORDER BY r.match_date DESC
        LIMIT ?
        """, (sport, team, team, before_date.isoformat(), n_matches))

        matches = cursor.fetchall()

        if not matches:
            return 0.5  # Neutral form si no hay histórico

        # Calcular scores por partido
        scores = []
        for match in matches:
            is_home = match['home_team'] == team
            result = match['result_label']

            if is_home:
                score = 1.0 if result == 'home_win' else (0.5 if result == 'draw' else 0.0)
            else:
                score = 0.0 if result == 'home_win' else (0.5 if result == 'draw' else 1.0)

            scores.append(score)

        # Decay exponencial: partidos más recientes pesan más
        # exp(linspace(-1, 0, n)) da [0.37, ..., 1.0]
        weights = np.exp(np.linspace(-1, 0, len(scores)))
        weights = weights / weights.sum()  # Normalizar

        # Form promedio ponderado
        form = np.average(scores, weights=weights)

        return float(form)

    def calculate_h2h_stats(
        self,
        home_team: str,
        away_team: str,
        sport: str,
        before_date: datetime,
        n_matches: int = 10
    ) -> Dict:
        """
        Calcula estadísticas head-to-head entre dos equipos

        Args:
            home_team: Equipo local
            away_team: Equipo visitante
            sport: Deporte
            before_date: Fecha límite
            n_matches: Número de enfrentamientos a considerar

        Returns:
            Dict con estadísticas H2H
        """
        self.db.connect()
        cursor = self.db.conn.cursor()

        cursor.execute("""
        SELECT
            r.home_team, r.away_team, r.result_label,
            r.home_score, r.away_score
        FROM raw_match_results r
        WHERE r.sport = ?
        AND (
            (r.home_team = ? AND r.away_team = ?) OR
            (r.home_team = ? AND r.away_team = ?)
        )
        AND datetime(r.match_date) < datetime(?)
        ORDER BY r.match_date DESC
        LIMIT ?
        """, (sport, home_team, away_team, away_team, home_team,
              before_date.isoformat(), n_matches))

        matches = cursor.fetchall()

        if not matches:
            return {
                'h2h_matches': 0,
                'h2h_home_wins': 0,
                'h2h_away_wins': 0,
                'h2h_draws': 0,
                'h2h_home_win_rate': 0.33,  # Prior neutral
                'h2h_avg_goals_home': 1.5,
                'h2h_avg_goals_away': 1.5
            }

        # Calcular estadísticas
        home_wins = 0
        away_wins = 0
        draws = 0
        goals_home = []
        goals_away = []

        for match in matches:
            # Determinar quién era local/visitante en ese partido
            if match['home_team'] == home_team:
                # home_team era local
                if match['result_label'] == 'home_win':
                    home_wins += 1
                elif match['result_label'] == 'away_win':
                    away_wins += 1
                else:
                    draws += 1

                if match['home_score'] is not None:
                    goals_home.append(match['home_score'])
                    goals_away.append(match['away_score'])
            else:
                # home_team era visitante
                if match['result_label'] == 'away_win':
                    home_wins += 1
                elif match['result_label'] == 'home_win':
                    away_wins += 1
                else:
                    draws += 1

                if match['away_score'] is not None:
                    goals_home.append(match['away_score'])
                    goals_away.append(match['home_score'])

        total = len(matches)

        return {
            'h2h_matches': total,
            'h2h_home_wins': home_wins,
            'h2h_away_wins': away_wins,
            'h2h_draws': draws,
            'h2h_home_win_rate': home_wins / total if total > 0 else 0.33,
            'h2h_avg_goals_home': np.mean(goals_home) if goals_home else 1.5,
            'h2h_avg_goals_away': np.mean(goals_away) if goals_away else 1.5
        }

    def calculate_goals_stats(
        self,
        team: str,
        sport: str,
        before_date: datetime,
        n_matches: int = 10,
        home_only: bool = False,
        away_only: bool = False
    ) -> Dict:
        """
        Calcula estadísticas de goles (scored/conceded)

        Args:
            team: Nombre del equipo
            sport: Deporte
            before_date: Fecha límite
            n_matches: Número de partidos
            home_only: Solo partidos como local
            away_only: Solo partidos como visitante

        Returns:
            Dict con stats de goles
        """
        self.db.connect()
        cursor = self.db.conn.cursor()

        query = """
        SELECT
            r.home_team, r.away_team, r.home_score, r.away_score
        FROM raw_match_results r
        WHERE r.sport = ?
        AND datetime(r.match_date) < datetime(?)
        """

        params = [sport, before_date.isoformat()]

        if home_only:
            query += " AND r.home_team = ?"
            params.append(team)
        elif away_only:
            query += " AND r.away_team = ?"
            params.append(team)
        else:
            query += " AND (r.home_team = ? OR r.away_team = ?)"
            params.extend([team, team])

        query += " ORDER BY r.match_date DESC LIMIT ?"
        params.append(n_matches)

        cursor.execute(query, params)
        matches = cursor.fetchall()

        if not matches:
            return {
                'avg_goals_scored': 1.5,
                'avg_goals_conceded': 1.5,
                'goal_difference': 0.0
            }

        goals_scored = []
        goals_conceded = []

        for match in matches:
            if match['home_score'] is None or match['away_score'] is None:
                continue

            is_home = match['home_team'] == team

            if is_home:
                goals_scored.append(match['home_score'])
                goals_conceded.append(match['away_score'])
            else:
                goals_scored.append(match['away_score'])
                goals_conceded.append(match['home_score'])

        if not goals_scored:
            return {
                'avg_goals_scored': 1.5,
                'avg_goals_conceded': 1.5,
                'goal_difference': 0.0
            }

        avg_scored = np.mean(goals_scored)
        avg_conceded = np.mean(goals_conceded)

        return {
            'avg_goals_scored': float(avg_scored),
            'avg_goals_conceded': float(avg_conceded),
            'goal_difference': float(avg_scored - avg_conceded)
        }

    def calculate_league_strength(
        self,
        league: str,
        sport: str,
        before_date: datetime
    ) -> float:
        """
        Calcula índice de fuerza de la liga (ELO promedio)

        Args:
            league: Nombre de la liga
            sport: Deporte
            before_date: Fecha límite

        Returns:
            League strength (ELO promedio)
        """
        # Obtener equipos únicos de la liga
        self.db.connect()
        cursor = self.db.conn.cursor()

        cursor.execute("""
        SELECT DISTINCT home_team FROM raw_match_results
        WHERE league = ? AND sport = ? AND datetime(match_date) < datetime(?)
        UNION
        SELECT DISTINCT away_team FROM raw_match_results
        WHERE league = ? AND sport = ? AND datetime(match_date) < datetime(?)
        """, (league, sport, before_date.isoformat(),
              league, sport, before_date.isoformat()))

        teams = [row[0] for row in cursor.fetchall()]

        if not teams:
            return self.initial_elo  # Default

        # Calcular ELO promedio de la liga
        elos = []
        for team in teams[:20]:  # Limitar a 20 equipos para performance
            elo = self.calculate_elo_rating(team, sport, before_date, league)
            elos.append(elo)

        return float(np.mean(elos)) if elos else self.initial_elo

    def build_advanced_features(
        self,
        match: Dict,
        sport: str = 'soccer'
    ) -> Dict:
        """
        Construye features avanzadas para un partido
        TIME-AWARE: Solo usa datos anteriores al partido

        Args:
            match: Dict con match_id, home_team, away_team, match_date, odds
            sport: Deporte

        Returns:
            Dict con features avanzadas
        """
        home_team = match['home_team']
        away_team = match['away_team']
        match_date_str = match['match_date']
        league = match.get('league', 'Unknown')

        # Parse fecha
        try:
            match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
        except:
            match_date = datetime.now()

        logger.debug(f"Building features for {home_team} vs {away_team} ({match_date.date()})")

        # ELO Ratings
        home_elo = self.calculate_elo_rating(home_team, sport, match_date)
        away_elo = self.calculate_elo_rating(away_team, sport, match_date)

        # Form (últimos 5 partidos)
        home_form_5 = self.calculate_form_with_decay(home_team, sport, match_date, n_matches=5)
        away_form_5 = self.calculate_form_with_decay(away_team, sport, match_date, n_matches=5)

        # Form específica (local/visitante)
        home_form_home = self.calculate_form_with_decay(home_team, sport, match_date, n_matches=5)  # TODO: añadir filtro home_only
        away_form_away = self.calculate_form_with_decay(away_team, sport, match_date, n_matches=5)  # TODO: añadir filtro away_only

        # H2H
        h2h_stats = self.calculate_h2h_stats(home_team, away_team, sport, match_date)

        # Goals stats
        home_goals = self.calculate_goals_stats(home_team, sport, match_date, n_matches=10)
        away_goals = self.calculate_goals_stats(away_team, sport, match_date, n_matches=10)

        # League strength
        league_strength = self.calculate_league_strength(league, sport, match_date)

        # Market features (from odds)
        odds = match.get('odds', {})
        home_win_odds = odds.get('home_win', 2.0)
        away_win_odds = odds.get('away_win', 2.0)
        draw_odds = odds.get('draw', 3.0) if sport == 'soccer' else None

        # Implied probabilities
        implied_home = 1 / home_win_odds if home_win_odds > 0 else 0.5
        implied_away = 1 / away_win_odds if away_win_odds > 0 else 0.5
        implied_draw = 1 / draw_odds if draw_odds and draw_odds > 0 else 0.33

        # Market margin
        total_implied = implied_home + implied_away + (implied_draw if sport == 'soccer' else 0)
        margin = total_implied - 1.0

        # Features dict
        features = {
            # ELO
            'home_elo': home_elo,
            'away_elo': away_elo,
            'elo_diff': home_elo - away_elo,

            # Form
            'home_form_5': home_form_5,
            'away_form_5': away_form_5,
            'form_diff': home_form_5 - away_form_5,

            # H2H
            'h2h_matches': h2h_stats['h2h_matches'],
            'h2h_home_win_rate': h2h_stats['h2h_home_win_rate'],
            'h2h_avg_goals_home': h2h_stats['h2h_avg_goals_home'],
            'h2h_avg_goals_away': h2h_stats['h2h_avg_goals_away'],

            # Goals
            'home_goals_scored_avg': home_goals['avg_goals_scored'],
            'home_goals_conceded_avg': home_goals['avg_goals_conceded'],
            'away_goals_scored_avg': away_goals['avg_goals_scored'],
            'away_goals_conceded_avg': away_goals['avg_goals_conceded'],
            'home_goal_diff': home_goals['goal_difference'],
            'away_goal_diff': away_goals['goal_difference'],

            # League
            'league_strength': league_strength,

            # Market
            'home_win_odds': home_win_odds,
            'away_win_odds': away_win_odds,
            'implied_home': implied_home,
            'implied_away': implied_away,
            'market_margin': margin
        }

        if sport == 'soccer' and draw_odds:
            features['draw_odds'] = draw_odds
            features['implied_draw'] = implied_draw

        logger.debug(f"Features built: ELO diff={features['elo_diff']:.1f}, Form diff={features['form_diff']:.2f}")

        return features


if __name__ == "__main__":
    # Test del feature engineering
    from src.utils.database import BettingDatabase

    print("=== Testing Advanced Feature Engineering ===\n")

    db = BettingDatabase()
    engine = AdvancedFeatureEngine(db)

    # Match de prueba
    test_match = {
        'match_id': 'test_001',
        'home_team': 'Arsenal',
        'away_team': 'Chelsea',
        'match_date': '2024-01-15T15:00:00',
        'league': 'Premier League',
        'odds': {
            'home_win': 2.10,
            'away_win': 3.40,
            'draw': 3.20
        }
    }

    features = engine.build_advanced_features(test_match, sport='soccer')

    print(f"Match: {test_match['home_team']} vs {test_match['away_team']}\n")
    print("Advanced Features:")
    for key, value in features.items():
        print(f"  {key}: {value:.3f}" if isinstance(value, float) else f"  {key}: {value}")
