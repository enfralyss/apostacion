"""
Feature Integration - Integra advanced features en el pipeline de training/prediction
"""

import pandas as pd
from typing import Dict, List
from loguru import logger
from src.data.feature_engineering import AdvancedFeatureEngine
from src.utils.database import BettingDatabase


def calculate_match_features_advanced(
    match: Dict,
    db: BettingDatabase
) -> Dict:
    """
    Calcula features avanzadas para un match usando AdvancedFeatureEngine

    Este es el wrapper que se integra con el sistema actual

    Args:
        match: Dict con match info (home_team, away_team, match_date, odds, etc.)
        db: BettingDatabase instance

    Returns:
        Dict con features avanzadas listas para modelo
    """
    sport = match.get('sport', 'soccer')

    # Crear feature engine
    engine = AdvancedFeatureEngine(db)

    # Build advanced features
    features = engine.build_advanced_features(match, sport=sport)

    return features


def build_training_dataset_with_advanced_features(
    db: BettingDatabase,
    sport: str = 'soccer',
    min_rows: int = 100
) -> pd.DataFrame:
    """
    Construye dataset de entrenamiento con features avanzadas

    Args:
        db: BettingDatabase instance
        sport: Deporte a entrenar
        min_rows: Mínimo de filas requeridas

    Returns:
        DataFrame con features avanzadas + target (result)
    """
    logger.info(f"Building training dataset with advanced features for {sport}...")

    # 1. Obtener matches con odds y resultados
    db.connect()
    cursor = db.conn.cursor()

    query = """
    SELECT
        r.match_id,
        r.sport,
        r.league,
        r.home_team,
        r.away_team,
        r.match_date,
        r.result_label,
        r.home_score,
        r.away_score,
        c.home_win_odds,
        c.away_win_odds,
        c.draw_odds
    FROM raw_match_results r
    JOIN canonical_odds c ON r.match_id = c.match_id
    WHERE r.sport = ?
    AND r.result_label IS NOT NULL
    ORDER BY r.match_date ASC
    """

    cursor.execute(query, (sport,))
    rows = cursor.fetchall()

    if len(rows) < min_rows:
        logger.warning(f"Insufficient data: {len(rows)} rows (min: {min_rows})")
        return pd.DataFrame()

    logger.info(f"Found {len(rows)} matches with results")

    # 2. Build features para cada match
    features_list = []

    for i, row in enumerate(rows):
        if i % 100 == 0:
            logger.info(f"Processing match {i}/{len(rows)}...")

        match = {
            'match_id': row['match_id'],
            'sport': row['sport'],
            'league': row['league'],
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'match_date': row['match_date'],
            'odds': {
                'home_win': row['home_win_odds'],
                'away_win': row['away_win_odds'],
                'draw': row['draw_odds']
            }
        }

        try:
            features = calculate_match_features_advanced(match, db)

            # Agregar target
            features['result'] = row['result_label']
            features['match_id'] = row['match_id']
            features['match_date'] = row['match_date']

            features_list.append(features)
        except Exception as e:
            logger.warning(f"Error processing match {match['match_id']}: {e}")
            continue

    if not features_list:
        logger.error("No features generated")
        return pd.DataFrame()

    # 3. Convertir a DataFrame
    df = pd.DataFrame(features_list)

    logger.info(f"Dataset built: {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"Features: {df.columns.tolist()}")

    # 4. Guardar CSV para referencia
    import os
    os.makedirs("data", exist_ok=True)

    output_path = f"data/training_advanced_{sport}.csv"
    df.to_csv(output_path, index=False)
    logger.info(f"Dataset saved to {output_path}")

    return df


if __name__ == "__main__":
    # Test de integración
    print("=== Testing Feature Integration ===\n")

    db = BettingDatabase()

    # Build dataset with advanced features
    df = build_training_dataset_with_advanced_features(db, sport='soccer', min_rows=50)

    if not df.empty:
        print(f"\nDataset shape: {df.shape}")
        print(f"\nFeatures ({len(df.columns)} total):")
        print(df.columns.tolist())
        print(f"\nFirst 5 rows:")
        print(df.head())

        print(f"\nTarget distribution:")
        print(df['result'].value_counts())
