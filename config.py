import os, json

JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "offensive_words.json")
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
    OFFENSIVE_WORDS = data.get("categories", {}).get("insults", [])