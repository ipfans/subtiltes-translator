import json
import os
from typing import TypedDict

CONFIG_FILE = "config.json"


class ConfigDict(TypedDict):
    openai_key: str
    claude_key: str
    gemini_key: str


def load_config() -> ConfigDict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return ConfigDict(**json.load(f))

    return ConfigDict(openai_key="", claude_key="", gemini_key="")


def save_config(config: ConfigDict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


def get_api_key(engine: str) -> str:
    config = load_config()
    return config.get(f"{engine.lower()}_key", "")


def set_api_key(engine: str, key: str):
    config = load_config()
    config[f"{engine.lower()}_key"] = key
    save_config(config)
