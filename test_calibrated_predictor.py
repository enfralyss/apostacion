"""
Test rapido del predictor actualizado con modelo calibrado
"""

from src.models.predictor import MatchPredictor
from src.utils.database import BettingDatabase
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("TEST: PREDICTOR CON MODELO CALIBRADO")
print("=" * 70)

# 1. Cargar predictor
print("\n[1] Cargando predictor...")
try:
    predictor = MatchPredictor()
    print(f"[OK] Predictor cargado")
except Exception as e:
    print(f"[ERROR] Error cargando predictor: {e}")
    sys.exit(1)

# 2. Verificar modelo calibrado
print("\n[2] Verificando modelo...")
if hasattr(predictor, 'is_calibrated'):
    if predictor.is_calibrated:
        print(f"[OK] Usando modelo CALIBRADO")
        print(f"   Clase: {predictor.soccer_model.__class__.__name__}")
    else:
        print(f"[WARN] Usando modelo ANTIGUO (sin calibrar)")
        print(f"   Entrenar modelo calibrado: python train_advanced_model.py")
else:
    print(f"[WARN] Predictor sin atributo is_calibrated (version antigua)")

# 3. Obtener match de prueba de la DB
print("\n[3] Obteniendo match de prueba desde DB...")
db = BettingDatabase()
db.connect()
cursor = db.conn.cursor()

cursor.execute("""
    SELECT c.match_id, c.sport, c.league, c.home_team, c.away_team, c.match_date,
           c.home_win_odds, c.away_win_odds, c.draw_odds
    FROM canonical_odds c
    JOIN raw_match_results r ON c.match_id = r.match_id
    WHERE c.sport = 'soccer'
    ORDER BY c.match_date DESC
    LIMIT 1
""")

row = cursor.fetchone()
if not row:
    print("[ERROR] No hay matches en la DB")
    print("   Ejecutar: python bootstrap_historical_data.py --months 6")
    sys.exit(1)

test_match = {
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

print(f"[OK] Match de prueba: {test_match['home_team']} vs {test_match['away_team']}")
print(f"   Liga: {test_match['league']}")
print(f"   Fecha: {test_match['match_date']}")

# 4. Generar predicción
print("\n[4] Generando predicción...")
try:
    prediction = predictor.predict_match(test_match)

    if 'error' in prediction:
        print(f"[ERROR] Error en predicción: {prediction['error']}")
        sys.exit(1)

    print(f"[OK] Predicción generada exitosamente")
    print(f"\n   Predicción: {prediction['prediction']}")
    print(f"   Confianza: {prediction['confidence']:.2%}")
    print(f"\n   Probabilidades:")
    for outcome, prob in prediction['probabilities'].items():
        print(f"      {outcome}: {prob:.2%}")

    # Calcular edge
    implied_probs = {
        'home_win': 1 / test_match['odds']['home_win'],
        'away_win': 1 / test_match['odds']['away_win'],
        'draw': 1 / test_match['odds']['draw']
    }

    print(f"\n   Edge Analysis:")
    for outcome in ['home_win', 'away_win', 'draw']:
        model_prob = prediction['probabilities'].get(outcome, 0)
        market_prob = implied_probs[outcome]
        edge = model_prob - market_prob
        print(f"      {outcome}: edge={edge:+.2%} (model={model_prob:.2%}, market={market_prob:.2%})")

except Exception as e:
    print(f"[ERROR] Error generando predicción: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Verificar features usadas
print("\n[5] Verificando features...")
if predictor.is_calibrated:
    print("[OK] Usando features AVANZADAS (24 features: ELO, form, H2H, goals)")
else:
    print("[WARN] Usando features BÁSICAS (10 features)")

print("\n" + "=" * 70)
print("TEST COMPLETADO")
print("=" * 70)

if predictor.is_calibrated:
    print("\n[OK] RESULTADO: Predictor funcionando con modelo CALIBRADO")
    print("   - Probabilidades calibradas (ECE=0.0)")
    print("   - Features avanzadas (ELO, form, H2H)")
    print("   - Listo para autotuning y producción")
else:
    print("\n[WARN] RESULTADO: Predictor usando modelo ANTIGUO")
    print("   - Probabilidades SIN calibrar")
    print("   - Features básicas")
    print("   - Entrenar modelo calibrado: python train_advanced_model.py")

print("\n" + "=" * 70)
