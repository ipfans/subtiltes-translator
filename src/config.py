import json
import os
from typing import TypedDict

CONFIG_FILE = "config.json"


class ConfigDict(TypedDict):
    openai_key: str
    claude_key: str
    gemini_key: str
    prompt: str


def load_config() -> ConfigDict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return ConfigDict(**json.load(f))

    return ConfigDict(
        openai_key="",
        claude_key="",
        gemini_key="",
        prompt="你正在尝试进行翻译一个美国电视剧剧集的英语 SRT 字幕，翻译成中文。影片是 1965年的 Get Smart，影片包含谍战内容，日常生活，其他的一些美式俚语等内容。音频采用转录生成，你需要根据前后文修正转录错误的内容，并进行翻译。翻译要求根据上下文修正成中文母语者熟悉的表达方式，需要你保持原有文件格式进行输出，并对输出内容中的中文进行润色，润色时需要根据前后相关内容矫正名词。无需进行说明，保证原意不变，不生成任何 SRT 文件中不存在的内容",
    )


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


def get_prompt() -> str:
    config = load_config()
    return config.get("prompt", "")


def set_prompt(prompt: str):
    config = load_config()
    config["prompt"] = prompt
    save_config(config)
