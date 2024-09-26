import enum
import os
import pathlib
from typing import Any

import srt


class FileType(enum.Enum):
    SRT = "srt"
    ASS = "ass"


def get_file_type(file_path: str) -> FileType:
    """
    根据文件扩展名判断文件类型
    """
    if file_path.endswith(".srt"):
        return FileType.SRT
    elif file_path.endswith(".ass"):
        return FileType.ASS
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


def split_subtitle_file(
    file_type: FileType, subtitle_file: str, tmp_dir: str
) -> list[str]:
    """
    将字幕文件分割为单个文件
    """
    if file_type == FileType.SRT:
        return split_srt_file(subtitle_file, tmp_dir)
    else:
        raise NotImplementedError("ASS 文件分割未实现")


def split_srt_file(subtitle_file: str, tmp_dir: str) -> list[str]:
    """
    将 srt 文件分割为单个文件
    """
    # 加载 srt 文件
    with open(os.path.expanduser(subtitle_file), "r", encoding="utf-8") as f:
        data = f.read()
    srt_file = srt.parse(data)
    srt_data = [line for line in srt_file]
    filename = pathlib.Path(subtitle_file).stem
    files = []
    for i in range(0, len(srt_data), 100):
        fn = pathlib.Path(tmp_dir).joinpath(f"{filename}_{i+1:08d}.srt")
        data = srt.compose(srt_data[i : i + 100])
        with fn.open("w") as f:
            f.write(data)
        files.append(fn)
    return files


def merge_subtitle_files(
    file_type: FileType,
    subtitle_files: list[Any],
    target_file: pathlib.Path,
):
    """
    将翻译后的字幕文件合并为一个文件，subtitle_files 为翻译后的元素
    """
    if file_type == FileType.SRT:
        return merge_srt_files(subtitle_files, target_file)
    else:
        raise NotImplementedError("ASS 文件合并未实现")


def merge_srt_files(subtitle_files: list[Any], target_file: pathlib.Path):
    """
    将翻译后的 srt 文件合并为一个文件
    """
    with target_file.open("w", encoding="utf-8") as f:
        f.write(srt.compose(subtitle_files))
