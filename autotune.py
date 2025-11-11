"""
Autotuning de parámetros de selección de picks para TriunfoBet Bot
- Ajusta automáticamente min_edge, min_probability, min_odds, max_odds en config.yaml
- Evalúa cada combinación usando ROI y win rate sobre histórico
- Actualiza config.yaml con el mejor set encontrado
"""

import yaml
import itertools
import copy
from src.utils.database import BettingDatabase
from src.betting.pick_selector import PickSelector
from src.models.predictor import MatchPredictor
import time
from random import shuffle

CONFIG_PATH = "config/config.yaml"

# Espacios de búsqueda (ajustados para modelo calibrado con accuracy ~48-52%)
PARAM_GRID = {
    'min_edge': [0.02, 0.03, 0.04, 0.05],
    'min_probability': [0.40, 0.45, 0.50, 0.52, 0.55],  # Más realista para modelo calibrado
    'min_odds': [1.50, 1.60, 1.70],
    'max_odds': [2.50, 3.00, 3.50]  # Más permisivo para encontrar value
}


def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, sort_keys=False, allow_unicode=True)

def evaluate_params(params, matches, predictor, db: BettingDatabase = None):
    # Crea un PickSelector temporal con los parámetros dados
    config = load_config()
    config['picks'].update(params)
    selector = PickSelector()
    selector.config = config
    selector.pick_criteria = config['picks']
    # Predice y selecciona picks
    if not matches:
        return {'roi': -999, 'win_rate': 0, 'n': 0}
    predictions = predictor.predict_multiple_matches(matches)
    picks = selector.select_picks(predictions)
    # Simula resultados usando la base de datos
    if db is None:
        db = BettingDatabase()
    # Solo picks con resultado conocido
    results = []
    db.connect()
    cursor = db.conn.cursor()
    for pick in picks:
        # Busca resultado real en DB
        match_id = pick['match_id']
        cursor.execute("SELECT result_label FROM raw_match_results WHERE match_id=?", (match_id,))
        row = cursor.fetchone()
        if not row:
            continue
        result = row['result_label']
        # Gana si predicción coincide con resultado
        win = (result == pick['prediction'])
        results.append({'win': win, 'odds': pick['odds']})
    if not results:
        return {'roi': -999, 'win_rate': 0, 'n': 0, 'geo_growth': -999, 'volatility': 0.0, 'score': -999}
    # Métricas de rendimiento por unidad apostada
    total_bets = len(results)
    rets = [(r['odds'] - 1.0) if r['win'] else -1.0 for r in results]
    total_staked = total_bets  # 1 unidad por apuesta
    total_return = sum((ret + 1.0) for ret in rets)
    roi = (total_return - total_staked) / total_staked
    win_rate = sum(1 for r in results if r['win']) / total_bets
    # Volatilidad (desv. estándar de retornos por apuesta)
    try:
        import statistics as _stats
        volatility = _stats.pstdev(rets) if len(rets) > 1 else abs(rets[0])
    except Exception:
        volatility = 0.0
    # Crecimiento geométrico (Kelly fraccional f=0.25)
    f = 0.25
    import math as _math
    growth_factors = []
    for ret in rets:
        g = 1.0 + f * ret
        if g <= 0:
            # Ruina en log-growth, castigar fuertemente
            return {'roi': roi, 'win_rate': win_rate, 'n': total_bets, 'geo_growth': -999, 'volatility': volatility, 'score': -999}
        growth_factors.append(g)
    geo_growth = sum(_math.log(g) for g in growth_factors) / total_bets  # log-growth por apuesta
    # Puntuación compuesta orientada a largo plazo: premia ROI y log-growth, penaliza volatilidad y bajo N
    score = 0.6 * roi + 0.3 * geo_growth + 0.1 * win_rate - 0.05 * volatility
    # Penalización por tamaño de muestra bajo
    score -= max(0, 50 - total_bets) * 0.002
    return {'roi': roi, 'win_rate': win_rate, 'n': total_bets, 'geo_growth': geo_growth, 'volatility': volatility, 'score': score}

def autotune_parameters(db: BettingDatabase = None, *, sample_size: int = 200, max_combinations: int = 24, time_limit_sec: int = 120):
    """Ejecuta el grid search de parámetros y retorna dict con mejores parámetros y métricas.

    Args:
        db: instancia opcional de BettingDatabase reutilizable.
        sample_size: número máximo de partidos históricos a usar
        max_combinations: límite de combinaciones a evaluar
        time_limit_sec: tiempo máximo de ejecución
    Returns:
        {'best_params': {...}, 'best_metrics': {...}, 'tested': [({'params':..,'metrics':..}), ...]}
        Retorna best_params=None si no encuentra parámetros válidos
    """
    if db is None:
        db = BettingDatabase()
    config = load_config()
    # Para evaluar necesitamos matches históricos con odds y resultado.
    # Aquí usamos raw_match_results + canonical_odds join simplificado.
    # Fallback: si no hay suficientes datos, retornamos vacío.
    matches = []
    try:
        db.connect()
        cur = db.conn.cursor()
        cur.execute('''SELECT c.match_id, c.sport, c.league, c.home_team, c.away_team, c.match_date,
                              c.home_win_odds, c.away_win_odds, c.draw_odds
                       FROM canonical_odds c
                       JOIN raw_match_results r ON c.match_id=r.match_id
                       ORDER BY c.match_date DESC LIMIT 1000''')
        rows = cur.fetchall()
        for r in rows:
            odds = {
                'home_win': r['home_win_odds'],
                'away_win': r['away_win_odds'],
                'draw': r['draw_odds']
            }
            matches.append({
                'match_id': r['match_id'],
                'sport': r['sport'],
                'league': r['league'],
                'home_team': r['home_team'],
                'away_team': r['away_team'],
                'match_date': r['match_date'],
                'odds': odds
            })
    except Exception as e:
        print(f"⚠️ Error cargando partidos históricos para autotuning: {e}")
        return {'best_params': None, 'best_metrics': None, 'tested': [], 'error': str(e)}

    if not matches:
        print("⚠️ No hay partidos históricos con resultados y odds. Ejecuta bootstrap_historical_data.py primero.")
        return {'best_params': None, 'best_metrics': None, 'tested': [], 'error': 'No historical data available'}

    # Reducir el tamaño del dataset para acelerar
    # Ordenar por fecha descendente y tomar muestra reciente
    try:
        matches.sort(key=lambda m: m.get('match_date', ''), reverse=True)
    except Exception:
        pass
    if sample_size and len(matches) > sample_size:
        matches = matches[:sample_size]

    print(f"🔍 Autotuning con {len(matches)} partidos históricos...")

    predictor = MatchPredictor()

    # Validar que está usando modelo calibrado
    if hasattr(predictor, 'is_calibrated') and predictor.is_calibrated:
        print("✅ Usando modelo CALIBRADO para autotuning")
        print(f"   Modelo: {predictor.soccer_model.__class__.__name__}")
    else:
        print("⚠️ WARNING: Usando modelo SIN calibrar - resultados no óptimos")
        print("   Ejecuta: python train_advanced_model.py primero")
        print("   Continuando con modelo antiguo...")

    best_score = -999
    best_params = None
    best_metrics = None
    tested = []
    all_values = list(itertools.product(*PARAM_GRID.values()))
    # Limitar número de combinaciones
    if max_combinations and len(all_values) > max_combinations:
        all_values = all_values[:max_combinations]
    
    print(f"📊 Evaluando {len(all_values)} combinaciones de parámetros...")
    
    start = time.time()
    for i, values in enumerate(all_values, 1):
        # Corte por tiempo
        if time.time() - start > time_limit_sec:
            print(f"⏱️ Tiempo límite alcanzado ({time_limit_sec}s). Evaluadas {i-1} combinaciones.")
            break
        params = dict(zip(PARAM_GRID.keys(), values))
        metrics = evaluate_params(params, matches, predictor, db)
        tested.append({'params': params, 'metrics': metrics})
        metric_score = metrics.get('score', metrics.get('roi', -999))
        
        # Progress feedback cada 5 combinaciones
        if i % 5 == 0:
            print(f"  [{i}/{len(all_values)}] Evaluando... mejor score hasta ahora: {best_score:.3f}")
        
        if metric_score > best_score and metrics['n'] > 20:  # menor umbral para permitir pruebas tempranas
            best_score = metric_score
            best_params = params
            best_metrics = metrics
            print(f"  ✓ Nueva mejor configuración encontrada! Score: {best_score:.3f}, ROI: {metrics['roi']:.2%}, N: {metrics['n']}")
    
    elapsed = time.time() - start
    print(f"⏱️ Autotuning completado en {elapsed:.1f}s")
    
    if best_params:
        print(f"✅ Mejores parámetros: {best_params}")
        print(f"   ROI: {best_metrics['roi']:.2%}, Win Rate: {best_metrics['win_rate']:.1%}, Score: {best_score:.3f}, N: {best_metrics['n']}")
        # No guardar directamente en config.yaml desde aquí si se usa UI; la UI decidirá.
        return {'best_params': best_params, 'best_metrics': best_metrics, 'tested': tested}
    else:
        print(f"⚠️ No se encontraron parámetros que cumplan el criterio mínimo (n > 20)")
        print(f"   Evaluadas {len(tested)} combinaciones")
        return {'best_params': None, 'best_metrics': None, 'tested': tested}

def main():
    config = load_config()
    # Carga partidos históricos con odds y resultados
    db = BettingDatabase()
    # Adaptamos matches para predictor usando canonical_odds + raw_match_results
    db.connect()
    matches = []
    cur = db.conn.cursor()
    cur.execute('''SELECT c.match_id, c.sport, c.league, c.home_team, c.away_team, c.match_date,
                          c.home_win_odds, c.away_win_odds, c.draw_odds
                   FROM canonical_odds c
                   JOIN raw_match_results r ON c.match_id=r.match_id
                   ORDER BY c.match_date DESC LIMIT 500''')
    for r in cur.fetchall():
        odds = {
            'home_win': r['home_win_odds'],
            'away_win': r['away_win_odds'],
            'draw': r['draw_odds']
        }
        matches.append({
            'match_id': r['match_id'], 'sport': r['sport'], 'league': r['league'],
            'home_team': r['home_team'], 'away_team': r['away_team'], 'match_date': r['match_date'], 'odds': odds
        })
    predictor = MatchPredictor()
    best_score = -999
    best_params = None
    best_metrics = None
    # Grid search
    for values in itertools.product(*PARAM_GRID.values()):
        params = dict(zip(PARAM_GRID.keys(), values))
        metrics = evaluate_params(params, matches, predictor)
        print(f"Tested {params} -> ROI: {metrics['roi']:.2%}, Win rate: {metrics['win_rate']:.1%}, N={metrics['n']}")
        # Usa ROI como score principal
        if metrics['roi'] > best_score and metrics['n'] > 50:
            best_score = metrics['roi']
            best_params = params
            best_metrics = metrics
    if best_params:
        print(f"\nBest params: {best_params} -> ROI: {best_metrics['roi']:.2%}, Win rate: {best_metrics['win_rate']:.1%}, N={best_metrics['n']}")
        # Actualiza config.yaml
        config['picks'].update(best_params)
        save_config(config)
        print("config.yaml actualizado con los mejores parámetros.")
    else:
        print("No se encontró un set óptimo con suficiente volumen de apuestas.")

if __name__ == "__main__":
    main()
