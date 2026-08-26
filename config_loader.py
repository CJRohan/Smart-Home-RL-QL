"""Read model parameters from config.json."""

import json
from pathlib import Path


class ConfigLoader:
    """Loads the configuration so the other model classes can use it."""

    def __init__(self, filename="config.json"):
        # The config file sits in the same folder as this Python file.
        self.config_path = Path(__file__).with_name(filename)

    def load(self):
        # Open the JSON file and turn its text into a Python dictionary.
        with self.config_path.open("r", encoding="utf-8") as file:
            return json.load(file)
