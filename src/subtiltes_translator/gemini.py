import pathlib
import tempfile
from typing import Any, Callable

import ass
import google.generativeai as genai
import srt
from google.generativeai.types import GenerationConfigDict

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
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }  # type: ignore

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-exp-0827",
        generation_config=generation_config,
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
            f"你正在尝试进行翻译一个美国电视剧剧集的{from_language} {file_type.value} 字幕，翻译成{target_language}。影片主要描述日常生活，其他的一些美式俚语等内容。需要你保持原有文件格式进行输出，并对输出内容中的中文进行润色，润色时需要根据文中内容矫正名词。无需进行说明",
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

    output_file = pathlib.Path(target_dir).joinpath(
        f"{pathlib.Path(files[0]).stem}_{target_language}.{file_type.value.lower()}"
    )
    merge_subtitle_files(file_type, translated_srt, output_file)