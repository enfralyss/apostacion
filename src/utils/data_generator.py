"""
Generador de datos históricos para entrenamiento del modelo
Crea datasets realistas de partidos pasados con resultados
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


def generate_training_data(sport: str, num_matches: int = 1000) -> pd.DataFrame:
    """
    Genera datos de entrenamiento sintéticos pero realistas

    Args:
        sport: 'soccer' o 'nba'
        num_matches: Número de partidos a generar

    Returns:
        DataFrame con features y resultados
    """
    data = []

    for i in range(num_matches):
        # Features del equipo local
        home_win_rate_last_10 = random.uniform(0.2, 0.8)
        home_form_last_5 = random.uniform(0.4, 1.0)
        home_win_rate = random.uniform(0.3, 0.8)

        # Features del equipo visitante
        away_win_rate_last_10 = random.uniform(0.2, 0.8)
        away_form_last_5 = random.uniform(0.4, 1.0)
        away_win_rate = random.uniform(0.2, 0.7)

        if sport == "soccer":
            # Soccer-specific features
            home_goals_scored = random.uniform(0.8, 2.5)
            home_goals_conceded = random.uniform(0.5, 2.0)
            away_goals_scored = random.uniform(0.6, 2.0)
            away_goals_conceded = random.uniform(0.8, 2.2)

            home_goal_diff = home_goals_scored - home_goals_conceded
            away_goal_diff = away_goals_scored - away_goals_conceded

            home_clean_sheet_rate = random.uniform(0.2, 0.6)
            away_clean_sheet_rate = random.uniform(0.15, 0.5)

            home_days_rest = random.randint(3, 7)
            away_days_rest = random.randint(3, 7)

            home_injuries = random.randint(0, 3)
            away_injuries = random.randint(0, 3)

            # H2H
            h2h_home_win_rate = random.uniform(0.2, 0.7)

            # Calcular probabilidad de victoria local (lógica simplificada)
            home_strength = (
                home_win_rate_last_10 * 0.2 +
                home_form_last_5 * 0.15 +
                home_win_rate * 0.15 +
                (home_goal_diff + 2) / 4 * 0.15 +
                home_clean_sheet_rate * 0.1 +
                h2h_home_win_rate * 0.15 +
                (7 - home_injuries) / 7 * 0.1
            )

            away_strength = (
                away_win_rate_last_10 * 0.2 +
                away_form_last_5 * 0.15 +
                away_win_rate * 0.15 +
                (away_goal_diff + 2) / 4 * 0.15 +
                away_clean_sheet_rate * 0.1 +
                (1 - h2h_home_win_rate) * 0.15 +
                (7 - away_injuries) / 7 * 0.1
            )

            # Ventaja de local
            home_advantage = 0.15

            # Normalizar
            total_strength = home_strength + away_strength
            home_prob = (home_strength / total_strength) + home_advantage
            away_prob = away_strength / total_strength
            draw_prob = max(0, 1 - home_prob - away_prob)  # Asegurar no negativo

            # Asegurar que sumen 1
            total_prob = home_prob + away_prob + draw_prob
            if total_prob > 0:
                home_prob /= total_prob
                away_prob /= total_prob
                draw_prob /= total_prob
            else:
                home_prob, away_prob, draw_prob = 0.33, 0.33, 0.34

            # Asegurar que todas sean no negativas
            home_prob = max(0, min(1, home_prob))
            away_prob = max(0, min(1, away_prob))
            draw_prob = max(0, min(1, draw_prob))

            # Determinar resultado
            outcome = np.random.choice(['home_win', 'draw', 'away_win'],
                                     p=[home_prob, draw_prob, away_prob])

            match = {
                'home_win_rate_last_10': home_win_rate_last_10,
                'home_form_last_5': home_form_last_5,
                'home_win_rate': home_win_rate,
                'home_goals_scored_avg': home_goals_scored,
                'home_goals_conceded_avg': home_goals_conceded,
                'home_goal_differential': home_goal_diff,
                'home_clean_sheet_rate': home_clean_sheet_rate,
                'home_days_rest': home_days_rest,
                'home_injuries_normalized': home_injuries / 5.0,

                'away_win_rate_last_10': away_win_rate_last_10,
                'away_form_last_5': away_form_last_5,
                'away_win_rate': away_win_rate,
                'away_goals_scored_avg': away_goals_scored,
                'away_goals_conceded_avg': away_goals_conceded,
                'away_goal_differential': away_goal_diff,
                'away_clean_sheet_rate': away_clean_sheet_rate,
                'away_days_rest': away_days_rest,
                'away_injuries_normalized': away_injuries / 5.0,

                'h2h_home_win_rate': h2h_home_win_rate,

                'stat_differential': home_strength - away_strength,

                'result': outcome
            }

        else:  # NBA
            # NBA-specific features
            home_points_scored = random.uniform(105, 118)
            home_points_conceded = random.uniform(102, 115)
            away_points_scored = random.uniform(102, 115)
            away_points_conceded = random.uniform(105, 118)

            home_point_diff = home_points_scored - home_points_conceded
            away_point_diff = away_points_scored - away_points_conceded

            home_off_rating = random.uniform(108, 118)
            home_def_rating = random.uniform(105, 115)
            away_off_rating = random.uniform(106, 116)
            away_def_rating = random.uniform(107, 117)

            home_pace = random.uniform(98, 104)
            away_pace = random.uniform(98, 104)

            home_days_rest = random.randint(1, 4)
            away_days_rest = random.randint(1, 4)

            home_injuries = random.randint(0, 3)
            away_injuries = random.randint(0, 3)

            h2h_home_win_rate = random.uniform(0.3, 0.7)

            # Calcular probabilidad
            home_strength = (
                home_win_rate_last_10 * 0.2 +
                home_form_last_5 * 0.15 +
                home_win_rate * 0.15 +
                (home_point_diff + 10) / 20 * 0.15 +
                (home_off_rating - 105) / 15 * 0.1 +
                (118 - home_def_rating) / 15 * 0.1 +
                h2h_home_win_rate * 0.1 +
                (7 - home_injuries) / 7 * 0.05
            )

            away_strength = (
                away_win_rate_last_10 * 0.2 +
                away_form_last_5 * 0.15 +
                away_win_rate * 0.15 +
                (away_point_diff + 10) / 20 * 0.15 +
                (away_off_rating - 105) / 15 * 0.1 +
                (118 - away_def_rating) / 15 * 0.1 +
                (1 - h2h_home_win_rate) * 0.1 +
                (7 - away_injuries) / 7 * 0.05
            )

            home_advantage = 0.1

            total_strength = home_strength + away_strength
            home_prob = (home_strength / total_strength) + home_advantage
            away_prob = 1 - home_prob

            outcome = np.random.choice(['home_win', 'away_win'],
                                     p=[home_prob, away_prob])

            match = {
                'home_win_rate_last_10': home_win_rate_last_10,
                'home_form_last_5': home_form_last_5,
                'home_win_rate': home_win_rate,
                'home_points_scored_avg': home_points_scored,
                'home_points_conceded_avg': home_points_conceded,
                'home_point_differential': home_point_diff,
                'home_offensive_rating': home_off_rating,
                'home_defensive_rating': home_def_rating,
                'home_pace': home_pace,
                'home_days_rest': home_days_rest,
                'home_injuries_normalized': home_injuries / 5.0,

                'away_win_rate_last_10': away_win_rate_last_10,
                'away_form_last_5': away_form_last_5,
                'away_win_rate': away_win_rate,
                'away_points_scored_avg': away_points_scored,
                'away_points_conceded_avg': away_points_conceded,
                'away_point_differential': away_point_diff,
                'away_offensive_rating': away_off_rating,
                'away_defensive_rating': away_def_rating,
                'away_pace': away_pace,
                'away_days_rest': away_days_rest,
                'away_injuries_normalized': away_injuries / 5.0,

                'h2h_home_win_rate': h2h_home_win_rate,

                'stat_differential': home_strength - away_strength,

                'result': outcome
            }

        data.append(match)

    df = pd.DataFrame(data)
    return df


if __name__ == "__main__":
    # Generar datos de prueba
    print("Generating training data...")

    soccer_data = generate_training_data("soccer", 1000)
    soccer_data.to_csv("data/historical_soccer.csv", index=False)
    print(f"Generated {len(soccer_data)} soccer matches")
    print(f"Soccer results distribution:\n{soccer_data['result'].value_counts()}\n")

    nba_data = generate_training_data("nba", 1000)
    nba_data.to_csv("data/historical_nba.csv", index=False)
    print(f"Generated {len(nba_data)} NBA matches")
    print(f"NBA results distribution:\n{nba_data['result'].value_counts()}")
