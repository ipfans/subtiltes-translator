import os
import tempfile

import flet as ft

from src.config import get_api_key, load_config, set_api_key
from src.subtiltes_translator.gemini import translate_subtitle


def main(page: ft.Page):
    page.title = "字幕翻译软件"
    page.window.width = 600
    page.window.height = 350
    page.padding = 20

    tmp = tempfile.mkdtemp()
    config = load_config()

    def create_settings_page(disable_back: bool = False):
        openai_key = ft.TextField(
            label="OpenAI API Key",
            value=config["openai_key"],
            disabled=True,
        )
        claude_key = ft.TextField(
            label="Claude API Key",
            value=config["claude_key"],
            disabled=True,
        )
        gemini_key = ft.TextField(
            label="Google Gemini API Key", value=config["gemini_key"]
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

        save_button = ft.ElevatedButton("保存设置", on_click=save_settings)
        return_button = ft.IconButton(
            icon=ft.icons.ARROW_BACK,
            tooltip="返回主页",
            on_click=return_to_main,
        )

        col = [
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

        return ft.Column(col)

    # 判断config所有内容为空时，跳转设置页面
    if (
        not config["openai_key"]
        and not config["claude_key"]
        and not config["gemini_key"]
    ):
        page.clean()
        page.add(create_settings_page(disable_back=True))
        return

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
        width=200,
    )

    def update_engine_dropdown():
        engine_dropdown.options = []
        if get_api_key("openai"):
            engine_dropdown.options.append(ft.dropdown.Option("OpenAI"))
        if get_api_key("claude"):
            engine_dropdown.options.append(ft.dropdown.Option("Claude"))
        if get_api_key("gemini"):
            engine_dropdown.options.append(ft.dropdown.Option("Google Gemini"))
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
        width=200,
    )

    progress_bar = ft.ProgressBar(width=400, visible=False)

    def on_subtitle_result(e: ft.FilePickerResultEvent):
        if e.files:
            home_dir = os.path.expanduser("~")
            relative_paths = []
            for file in e.files:
                if file.path.startswith("/Volumes/"):
                    path = "/" + "/".join(file.path.split("/")[3:])
                else:
                    path = file.path
                relative_path = os.path.relpath(path, home_dir)
                if relative_path.startswith(".."):
                    relative_paths.append(path)
                else:
                    relative_paths.append(f"~/{relative_path}")
            subtitle_text.value = ", ".join(relative_paths)
        else:
            subtitle_text.value = "未选择文件"
        page.update()

    def on_output_result(e: ft.FilePickerResultEvent):
        if e.path:
            path = e.path
            if e.path.startswith("/Volumes/"):
                path = "/" + "/".join(path.split("/")[3:])
            home_dir = os.path.expanduser("~")
            relative_path = os.path.relpath(path, home_dir)
            if relative_path.startswith(".."):
                output_text.value = path
            else:
                output_text.value = f"~/{relative_path}"
        else:
            output_text.value = "未选择目录"
        page.update()

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

            translate_subtitle(
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
    )
    subtitle_text = ft.Text()

    output_picker = ft.FilePicker(on_result=on_output_result)
    page.overlay.append(output_picker)
    output_button = ft.ElevatedButton(
        "选择输出目录",
        icon=ft.icons.FOLDER,
        on_click=lambda _: output_picker.get_directory_path(),
    )
    output_text = ft.Text()

    translate_button = ft.ElevatedButton("翻译", on_click=translate)
    reset_button = ft.ElevatedButton("重置", on_click=reset)

    settings_button = ft.IconButton(icon=ft.icons.SETTINGS, on_click=open_settings)

    page.add(
        ft.Row(
            [engine_dropdown, settings_button],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        subtitle_language_dropdown,
        ft.Column(
            [
                ft.Row([subtitle_button, subtitle_text]),
                ft.Row([output_button, output_text]),
                ft.Row(
                    [translate_button, reset_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                progress_bar,
            ]
        ),
    )


ft.app(target=main)
