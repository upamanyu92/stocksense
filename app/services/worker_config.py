import json
import logging
import os
from typing import Dict, Any

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'worker_config.json')


def load_config() -> Dict[str, Any]:
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load worker config: {e}")
    return {'background_worker_enabled': False, 'digest_email_enabled': False}


def save_config(config: Dict[str, Any]):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f)

