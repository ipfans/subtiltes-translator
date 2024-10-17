import os
import pathlib
import tempfile

import flet as ft

from src.config import get_api_key, get_prompt, load_config, set_api_key, set_prompt
from src.subtiltes_translator.gemini import translate_subtitle


def file_path_to_relative(path: str) -> str:
    home_dir = os.path.expanduser("~")
    if os.name == "posix":  # For macOS and Linux
        if path.startswith("/Volumes/"):
            path = "/" + "/".join(path.split("/")[3:])
    relative_path = os.path.relpath(path, home_dir)
    if relative_path.startswith("..") or os.name == "nt":  # For Windows
        return path
    else:
        return os.path.join("~", relative_path)


def main(page: ft.Page):
    page.title = "字幕翻译软件"
    page.window_width = 600
    page.window_height = 650
    page.padding = 30
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed="blue")

    tmp = tempfile.mkdtemp()
    config = load_config()

    def create_settings_page(disable_back: bool = False):
        openai_key = ft.TextField(
            label="OpenAI API Key",
            value=config["openai_key"],
            disabled=True,
            width=400,
        )
        claude_key = ft.TextField(
            label="Claude API Key",
            value=config["claude_key"],
            disabled=True,
            width=400,
        )
        gemini_key = ft.TextField(
            label="Google Gemini API Key",
            value=config["gemini_key"],
            width=400,
        )

        def save_settings(e):
            set_api_key("openai", openai_key.value or "")
            set_api_key("claude", claude_key.value or "")
            set_api_key("gemini", gemini_key.value or "")

            if not disable_back:
                page.snack_bar = ft.SnackBar(content=ft.Text("设置已保存"))
                page.snack_bar.open = True
                page.update()
                update_engine_dropdown()
            else:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("重启软件以应用设置"),
                )
                page.snack_bar.open = True
                page.update()

        def return_to_main(e):
            page.clean()
            main(page)

        save_button = ft.ElevatedButton(
            "保存设置",
            on_click=save_settings,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        )
        return_button = ft.IconButton(
            icon=ft.icons.ARROW_BACK,
            tooltip="返回主页",
            on_click=return_to_main,
        )

        col = [
            ft.Text("API 设置", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            openai_key,
            claude_key,
            gemini_key,
            save_button,
        ]
        if not disable_back:
            col.insert(
                0,
                ft.Row([return_button], alignment=ft.MainAxisAlignment.START),
            )

        return ft.Container(
            content=ft.Column(col, spacing=20),
            padding=30,
            border_radius=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
        )

    def on_engine_change(e):
        selected_engine = e.control.value
        if selected_engine:
            api_key = get_api_key(selected_engine)
            if not api_key:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"请先设置 {selected_engine} 的 API Key"),
                    action="去设置",
                )
                page.snack_bar.open = True
                page.update()

                def on_snackbar_action(e):
                    open_settings(None)

                page.snack_bar.on_action = on_snackbar_action

    engine_dropdown = ft.Dropdown(
        label="选择翻译引擎",
        options=[],
        width=300,
        border_radius=10,
    )

    def update_engine_dropdown():
        engine_dropdown.options = []
        default_engine = None
        if get_api_key("openai"):
            engine_dropdown.options.append(ft.dropdown.Option("OpenAI"))
            if not default_engine:
                default_engine = "OpenAI"
        if get_api_key("claude"):
            engine_dropdown.options.append(ft.dropdown.Option("Claude"))
            if not default_engine:
                default_engine = "Claude"
        if get_api_key("gemini"):
            engine_dropdown.options.append(ft.dropdown.Option("Google Gemini"))
            if not default_engine:
                default_engine = "Google Gemini"
        if default_engine:
            engine_dropdown.value = default_engine
        page.update()

    update_engine_dropdown()

    subtitle_language_dropdown = ft.Dropdown(
        label="选择字幕语言",
        options=[
            ft.dropdown.Option("英语"),
            ft.dropdown.Option("日语"),
            ft.dropdown.Option("韩语"),
            ft.dropdown.Option("法语"),
            ft.dropdown.Option("德语"),
            ft.dropdown.Option("西班牙语"),
        ],
        width=300,
        border_radius=10,
        value="英语",
    )

    progress_bar = ft.ProgressBar(width=600, height=10, visible=False)

    def on_subtitle_result(e: ft.FilePickerResultEvent):
        if e.files:
            relative_paths = []
            for file in e.files:
                relative_paths.append(file_path_to_relative(file.path))
            subtitle_text.value = ", ".join(relative_paths)
            output_text.value = file_path_to_relative(
                str(pathlib.Path(e.files[0].path).parent)
            )
        else:
            subtitle_text.value = "未选择文件"
        page.update()

    def on_output_result(e: ft.FilePickerResultEvent):
        if e.path:
            output_text.value = file_path_to_relative(e.path)
        else:
            output_text.value = "未选择目录"
        page.update()

    default_prompt = get_prompt()

    # 创建 prompt 输入窗口
    def on_prompt_change(e):
        if not prompt_input.value:
            prompt_input.value = default_prompt
            page.update()

    prompt_input = ft.TextField(
        label="翻译提示",
        value=default_prompt,
        multiline=True,
        min_lines=3,
        max_lines=3,
        width=600,
        on_change=on_prompt_change,
    )

    def translate(e):
        if not engine_dropdown.value:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("请先选择翻译引擎"),
            )
            page.snack_bar.open = True
            page.update()
            return
        if not subtitle_text.value:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("请先选择字幕语言"),
            )
            page.snack_bar.open = True
            page.update()
            return
        if engine_dropdown.value == "Google Gemini":
            if (
                not subtitle_text.value
                or not output_text.value
                or not subtitle_language_dropdown.value
                or output_text.value == "未选择目录"
                or subtitle_text.value == "未选择文件"
            ):
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("请先选择字幕文件和输出目录"),
                )
                page.snack_bar.open = True
                page.update()
                return

            settings_button.disabled = True
            reset_button.disabled = True
            translate_button.disabled = True
            progress_bar.visible = True
            page.update()

            def update_progress(current, total):
                progress = current / total
                progress_bar.value = progress
                page.update()

            set_prompt(prompt_input.value or default_prompt)

            translate_subtitle(
                prompt=prompt_input.value or default_prompt,
                subtitle_file=subtitle_text.value,
                target_language="中文",
                from_language=subtitle_language_dropdown.value,
                target_dir=output_text.value,
                api_key=get_api_key("gemini"),
                tmp_dir=tmp,
                progress_callback=update_progress,
            )

            progress_bar.visible = False
            page.update()

            page.snack_bar = ft.SnackBar(content=ft.Text("翻译完成"))
            page.snack_bar.open = True
            settings_button.disabled = False
            reset_button.disabled = False
            translate_button.disabled = False
            page.update()

    def reset(e):
        subtitle_text.value = ""
        output_text.value = ""
        engine_dropdown.value = None
        subtitle_language_dropdown.value = None
        page.update()

    def open_settings(e):
        page.clean()
        page.add(create_settings_page())

    subtitle_picker = ft.FilePicker(on_result=on_subtitle_result)
    page.overlay.append(subtitle_picker)
    subtitle_button = ft.ElevatedButton(
        "选择字幕文件",
        icon=ft.icons.UPLOAD_FILE,
        on_click=lambda _: subtitle_picker.pick_files(
            allowed_extensions=["srt", "ass"], allow_multiple=False
        ),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )
    subtitle_text = ft.Text(size=14)

    output_picker = ft.FilePicker(on_result=on_output_result)
    page.overlay.append(output_picker)
    output_button = ft.ElevatedButton(
        "选择输出目录",
        icon=ft.icons.FOLDER,
        on_click=lambda _: output_picker.get_directory_path(),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )
    output_text = ft.Text(size=14)

    translate_button = ft.ElevatedButton(
        "翻译",
        on_click=translate,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        width=150,
    )
    reset_button = ft.ElevatedButton(
        "重置",
        on_click=reset,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        width=150,
    )

    settings_button = ft.IconButton(
        icon=ft.icons.SETTINGS,
        on_click=open_settings,
        tooltip="设置",
    )

    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("字幕翻译软件", style=ft.TextThemeStyle.HEADLINE_LARGE),
                    ft.Row(
                        [engine_dropdown, settings_button],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    subtitle_language_dropdown,
                    prompt_input,
                    ft.Column(
                        [
                            ft.Row([subtitle_button, subtitle_text]),
                            ft.Row([output_button, output_text]),
                            ft.Row(
                                [translate_button, reset_button],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            progress_bar,
                        ],
                        spacing=20,
                    ),
                ],
                spacing=30,
            ),
            padding=20,
            border_radius=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
        )
    )

    # 判断config所有内容为空时，跳转设置页面
    if (
        not config["openai_key"]
        and not config["claude_key"]
        and not config["gemini_key"]
    ):
        open_settings(None)


ft.app(target=main)
