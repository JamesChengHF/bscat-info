from ujson import load
import os

db_config_json = os.path.join(os.path.dirname(__file__), 'config.json')

with open(db_config_json, 'r') as f:
    db_config = load(f)['database']
