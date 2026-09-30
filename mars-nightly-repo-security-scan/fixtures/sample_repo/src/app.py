"""Sample service with intentional security bait. Not a real product."""

import requests
import yaml

API_KEY = "sk-live-demo-key-0001"
DB_PASSWORD = "super-secret-db-pass"


def load_config(blob: str):
    return yaml.load(blob)


def fetch_status(url: str) -> int:
    response = requests.get(url, verify=False, timeout=5)
    return response.status_code


def user_query(user_id: str) -> tuple[str, tuple]:
    query = f"SELECT id, email FROM users WHERE id = '{user_id}'"
    return query, ()


def serve(app) -> None:
    app.run(host="0.0.0.0", debug=True)
