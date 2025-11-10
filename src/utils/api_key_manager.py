"""
API Key Manager - Gestiona pool de API keys con rotación automática
"""

import os
from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger
import json


class APIKeyManager:
    """
    Gestor inteligente de pool de API keys
    - Rotación automática cuando se agotan requests
    - Tracking de uso por key
    - Fallback a siguiente key disponible
    """

    def __init__(self, keys_env_var: str = "ODDS_API_KEYS"):
        """
        Args:
            keys_env_var: Variable de entorno con las keys separadas por coma
        """
        self.keys_str = os.getenv(keys_env_var, "")
        self.keys = [k.strip() for k in self.keys_str.split(',') if k.strip()]

        if not self.keys:
            logger.warning(f"No API keys found in {keys_env_var}")
            self.keys = []

        self.current_index = 0
        self.usage_file = "data/api_keys_usage.json"
        self.usage_data = self._load_usage_data()

        logger.info(f"API Key Manager initialized with {len(self.keys)} keys")

    def _load_usage_data(self) -> dict:
        """Carga datos de uso desde archivo JSON"""
        try:
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    # Convertir strings de fecha a datetime
                    for key_hash, info in data.items():
                        if 'reset_date' in info:
                            info['reset_date'] = datetime.fromisoformat(info['reset_date'])
                    return data
        except Exception as e:
            logger.debug(f"Could not load usage data: {e}")

        return {}

    def _save_usage_data(self):
        """Guarda datos de uso a archivo JSON"""
        try:
            os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)
            # Convertir datetime a string para JSON
            save_data = {}
            for key_hash, info in self.usage_data.items():
                save_data[key_hash] = {
                    'requests_used': info.get('requests_used', 0),
                    'requests_remaining': info.get('requests_remaining', 500),
                    'reset_date': info.get('reset_date', datetime.now()).isoformat()
                }

            with open(self.usage_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save usage data: {e}")

    def _get_key_hash(self, key: str) -> str:
        """Genera hash de la key para tracking (primeros 8 chars)"""
        return key[:8] if len(key) >= 8 else key

    def _update_key_usage(self, key: str, requests_remaining: int):
        """Actualiza uso de una key específica"""
        key_hash = self._get_key_hash(key)

        if key_hash not in self.usage_data:
            self.usage_data[key_hash] = {
                'requests_used': 0,
                'requests_remaining': 500,
                'reset_date': datetime.now() + timedelta(days=30)
            }

        self.usage_data[key_hash]['requests_remaining'] = requests_remaining
        self.usage_data[key_hash]['requests_used'] = 500 - requests_remaining

        self._save_usage_data()

        logger.debug(f"Key {key_hash}: {requests_remaining} requests remaining")

    def _check_reset_dates(self):
        """Verifica si alguna key debe resetear su contador mensual"""
        now = datetime.now()
        for key_hash, info in self.usage_data.items():
            reset_date = info.get('reset_date')
            if reset_date and now >= reset_date:
                # Reset mensual
                self.usage_data[key_hash]['requests_remaining'] = 500
                self.usage_data[key_hash]['requests_used'] = 0
                self.usage_data[key_hash]['reset_date'] = now + timedelta(days=30)
                logger.info(f"Key {key_hash} reset: 500 requests available")
                self._save_usage_data()

    def get_current_key(self) -> Optional[str]:
        """
        Obtiene la key actual para usar

        Returns:
            API key activa o None si no hay keys disponibles
        """
        if not self.keys:
            logger.error("No API keys available")
            return None

        self._check_reset_dates()

        # Intentar encontrar una key con requests disponibles
        attempts = 0
        while attempts < len(self.keys):
            key = self.keys[self.current_index]
            key_hash = self._get_key_hash(key)

            # Verificar si tiene requests disponibles
            if key_hash in self.usage_data:
                remaining = self.usage_data[key_hash].get('requests_remaining', 500)
                if remaining > 10:  # Dejar margen de 10 requests
                    logger.debug(f"Using key {key_hash} ({remaining} requests left)")
                    return key
                else:
                    logger.warning(f"Key {key_hash} exhausted ({remaining} left), rotating...")
                    self.rotate_key()
            else:
                # Key nueva, asumir 500 requests disponibles
                return key

            attempts += 1

        logger.error("All API keys exhausted!")
        return self.keys[self.current_index]  # Devolver alguna como fallback

    def rotate_key(self):
        """Rota a la siguiente key en el pool"""
        self.current_index = (self.current_index + 1) % len(self.keys)
        new_key_hash = self._get_key_hash(self.keys[self.current_index])
        logger.info(f"Rotated to key {new_key_hash}")

    def update_usage(self, requests_remaining: int):
        """
        Actualiza el contador de requests de la key actual

        Args:
            requests_remaining: Requests restantes reportados por la API
        """
        if not self.keys:
            return

        current_key = self.keys[self.current_index]
        self._update_key_usage(current_key, requests_remaining)

        # Si quedan pocos requests, rotar automáticamente
        if requests_remaining < 10:
            logger.warning(f"Key running low ({requests_remaining} left), rotating...")
            self.rotate_key()

    def get_pool_status(self) -> dict:
        """
        Obtiene estado completo del pool de keys

        Returns:
            Dict con información de todas las keys
        """
        self._check_reset_dates()

        status = {
            'total_keys': len(self.keys),
            'current_key_index': self.current_index,
            'keys': []
        }

        total_remaining = 0

        for i, key in enumerate(self.keys):
            key_hash = self._get_key_hash(key)
            usage = self.usage_data.get(key_hash, {
                'requests_used': 0,
                'requests_remaining': 500,
                'reset_date': datetime.now() + timedelta(days=30)
            })

            remaining = usage.get('requests_remaining', 500)
            total_remaining += remaining

            status['keys'].append({
                'index': i,
                'key_hash': key_hash,
                'is_current': i == self.current_index,
                'requests_used': usage.get('requests_used', 0),
                'requests_remaining': remaining,
                'reset_date': usage.get('reset_date', datetime.now()).strftime('%Y-%m-%d'),
                'status': 'active' if remaining > 50 else 'low' if remaining > 10 else 'exhausted'
            })

        status['total_requests_remaining'] = total_remaining
        status['total_requests_available'] = len(self.keys) * 500

        return status


if __name__ == "__main__":
    # Test del manager
    manager = APIKeyManager()

    print("\n=== API Key Manager Test ===\n")

    # Obtener key actual
    current = manager.get_current_key()
    print(f"Current key: {current[:8] if current else 'None'}...\n")

    # Simular uso
    manager.update_usage(450)
    manager.update_usage(200)
    manager.update_usage(5)  # Debería rotar

    # Ver estado del pool
    status = manager.get_pool_status()
    print("\nPool Status:")
    print(f"Total keys: {status['total_keys']}")
    print(f"Total requests remaining: {status['total_requests_remaining']}/{status['total_requests_available']}")
    print(f"\nKeys:")
    for key_info in status['keys']:
        marker = ">>> " if key_info['is_current'] else "    "
        print(f"{marker}Key {key_info['key_hash']}: {key_info['requests_remaining']} requests ({key_info['status']})")
