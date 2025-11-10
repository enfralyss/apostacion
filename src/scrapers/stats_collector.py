"""
Stats Collector - Recolecta estadísticas de equipos de APIs públicas
Genera datos mock realistas para desarrollo
"""

import random
from typing import Dict, List
from datetime import datetime, timedelta
from loguru import logger


class StatsCollector:
    """Recolector de estadísticas de equipos"""

    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock

    def get_team_stats(self, team_name: str, sport: str) -> Dict:
        """
        Obtiene estadísticas completas de un equipo

        Args:
            team_name: Nombre del equipo
            sport: 'soccer' o 'nba'

        Returns:
            Diccionario con estadísticas del equipo
        """
        if self.use_mock:
            return self._generate_mock_stats(team_name, sport)
        else:
            if sport == "soccer":
                return self._fetch_soccer_stats(team_name)
            else:
                return self._fetch_nba_stats(team_name)

    def _generate_mock_stats(self, team_name: str, sport: str) -> Dict:
        """Genera estadísticas mock realistas"""

        base_stats = {
            "team_name": team_name,
            "sport": sport,
            "last_updated": datetime.now().isoformat()
        }

        if sport == "soccer":
            stats = {
                **base_stats,
                # Forma reciente
                "wins_last_10": random.randint(4, 8),
                "draws_last_10": random.randint(1, 3),
                "losses_last_10": random.randint(1, 4),
                "form_last_5": round(random.uniform(1.5, 3.0), 2),  # Puntos por partido

                # Récord local/visitante
                "home_wins": random.randint(5, 10),
                "home_draws": random.randint(1, 3),
                "home_losses": random.randint(0, 3),
                "away_wins": random.randint(3, 7),
                "away_draws": random.randint(2, 4),
                "away_losses": random.randint(1, 5),

                # Goles
                "goals_scored_avg": round(random.uniform(1.2, 2.5), 2),
                "goals_conceded_avg": round(random.uniform(0.8, 1.8), 2),
                "goals_scored_home_avg": round(random.uniform(1.5, 3.0), 2),
                "goals_conceded_home_avg": round(random.uniform(0.5, 1.5), 2),
                "goals_scored_away_avg": round(random.uniform(0.8, 2.0), 2),
                "goals_conceded_away_avg": round(random.uniform(1.0, 2.2), 2),

                # Otros
                "clean_sheets": random.randint(3, 8),
                "failed_to_score": random.randint(1, 4),
                "days_since_last_match": random.randint(3, 7),
                "injuries_count": random.randint(0, 3),

                # Últimos 5 resultados (W=Win, D=Draw, L=Loss)
                "last_5_results": self._generate_form_string(5),
                "last_5_results_home": self._generate_form_string(5),
                "last_5_results_away": self._generate_form_string(5)
            }
        else:  # NBA
            stats = {
                **base_stats,
                # Forma reciente
                "wins_last_10": random.randint(4, 8),
                "losses_last_10": random.randint(2, 6),
                "form_last_5": round(random.uniform(2.0, 4.5), 2),  # Wins últimos 5

                # Récord local/visitante
                "home_wins": random.randint(8, 15),
                "home_losses": random.randint(2, 8),
                "away_wins": random.randint(5, 12),
                "away_losses": random.randint(4, 12),

                # Puntos
                "points_scored_avg": round(random.uniform(105.0, 118.0), 1),
                "points_conceded_avg": round(random.uniform(102.0, 115.0), 1),
                "points_scored_home_avg": round(random.uniform(108.0, 122.0), 1),
                "points_conceded_home_avg": round(random.uniform(100.0, 112.0), 1),
                "points_scored_away_avg": round(random.uniform(102.0, 115.0), 1),
                "points_conceded_away_avg": round(random.uniform(105.0, 118.0), 1),

                # Otros
                "offensive_rating": round(random.uniform(108.0, 118.0), 1),
                "defensive_rating": round(random.uniform(105.0, 115.0), 1),
                "pace": round(random.uniform(98.0, 104.0), 1),
                "days_since_last_match": random.randint(1, 4),
                "injuries_count": random.randint(0, 3),

                # Últimos 5 resultados
                "last_5_results": self._generate_nba_form_string(5),
                "last_5_results_home": self._generate_nba_form_string(5),
                "last_5_results_away": self._generate_nba_form_string(5)
            }

        return stats

    def _generate_form_string(self, n: int) -> str:
        """Genera string de forma reciente para fútbol (W/D/L)"""
        results = random.choices(['W', 'D', 'L'], weights=[0.45, 0.25, 0.30], k=n)
        return ''.join(results)

    def _generate_nba_form_string(self, n: int) -> str:
        """Genera string de forma reciente para NBA (W/L)"""
        results = random.choices(['W', 'L'], weights=[0.55, 0.45], k=n)
        return ''.join(results)

    def get_head_to_head(self, team1: str, team2: str, sport: str) -> Dict:
        """
        Obtiene historial de enfrentamientos directos

        Returns:
            Estadísticas H2H
        """
        if self.use_mock:
            return self._generate_mock_h2h(team1, team2, sport)
        else:
            return self._fetch_real_h2h(team1, team2, sport)

    def _generate_mock_h2h(self, team1: str, team2: str, sport: str) -> Dict:
        """Genera datos H2H mock"""

        total_matches = random.randint(5, 15)
        team1_wins = random.randint(0, total_matches)
        team2_wins = random.randint(0, total_matches - team1_wins)
        draws = total_matches - team1_wins - team2_wins if sport == "soccer" else 0

        if sport == "nba":
            draws = 0
            team2_wins = total_matches - team1_wins

        return {
            "team1": team1,
            "team2": team2,
            "total_matches": total_matches,
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws,
            "team1_win_rate": round(team1_wins / total_matches, 3) if total_matches > 0 else 0,
            "last_5_h2h": self._generate_h2h_results(min(5, total_matches), sport)
        }

    def _generate_h2h_results(self, n: int, sport: str) -> List[Dict]:
        """Genera últimos N enfrentamientos"""
        results = []
        for i in range(n):
            result = {
                "date": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                "winner": random.choice(["team1", "team2", "draw"] if sport == "soccer" else ["team1", "team2"]),
            }
            if sport == "soccer":
                result["score"] = f"{random.randint(0, 4)}-{random.randint(0, 4)}"
            else:
                result["score"] = f"{random.randint(95, 125)}-{random.randint(95, 125)}"
            results.append(result)
        return results

    def _fetch_soccer_stats(self, team_name: str) -> Dict:
        """
        Obtiene estadísticas reales de fútbol desde API
        A implementar con API real (Football-Data.org, API-Football, etc.)
        """
        logger.warning("Real soccer API not implemented yet")
        # TODO: Implementar con requests a API real
        # import requests
        # response = requests.get(f"https://api.football-data.org/v4/teams/{team_id}")
        return {}

    def _fetch_nba_stats(self, team_name: str) -> Dict:
        """
        Obtiene estadísticas reales de NBA desde API
        A implementar con NBA Stats API
        """
        logger.warning("Real NBA API not implemented yet")
        # TODO: Implementar con NBA API
        return {}

    def _fetch_real_h2h(self, team1: str, team2: str, sport: str) -> Dict:
        """Obtiene H2H real desde API"""
        logger.warning("Real H2H API not implemented yet")
        return {}

    def calculate_team_features(self, team_stats: Dict, is_home: bool) -> Dict:
        """
        Calcula features para el modelo ML basado en estadísticas

        Args:
            team_stats: Estadísticas del equipo
            is_home: Si el equipo juega de local

        Returns:
            Features calculados
        """
        sport = team_stats.get("sport")

        if sport == "soccer":
            features = {
                "win_rate_last_10": team_stats["wins_last_10"] / 10,
                "form_last_5": team_stats["form_last_5"] / 3.0,  # Normalizado (max 3 pts)
                "win_rate": (
                    team_stats["home_wins"] / max(1, team_stats["home_wins"] + team_stats["home_draws"] + team_stats["home_losses"])
                    if is_home else
                    team_stats["away_wins"] / max(1, team_stats["away_wins"] + team_stats["away_draws"] + team_stats["away_losses"])
                ),
                "goals_scored_avg": team_stats["goals_scored_home_avg"] if is_home else team_stats["goals_scored_away_avg"],
                "goals_conceded_avg": team_stats["goals_conceded_home_avg"] if is_home else team_stats["goals_conceded_away_avg"],
                "goal_differential": (
                    team_stats["goals_scored_home_avg"] - team_stats["goals_conceded_home_avg"] if is_home
                    else team_stats["goals_scored_away_avg"] - team_stats["goals_conceded_away_avg"]
                ),
                "days_rest": team_stats["days_since_last_match"],
                "injuries_normalized": min(team_stats["injuries_count"] / 5.0, 1.0),  # Max 5 lesiones
                "clean_sheet_rate": team_stats["clean_sheets"] / 10.0
            }
        else:  # NBA
            features = {
                "win_rate_last_10": team_stats["wins_last_10"] / 10,
                "form_last_5": team_stats["form_last_5"] / 5.0,
                "win_rate": (
                    team_stats["home_wins"] / max(1, team_stats["home_wins"] + team_stats["home_losses"])
                    if is_home else
                    team_stats["away_wins"] / max(1, team_stats["away_wins"] + team_stats["away_losses"])
                ),
                "points_scored_avg": team_stats["points_scored_home_avg"] if is_home else team_stats["points_scored_away_avg"],
                "points_conceded_avg": team_stats["points_conceded_home_avg"] if is_home else team_stats["points_conceded_away_avg"],
                "point_differential": (
                    team_stats["points_scored_home_avg"] - team_stats["points_conceded_home_avg"] if is_home
                    else team_stats["points_scored_away_avg"] - team_stats["points_conceded_away_avg"]
                ),
                "offensive_rating": team_stats["offensive_rating"],
                "defensive_rating": team_stats["defensive_rating"],
                "pace": team_stats["pace"],
                "days_rest": team_stats["days_since_last_match"],
                "injuries_normalized": min(team_stats["injuries_count"] / 5.0, 1.0)
            }

        return features


if __name__ == "__main__":
    # Test del collector
    collector = StatsCollector(use_mock=True)

    print("=== Testing Stats Collector ===\n")

    # Test soccer stats
    soccer_stats = collector.get_team_stats("Real Madrid", "soccer")
    print("Real Madrid Stats:")
    print(f"  Form last 5: {soccer_stats['form_last_5']}")
    print(f"  Goals scored avg: {soccer_stats['goals_scored_avg']}")
    print(f"  Last 5 results: {soccer_stats['last_5_results']}")

    # Test NBA stats
    nba_stats = collector.get_team_stats("Los Angeles Lakers", "nba")
    print("\nLakers Stats:")
    print(f"  Form last 5: {nba_stats['form_last_5']}")
    print(f"  Points scored avg: {nba_stats['points_scored_avg']}")
    print(f"  Offensive rating: {nba_stats['offensive_rating']}")

    # Test H2H
    h2h = collector.get_head_to_head("Real Madrid", "Barcelona", "soccer")
    print(f"\nH2H Real Madrid vs Barcelona:")
    print(f"  Total matches: {h2h['total_matches']}")
    print(f"  Real Madrid wins: {h2h['team1_wins']}")
    print(f"  Barcelona wins: {h2h['team2_wins']}")
    print(f"  Draws: {h2h['draws']}")

    # Test features
    features = collector.calculate_team_features(soccer_stats, is_home=True)
    print(f"\nCalculated features for Real Madrid (home):")
    for key, value in features.items():
        print(f"  {key}: {value:.3f}")
