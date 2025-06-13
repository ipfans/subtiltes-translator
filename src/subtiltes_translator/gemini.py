import os
import pathlib
import tempfile
from typing import Any, Callable

import ass
import google.generativeai as genai
import srt
from google.generativeai.types import (
    GenerationConfigDict,
    HarmBlockThreshold,
    HarmCategory,
)

from .utils import get_file_type, merge_subtitle_files, split_subtitle_file


def generate_content(
    model: Any,
    contents: Any,
    generation_config: GenerationConfigDict,
    tmp_file: pathlib.Path,
) -> list[Any]:
    """
    生成内容
    """
    # 检查临时文件是否存在
    if tmp_file.exists():
        with tmp_file.open("r", encoding="utf-8") as f:
            data = srt.parse(f.read())
        return [line for line in data]

    # 如果临时文件不存在，则进行翻译
    response = model.generate_content(
        contents,
        generation_config=generation_config,
    )
    text = response.text
    # 如果 text 包含 "```" 则进行处理，仅包含```包裹的内容
    if "```" in text:
        text = text.split("```")[1]

    # 保存翻译结果到临时文件
    with tmp_file.open("w", encoding="utf-8") as f:
        f.write(text)

    data = srt.parse(text)
    return [line for line in data]


def translate_subtitle(
    prompt: str,
    subtitle_file: str,
    target_dir: str,
    from_language: str,
    target_language: str,
    api_key: str,
    tmp_dir: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:
    """
    翻译字幕
    """
    subtitle_file = os.path.expanduser(subtitle_file)
    target_dir = os.path.expanduser(target_dir)
    genai.configure(api_key=api_key)
    if tmp_dir is None:
        tmp = tempfile.mkdtemp()
    else:
        tmp = tmp_dir
    file_type = get_file_type(subtitle_file)

    generation_config: GenerationConfigDict = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 65536,
        "response_mime_type": "text/plain",
        "thinking_config": {
            "thinking_budget": 0,
        },
    }  # type: ignore

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-05-20",
        generation_config=generation_config,
        safety_settings={
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        },
    )

    files = split_subtitle_file(file_type, subtitle_file, tmp)

    translated_srt = []
    total_files = len(files)
    for index, file in enumerate(files, 1):
        sample_file = genai.upload_file(
            path=file, display_name="SRT subtitles", mime_type="text/plain"
        )

        fn = pathlib.Path(file)
        fn = fn.with_name(f"{fn.stem}_zh.{fn.suffix}")
        contents = [
            prompt,
            sample_file,
        ]
        try:
            srts = generate_content(model, contents, generation_config, fn)
        except srt.SRTParseError as e:
            print(f"Error parsing SRT file: {e}")
            srts = generate_content(model, contents, generation_config, fn)
        translated_srt.extend(srts)
        sample_file.delete()
        if progress_callback:
            progress_callback(index, total_files)

    output_file = (
        pathlib.Path(target_dir)
        .joinpath(
            f"{pathlib.Path(subtitle_file).stem}_{target_language}.{file_type.value.lower()}"
        )
        .absolute()
    )
    merge_subtitle_files(file_type, translated_srt, output_file)
