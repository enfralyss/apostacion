"""
Historical Odds Scraper - Obtiene odds históricas REALES

Fuentes alternativas para odds históricas:
1. Oddsportal.com (scraping con BeautifulSoup)
2. Football-Data.co.uk (CSV históricos gratis)
3. API-Football (odds históricas)
"""

import requests
import pandas as pd
from typing import List, Dict
from datetime import datetime, timedelta
from loguru import logger
import time
import os


class FootballDataUK:
    """
    Scraper de Football-Data.co.uk
    Provee CSVs GRATIS con odds históricas de varias casas de apuestas

    Ventajas:
    - Totalmente gratis
    - Datos desde 2000
    - Odds de múltiples bookmakers (Bet365, William Hill, etc)
    - Formato CSV fácil de procesar

    Desventajas:
    - Solo fútbol europeo (no NBA)
    - No hay datos en tiempo real
    """

    BASE_URL = "https://www.football-data.co.uk/mmz4281"

    # Mapeo de ligas a códigos
    LEAGUES = {
        'Premier League': 'E0',
        'La Liga': 'SP1',
        'Serie A': 'I1',
        'Bundesliga': 'D1',
        'Ligue 1': 'F1'
    }

    def __init__(self):
        self.session = requests.Session()

    def get_season_string(self, year: int) -> str:
        """Convierte año a formato de temporada (ej: 2023 -> '2324')"""
        next_year = (year + 1) % 100
        current_year = year % 100
        return f"{current_year:02d}{next_year:02d}"

    def fetch_league_season(self, league: str, season_year: int) -> pd.DataFrame:
        """
        Descarga datos de una liga para una temporada específica

        Args:
            league: Nombre de la liga (ej: 'Premier League')
            season_year: Año de inicio de la temporada (ej: 2023 para 2023/24)

        Returns:
            DataFrame con partidos y odds
        """
        league_code = self.LEAGUES.get(league)
        if not league_code:
            logger.error(f"Unknown league: {league}")
            return pd.DataFrame()

        season_str = self.get_season_string(season_year)
        url = f"{self.BASE_URL}/{season_str}/{league_code}.csv"

        logger.info(f"Fetching {league} {season_year}/{season_year+1} from {url}")

        try:
            df = pd.read_csv(url, encoding='utf-8')
            logger.info(f"Fetched {len(df)} matches from {league} {season_year}/{season_year+1}")
            return df
        except Exception as e:
            logger.warning(f"Could not fetch {league} {season_year}: {e}")
            return pd.DataFrame()

    def parse_to_standard_format(self, df: pd.DataFrame, league: str) -> List[Dict]:
        """
        Convierte DataFrame de Football-Data.co.uk a nuestro formato estándar

        Columnas importantes:
        - Date: Fecha del partido
        - HomeTeam, AwayTeam: Equipos
        - FTHG, FTAG: Full Time Home/Away Goals
        - FTR: Full Time Result (H/D/A)
        - B365H, B365D, B365A: Bet365 odds (Home/Draw/Away)
        - BWH, BWD, BWA: Bet&Win odds
        - PSH, PSD, PSA: Pinnacle odds (mejor promedio)
        """
        matches = []

        for _, row in df.iterrows():
            try:
                # Parse fecha
                date_str = row.get('Date')
                if pd.isna(date_str):
                    continue

                # Intentar múltiples formatos de fecha
                date_obj = None
                for fmt in ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d']:
                    try:
                        date_obj = datetime.strptime(str(date_str), fmt)
                        break
                    except:
                        continue

                if not date_obj:
                    continue

                # Equipos
                home_team = row.get('HomeTeam')
                away_team = row.get('AwayTeam')

                if pd.isna(home_team) or pd.isna(away_team):
                    continue

                # Resultado
                fthg = row.get('FTHG')  # Full Time Home Goals
                ftag = row.get('FTAG')  # Full Time Away Goals
                ftr = row.get('FTR')    # Full Time Result

                if pd.isna(ftr):
                    continue

                # Mapear resultado
                if ftr == 'H':
                    result_label = 'home_win'
                elif ftr == 'A':
                    result_label = 'away_win'
                elif ftr == 'D':
                    result_label = 'draw'
                else:
                    continue

                # Odds - Intentar Pinnacle primero (más confiables), luego Bet365
                home_odds = row.get('PSH') or row.get('B365H') or row.get('BWH')
                draw_odds = row.get('PSD') or row.get('B365D') or row.get('BWD')
                away_odds = row.get('PSA') or row.get('B365A') or row.get('BWA')

                # Validar que haya odds
                if pd.isna(home_odds) or pd.isna(away_odds):
                    continue

                # Crear match
                match = {
                    'match_id': f"fd_{league}_{home_team}_{away_team}_{date_obj.strftime('%Y%m%d')}",
                    'sport': 'soccer',
                    'league': league,
                    'home_team': str(home_team),
                    'away_team': str(away_team),
                    'match_date': date_obj.isoformat(),
                    'home_score': int(fthg) if not pd.isna(fthg) else None,
                    'away_score': int(ftag) if not pd.isna(ftag) else None,
                    'result_label': result_label,
                    'odds': {
                        'home_win': float(home_odds),
                        'away_win': float(away_odds),
                        'draw': float(draw_odds) if not pd.isna(draw_odds) else 3.3
                    },
                    'bookmakers_count': 1,
                    'data_source': 'football-data.co.uk',
                    'completed': True
                }

                matches.append(match)

            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue

        return matches

    def fetch_historical_data(self, months_back: int = 6) -> List[Dict]:
        """
        Obtiene datos históricos de múltiples ligas

        Args:
            months_back: Meses hacia atrás para cargar

        Returns:
            Lista de partidos con odds reales
        """
        all_matches = []

        # Determinar qué temporadas necesitamos
        current_date = datetime.now()
        current_year = current_date.year

        # Si estamos antes de julio, la temporada actual empezó el año anterior
        if current_date.month < 7:
            seasons = [current_year - 2, current_year - 1]
        else:
            seasons = [current_year - 1, current_year]

        # Fetch todas las ligas
        for league in self.LEAGUES.keys():
            for season_year in seasons:
                df = self.fetch_league_season(league, season_year)

                if not df.empty:
                    matches = self.parse_to_standard_format(df, league)
                    all_matches.extend(matches)

                # Rate limiting
                time.sleep(0.5)

        # Filtrar solo partidos de los últimos N meses
        cutoff_date = datetime.now() - timedelta(days=months_back * 30)
        filtered_matches = [
            m for m in all_matches
            if datetime.fromisoformat(m['match_date']) >= cutoff_date
        ]

        logger.info(f"Fetched {len(filtered_matches)} historical matches from last {months_back} months")

        return filtered_matches


class APIFootballHistorical:
    """
    API-Football.com para odds históricas
    Requiere API key pero tiene plan gratuito (100 requests/día)
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('API_FOOTBALL_KEY')
        self.base_url = "https://v3.football.api-sports.io"

        if not self.api_key:
            logger.warning("API_FOOTBALL_KEY not configured")

    def fetch_odds_for_match(self, fixture_id: int) -> Dict:
        """Obtiene odds para un partido específico"""
        # Implementación pendiente - requiere API key
        pass


if __name__ == "__main__":
    # Test
    print("=== Testing Historical Odds Scraper ===\n")

    # Football-Data.co.uk (GRATIS)
    fd_scraper = FootballDataUK()

    print("Fetching historical data from Football-Data.co.uk...")
    matches = fd_scraper.fetch_historical_data(months_back=3)

    print(f"\nTotal matches fetched: {len(matches)}\n")

    # Mostrar samples
    print("=== Sample Matches ===\n")
    for i, match in enumerate(matches[:5], 1):
        print(f"{i}. {match['league']}: {match['home_team']} vs {match['away_team']}")
        print(f"   Date: {match['match_date'][:10]}")
        print(f"   Result: {match['result_label']} ({match['home_score']}-{match['away_score']})")
        print(f"   Odds: {match['odds']}")
        print()

    # Agrupar por liga
    from collections import Counter
    leagues = Counter([m['league'] for m in matches])
    print("\n=== Matches by League ===")
    for league, count in leagues.items():
        print(f"{league}: {count} matches")
