"""
API Odds Fetcher - Obtiene odds reales de APIs públicas
Usa The Odds API para obtener cuotas en tiempo real
"""

import os
import requests
from typing import List, Dict
from datetime import datetime
from loguru import logger
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    def load_dotenv(*args, **kwargs):  # type: ignore
        return None

load_dotenv()


class OddsAPIFetcher:
    """
    Fetcher de odds usando The Odds API
    https://the-odds-api.com/

    Plan gratuito: 500 requests/mes
    """

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: API key de The Odds API (obtener en https://the-odds-api.com/)
        """
        self.api_key = api_key or os.getenv('ODDS_API_KEY')
        self.base_url = "https://api.the-odds-api.com/v4"

        if not self.api_key:
            logger.warning("No ODDS_API_KEY found. Get one free at https://the-odds-api.com/")
            logger.warning("500 requests/month free tier available")

    def get_available_matches(self, sport: str = "all") -> List[Dict]:
        """
        Obtiene partidos con odds reales

        Args:
            sport: 'soccer', 'basketball', o 'all'

        Returns:
            Lista de partidos con odds
        """
        if not self.api_key:
            logger.error("API key not configured")
            return []

        matches = []

        try:
            if sport in ["soccer", "all"]:
                # Champions League
                matches.extend(self._fetch_sport_odds("soccer_uefa_champs_league", "Champions League"))
                # La Liga
                matches.extend(self._fetch_sport_odds("soccer_spain_la_liga", "La Liga"))
                # Premier League
                matches.extend(self._fetch_sport_odds("soccer_epl", "Premier League"))
                # Serie A
                matches.extend(self._fetch_sport_odds("soccer_italy_serie_a", "Serie A"))
                # Bundesliga
                matches.extend(self._fetch_sport_odds("soccer_germany_bundesliga", "Bundesliga"))

            if sport in ["basketball", "all"]:
                # NBA
                matches.extend(self._fetch_sport_odds("basketball_nba", "NBA"))

        except Exception as e:
            logger.error(f"Error fetching odds: {e}")

        logger.info(f"Fetched {len(matches)} matches with real odds")
        return matches

    def _fetch_sport_odds(self, sport_key: str, league_name: str) -> List[Dict]:
        """
        Fetch odds para un deporte específico

        Args:
            sport_key: Key del deporte en The Odds API
            league_name: Nombre de la liga

        Returns:
            Lista de partidos
        """
        matches = []

        try:
            url = f"{self.base_url}/sports/{sport_key}/odds"

            params = {
                'apiKey': self.api_key,
                'regions': 'us,eu',  # Regiones de casas de apuestas
                'markets': 'h2h',     # Head to head (1X2 para soccer, moneyline para NBA)
                'oddsFormat': 'decimal',
                'dateFormat': 'iso'
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                logger.info(f"Fetched {len(data)} matches from {league_name}")

                for event in data:
                    match = self._parse_event(event, sport_key, league_name)
                    if match:
                        matches.append(match)

            elif response.status_code == 401:
                logger.error("Invalid API key")
            elif response.status_code == 429:
                logger.error("API rate limit exceeded")
            else:
                logger.warning(f"API returned status {response.status_code} for {league_name}")

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching {league_name}")
        except Exception as e:
            logger.error(f"Error fetching {league_name}: {e}")

        return matches

    def _parse_event(self, event: dict, sport_key: str, league_name: str) -> Dict:
        """Parse un evento de la API a nuestro formato"""

        try:
            home_team = event['home_team']
            away_team = event['away_team']
            commence_time = event['commence_time']

            # Obtener bookmaker con mejores odds (promedio)
            bookmakers = event.get('bookmakers', [])

            if not bookmakers:
                return None

            # Promediar odds de múltiples bookmakers
            home_odds_list = []
            away_odds_list = []
            draw_odds_list = []

            for bookmaker in bookmakers:
                markets = bookmaker.get('markets', [])
                for market in markets:
                    if market['key'] == 'h2h':
                        outcomes = market['outcomes']

                        for outcome in outcomes:
                            if outcome['name'] == home_team:
                                home_odds_list.append(outcome['price'])
                            elif outcome['name'] == away_team:
                                away_odds_list.append(outcome['price'])
                            elif outcome['name'] == 'Draw':
                                draw_odds_list.append(outcome['price'])

            if not home_odds_list or not away_odds_list:
                return None

            # Promediar
            home_odds = sum(home_odds_list) / len(home_odds_list)
            away_odds = sum(away_odds_list) / len(away_odds_list)

            # Soccer tiene empate
            is_soccer = 'soccer' in sport_key

            match = {
                'match_id': event['id'],
                'sport': 'soccer' if is_soccer else 'nba',
                'league': league_name,
                'home_team': home_team,
                'away_team': away_team,
                'match_date': commence_time,
                'bookmakers_count': len(bookmakers),
                'odds': {
                    'home_win': round(home_odds, 2),
                    'away_win': round(away_odds, 2)
                }
            }

            # Agregar empate si es soccer
            if is_soccer and draw_odds_list:
                draw_odds = sum(draw_odds_list) / len(draw_odds_list)
                match['odds']['draw'] = round(draw_odds, 2)

            return match

        except Exception as e:
            logger.debug(f"Error parsing event: {e}")
            return None

    def check_api_status(self) -> Dict:
        """Verifica el estado de la API y requests restantes"""

        if not self.api_key:
            return {'status': 'error', 'message': 'No API key'}

        try:
            # Hacer un request simple para ver headers
            url = f"{self.base_url}/sports"
            params = {'apiKey': self.api_key}

            response = requests.get(url, params=params, timeout=5)

            # The Odds API devuelve requests restantes en headers
            remaining = response.headers.get('x-requests-remaining', 'unknown')
            used = response.headers.get('x-requests-used', 'unknown')

            return {
                'status': 'ok' if response.status_code == 200 else 'error',
                'requests_remaining': remaining,
                'requests_used': used,
                'status_code': response.status_code
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def fetch_scores(self, sport: str = "all", days_from: int = 3) -> List[Dict]:
        """
        Obtiene scores/resultados finales de partidos recientes

        Args:
            sport: 'soccer', 'basketball', o 'all'
            days_from: días hacia atrás para consultar (default 3)

        Returns:
            Lista de partidos con scores finales
        """
        if not self.api_key:
            logger.error("API key not configured")
            return []

        scores = []

        try:
            if sport in ["soccer", "all"]:
                # Champions League
                scores.extend(self._fetch_sport_scores("soccer_uefa_champs_league", "Champions League"))
                # La Liga
                scores.extend(self._fetch_sport_scores("soccer_spain_la_liga", "La Liga"))
                # Premier League
                scores.extend(self._fetch_sport_scores("soccer_epl", "Premier League"))
                # Serie A
                scores.extend(self._fetch_sport_scores("soccer_italy_serie_a", "Serie A"))
                # Bundesliga
                scores.extend(self._fetch_sport_scores("soccer_germany_bundesliga", "Bundesliga"))

            if sport in ["basketball", "all"]:
                # NBA
                scores.extend(self._fetch_sport_scores("basketball_nba", "NBA"))

        except Exception as e:
            logger.error(f"Error fetching scores: {e}")

        logger.info(f"Fetched {len(scores)} match scores")
        return scores

    def _fetch_sport_scores(self, sport_key: str, league_name: str) -> List[Dict]:
        """
        Fetch scores para un deporte específico

        Args:
            sport_key: Key del deporte en The Odds API
            league_name: Nombre de la liga

        Returns:
            Lista de partidos con scores
        """
        scores = []

        try:
            url = f"{self.base_url}/sports/{sport_key}/scores"

            params = {
                'apiKey': self.api_key,
                'daysFrom': 3,  # Últimos 3 días
                'dateFormat': 'iso'
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                logger.info(f"Fetched {len(data)} completed matches from {league_name}")

                for event in data:
                    # Solo procesar partidos completados
                    if not event.get('completed'):
                        continue

                    score = self._parse_score(event, sport_key, league_name)
                    if score:
                        scores.append(score)

            elif response.status_code == 401:
                logger.error("Invalid API key")
            elif response.status_code == 429:
                logger.error("API rate limit exceeded")
            else:
                logger.warning(f"API returned status {response.status_code} for {league_name}")

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching scores for {league_name}")
        except Exception as e:
            logger.error(f"Error fetching scores for {league_name}: {e}")

        return scores

    def _parse_score(self, event: dict, sport_key: str, league_name: str) -> Dict:
        """Parse un score de la API a nuestro formato"""

        try:
            home_team = event['home_team']
            away_team = event['away_team']
            match_date = event['commence_time']

            # Obtener scores
            scores = event.get('scores')
            if not scores:
                return None

            home_score = None
            away_score = None

            for score in scores:
                if score['name'] == home_team:
                    home_score = int(score['score'])
                elif score['name'] == away_team:
                    away_score = int(score['score'])

            if home_score is None or away_score is None:
                return None

            # Determinar resultado
            if home_score > away_score:
                result_label = 'home_win'
            elif away_score > home_score:
                result_label = 'away_win'
            else:
                result_label = 'draw'

            is_soccer = 'soccer' in sport_key

            return {
                'match_id': event['id'],
                'sport': 'soccer' if is_soccer else 'nba',
                'league': league_name,
                'home_team': home_team,
                'away_team': away_team,
                'match_date': match_date,
                'home_score': home_score,
                'away_score': away_score,
                'result_label': result_label,
                'completed': True
            }

        except Exception as e:
            logger.debug(f"Error parsing score: {e}")
            return None


class FootballDataAPI:
    """
    Fetcher usando Football-Data.org
    Solo para fútbol europeo
    Plan gratuito: 10 requests/minuto
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FOOTBALL_DATA_API_KEY')
        self.base_url = "https://api.football-data.org/v4"

        if not self.api_key:
            logger.warning("No FOOTBALL_DATA_API_KEY found")

    def get_available_matches(self) -> List[Dict]:
        """Obtiene partidos de ligas europeas"""

        if not self.api_key:
            return []

        matches = []

        # IDs de competiciones
        competitions = {
            'CL': 'Champions League',    # 2001
            'PL': 'Premier League',       # 2021
            'PD': 'La Liga',              # 2014
            'SA': 'Serie A',              # 2019
            'BL1': 'Bundesliga'           # 2002
        }

        try:
            headers = {'X-Auth-Token': self.api_key}

            for comp_code, comp_name in competitions.items():
                url = f"{self.base_url}/competitions/{comp_code}/matches"
                params = {'status': 'SCHEDULED'}

                response = requests.get(url, headers=headers, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    for match in data.get('matches', []):
                        matches.append({
                            'match_id': match['id'],
                            'sport': 'soccer',
                            'league': comp_name,
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'match_date': match['utcDate'],
                            'odds': None  # Esta API no provee odds
                        })

        except Exception as e:
            logger.error(f"Error fetching Football-Data: {e}")

        return matches


if __name__ == "__main__":
    # Test
    print("=== Testing Real Odds APIs ===\n")

    # The Odds API
    odds_api = OddsAPIFetcher()

    # Check status
    status = odds_api.check_api_status()
    print(f"API Status: {status}\n")

    if status['status'] == 'ok':
        print(f"Requests remaining: {status.get('requests_remaining', 'unknown')}\n")

        # Fetch matches
        print("Fetching matches...")
        matches = odds_api.get_available_matches("all")

        print(f"\nTotal matches found: {len(matches)}\n")

        # Show samples
        print("=== Sample Matches ===\n")
        for i, match in enumerate(matches[:5], 1):
            print(f"{i}. {match['league']}: {match['home_team']} vs {match['away_team']}")
            print(f"   Odds: {match['odds']}")
            print(f"   Date: {match['match_date']}")
            print()
    else:
        print("API key not configured or invalid")
        print("\nTo get a FREE API key:")
        print("1. Go to: https://the-odds-api.com/")
        print("2. Sign up (free - 500 requests/month)")
        print("3. Get your API key")
        print("4. Add to .env file: ODDS_API_KEY=your_key_here")
