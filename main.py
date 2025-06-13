import os
import pathlib
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from src.config import get_api_key, get_prompt, load_config, set_api_key, set_prompt
from src.subtiltes_translator.gemini import translate_subtitle


class SupportedLanguage(Enum):
    """Supported subtitle languages."""

    ENGLISH = "英语"
    JAPANESE = "日语"
    KOREAN = "韩语"
    FRENCH = "法语"
    GERMAN = "德语"
    SPANISH = "西班牙语"


class TranslationEngine(Enum):
    """Supported translation engines."""

    OPENAI = "OpenAI"
    CLAUDE = "Claude"
    GEMINI = "Google Gemini"


@dataclass
class TranslationRequest:
    """Data class for translation requests."""

    engine: str
    subtitle_file: str
    output_directory: str
    source_language: str
    target_language: str = "中文"
    prompt: Optional[str] = None


class PathUtils:
    """Utility class for path operations."""

    @staticmethod
    def to_relative_path(path: str) -> str:
        """Convert absolute path to relative path from home directory."""
        home_dir = os.path.expanduser("~")

        if os.name == "posix" and path.startswith("/Volumes/"):
            path = "/" + "/".join(path.split("/")[3:])

        relative_path = os.path.relpath(path, home_dir)

        if relative_path.startswith("..") or os.name == "nt":
            return path
        else:
            return os.path.join("~", relative_path)


class UIStyleConfig:
    """Centralized UI styling configuration."""

    BUTTON_RADIUS = 10
    CONTAINER_RADIUS = 10
    COMPONENT_WIDTH = 600
    DROPDOWN_WIDTH = 300
    BUTTON_WIDTH = 150
    SPACING_SMALL = 20
    SPACING_MEDIUM = 30
    PADDING = 30

    @staticmethod
    def button_style() -> ft.ButtonStyle:
        """Standard button style."""
        return ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=UIStyleConfig.BUTTON_RADIUS)
        )

    @staticmethod
    def container_style() -> Dict[str, Any]:
        """Standard container style."""
        return {
            "border_radius": UIStyleConfig.CONTAINER_RADIUS,
            "bgcolor": ft.colors.SURFACE_VARIANT,
            "padding": UIStyleConfig.SPACING_SMALL,
        }


class NotificationManager:
    """Manages notifications and snackbars."""

    def __init__(self, page: ft.Page):
        self.page = page

    def show_error(
        self,
        message: str,
        action_text: Optional[str] = None,
        on_action: Optional[Callable] = None,
    ) -> None:
        """Show error notification."""
        snack_bar = ft.SnackBar(
            content=ft.Text(message), action=action_text if action_text else None
        )
        if on_action:
            snack_bar.on_action = on_action

        self.page.snack_bar = snack_bar
        self.page.snack_bar.open = True
        self.page.update()

    def show_success(self, message: str) -> None:
        """Show success notification."""
        snack_bar = ft.SnackBar(content=ft.Text(message))
        self.page.overlay.append(snack_bar)
        snack_bar.open = True
        self.page.update()


class ValidationService:
    """Service for validating user inputs."""

    @staticmethod
    def validate_translation_request(request: TranslationRequest) -> List[str]:
        """Validate translation request and return list of errors."""
        errors = []

        if not request.engine:
            errors.append("请先选择翻译引擎")

        if not request.subtitle_file or request.subtitle_file == "未选择文件":
            errors.append("请先选择字幕文件")

        if not request.output_directory or request.output_directory == "未选择目录":
            errors.append("请先选择输出目录")

        if not request.source_language:
            errors.append("请先选择字幕语言")

        return errors


class TranslationService:
    """Service for handling translation operations."""

    def __init__(self, tmp_dir: str):
        self.tmp_dir = tmp_dir

    def translate(
        self,
        request: TranslationRequest,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Execute translation based on engine type."""
        if request.engine == TranslationEngine.GEMINI.value:
            self._translate_with_gemini(request, progress_callback)
        else:
            raise NotImplementedError(
                f"Translation engine {request.engine} not implemented"
            )

    def _translate_with_gemini(
        self,
        request: TranslationRequest,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Translate using Google Gemini."""
        api_key = get_api_key("gemini")
        if not api_key:
            raise ValueError("Gemini API key not configured")

        translate_subtitle(
            prompt=request.prompt or get_prompt(),
            subtitle_file=request.subtitle_file,
            target_language=request.target_language,
            from_language=request.source_language,
            target_dir=request.output_directory,
            api_key=api_key,
            tmp_dir=self.tmp_dir,
            progress_callback=progress_callback,
        )


class EngineManager:
    """Manages available translation engines based on API keys."""

    @staticmethod
    def get_available_engines() -> List[str]:
        """Get list of available engines based on configured API keys."""
        engines = []

        if get_api_key("openai"):
            engines.append(TranslationEngine.OPENAI.value)
        if get_api_key("claude"):
            engines.append(TranslationEngine.CLAUDE.value)
        if get_api_key("gemini"):
            engines.append(TranslationEngine.GEMINI.value)

        return engines

    @staticmethod
    def get_default_engine() -> Optional[str]:
        """Get the first available engine as default."""
        engines = EngineManager.get_available_engines()
        return engines[0] if engines else None


def main(page: ft.Page):
    """Main application entry point."""
    SubtitleTranslatorApp(page)


class SubtitleTranslatorApp:
    """Main application class following Single Responsibility Principle."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.config = load_config()
        self.tmp_dir = tempfile.mkdtemp()
        self.notification_manager = NotificationManager(page)
        self.translation_service = TranslationService(self.tmp_dir)
        self.validation_service = ValidationService()

        # UI Components
        self.engine_dropdown: Optional[ft.Dropdown] = None
        self.language_dropdown: Optional[ft.Dropdown] = None
        self.prompt_input: Optional[ft.TextField] = None
        self.subtitle_text: Optional[ft.Text] = None
        self.output_text: Optional[ft.Text] = None
        self.progress_bar: Optional[ft.ProgressBar] = None
        self.translate_button: Optional[ft.ElevatedButton] = None
        self.reset_button: Optional[ft.ElevatedButton] = None
        self.settings_button: Optional[ft.IconButton] = None

        self._setup_page()
        self._initialize_ui()

    def _setup_page(self) -> None:
        """Configure page settings."""
        self.page.title = "字幕翻译软件"
        self.page.window.width = UIStyleConfig.COMPONENT_WIDTH
        self.page.window.height = 650
        self.page.padding = UIStyleConfig.PADDING
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.theme = ft.Theme(color_scheme_seed="blue")

    def _initialize_ui(self) -> None:
        """Initialize the user interface."""
        self._create_ui_components()
        self._setup_file_pickers()
        self._build_main_layout()

        # Check if configuration is needed
        if self._needs_initial_setup():
            self._show_settings_page()

    def _needs_initial_setup(self) -> bool:
        """Check if initial setup is required."""
        return not any(
            [
                self.config["openai_key"],
                self.config["claude_key"],
                self.config["gemini_key"],
            ]
        )

    def _create_ui_components(self) -> None:
        """Create all UI components."""
        self._create_dropdowns()
        self._create_input_fields()
        self._create_buttons()
        self._create_progress_bar()
        self._create_text_displays()

    def _create_dropdowns(self) -> None:
        """Create dropdown components."""
        self.engine_dropdown = ft.Dropdown(
            label="选择翻译引擎",
            options=[],
            width=UIStyleConfig.DROPDOWN_WIDTH,
            border_radius=UIStyleConfig.BUTTON_RADIUS,
            on_change=self._on_engine_change,
        )

        self.language_dropdown = ft.Dropdown(
            label="选择字幕语言",
            options=[ft.dropdown.Option(lang.value) for lang in SupportedLanguage],
            width=UIStyleConfig.DROPDOWN_WIDTH,
            border_radius=UIStyleConfig.BUTTON_RADIUS,
            value=SupportedLanguage.ENGLISH.value,
        )

        self._update_engine_dropdown()

    def _create_input_fields(self) -> None:
        """Create input field components."""
        default_prompt = get_prompt()
        self.prompt_input = ft.TextField(
            label="翻译提示",
            value=default_prompt,
            multiline=True,
            min_lines=3,
            max_lines=3,
            width=UIStyleConfig.COMPONENT_WIDTH,
            on_change=self._on_prompt_change,
        )

    def _create_buttons(self) -> None:
        """Create button components."""
        self.translate_button = ft.ElevatedButton(
            "翻译",
            on_click=self._on_translate,
            style=UIStyleConfig.button_style(),
            width=UIStyleConfig.BUTTON_WIDTH,
        )

        self.reset_button = ft.ElevatedButton(
            "重置",
            on_click=self._on_reset,
            style=UIStyleConfig.button_style(),
            width=UIStyleConfig.BUTTON_WIDTH,
        )

        self.settings_button = ft.IconButton(
            icon=ft.icons.SETTINGS,
            on_click=self._on_open_settings,
            tooltip="设置",
        )

    def _create_progress_bar(self) -> None:
        """Create progress bar component."""
        self.progress_bar = ft.ProgressBar(
            width=UIStyleConfig.COMPONENT_WIDTH, height=10, visible=False
        )

    def _create_text_displays(self) -> None:
        """Create text display components."""
        self.subtitle_text = ft.Text(size=14)
        self.output_text = ft.Text(size=14)

    def _setup_file_pickers(self) -> None:
        """Setup file picker components."""
        self.subtitle_picker = ft.FilePicker(on_result=self._on_subtitle_result)
        self.output_picker = ft.FilePicker(on_result=self._on_output_result)

        self.page.overlay.extend([self.subtitle_picker, self.output_picker])

        self.subtitle_button = ft.ElevatedButton(
            "选择字幕文件",
            icon=ft.icons.UPLOAD_FILE,
            on_click=lambda _: self.subtitle_picker.pick_files(
                allowed_extensions=["srt", "ass"], allow_multiple=False
            ),
            style=UIStyleConfig.button_style(),
        )

        self.output_button = ft.ElevatedButton(
            "选择输出目录",
            icon=ft.icons.FOLDER,
            on_click=lambda _: self.output_picker.get_directory_path(),
            style=UIStyleConfig.button_style(),
        )

    def _build_main_layout(self) -> None:
        """Build the main application layout."""
        main_content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("字幕翻译软件", style=ft.TextThemeStyle.HEADLINE_LARGE),
                    ft.Row(
                        [self.engine_dropdown, self.settings_button],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.language_dropdown,
                    self.prompt_input,
                    ft.Column(
                        [
                            ft.Row([self.subtitle_button, self.subtitle_text]),
                            ft.Row([self.output_button, self.output_text]),
                            ft.Row(
                                [self.translate_button, self.reset_button],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            self.progress_bar,
                        ],
                        spacing=UIStyleConfig.SPACING_SMALL,
                    ),
                ],
                spacing=UIStyleConfig.SPACING_MEDIUM,
            ),
            **UIStyleConfig.container_style(),
        )

        self.page.add(main_content)

    def _update_engine_dropdown(self) -> None:
        """Update engine dropdown options based on available API keys."""
        engines = EngineManager.get_available_engines()
        self.engine_dropdown.options = [
            ft.dropdown.Option(engine) for engine in engines
        ]

        default_engine = EngineManager.get_default_engine()
        if default_engine:
            self.engine_dropdown.value = default_engine

        self.page.update()

    def _on_engine_change(self, e) -> None:
        """Handle engine selection change."""
        selected_engine = e.control.value
        if selected_engine:
            engine_key = selected_engine.lower().replace(" ", "").replace("google", "")
            api_key = get_api_key(engine_key)
            if not api_key:
                self.notification_manager.show_error(
                    f"请先设置 {selected_engine} 的 API Key",
                    action_text="去设置",
                    on_action=lambda _: self._show_settings_page(),
                )

    def _on_prompt_change(self, e) -> None:
        """Handle prompt input change."""
        if not self.prompt_input.value:
            self.prompt_input.value = get_prompt()
            self.page.update()

    def _on_subtitle_result(self, e: ft.FilePickerResultEvent) -> None:
        """Handle subtitle file selection result."""
        if e.files:
            relative_paths = []
            for file in e.files:
                relative_paths.append(PathUtils.to_relative_path(file.path))
            self.subtitle_text.value = ", ".join(relative_paths)
            self.output_text.value = PathUtils.to_relative_path(
                str(pathlib.Path(e.files[0].path).parent)
            )
        else:
            self.subtitle_text.value = "未选择文件"
        self.page.update()

    def _on_output_result(self, e: ft.FilePickerResultEvent) -> None:
        """Handle output directory selection result."""
        if e.path:
            self.output_text.value = PathUtils.to_relative_path(e.path)
        else:
            self.output_text.value = "未选择目录"
        self.page.update()

    def _on_translate(self, e) -> None:
        """Handle translation request."""
        try:
            request = self._create_translation_request()
            errors = self.validation_service.validate_translation_request(request)

            if errors:
                self.notification_manager.show_error(errors[0])
                return

            self._execute_translation(request)

        except Exception as ex:
            self.notification_manager.show_error(f"翻译失败: {str(ex)}")

    def _create_translation_request(self) -> TranslationRequest:
        """Create translation request from UI inputs."""
        return TranslationRequest(
            engine=self.engine_dropdown.value or "",
            subtitle_file=self.subtitle_text.value or "",
            output_directory=self.output_text.value or "",
            source_language=self.language_dropdown.value or "",
            prompt=self.prompt_input.value,
        )

    def _execute_translation(self, request: TranslationRequest) -> None:
        """Execute the translation process."""
        # Disable UI during translation
        self._set_ui_enabled(False)
        self.progress_bar.visible = True
        self.page.update()

        try:
            # Save prompt if provided
            if request.prompt:
                set_prompt(request.prompt)

            # Execute translation
            self.translation_service.translate(
                request, progress_callback=self._update_progress
            )

            self.notification_manager.show_success("翻译完成")

        finally:
            # Re-enable UI
            self._set_ui_enabled(True)
            self.progress_bar.value = 0
            self.progress_bar.visible = False
            self.page.update()

    def _update_progress(self, current: int, total: int) -> None:
        """Update translation progress."""
        progress = current / total if total > 0 else 0
        self.progress_bar.value = progress
        self.page.update()

    def _set_ui_enabled(self, enabled: bool) -> None:
        """Enable or disable UI components during translation."""
        self.settings_button.disabled = not enabled
        self.reset_button.disabled = not enabled
        self.translate_button.disabled = not enabled

    def _on_reset(self, e) -> None:
        """Handle reset button click."""
        self.subtitle_text.value = ""
        self.output_text.value = ""
        self.engine_dropdown.value = None
        self.language_dropdown.value = SupportedLanguage.ENGLISH.value
        self.page.update()

    def _on_open_settings(self, e) -> None:
        """Handle settings button click."""
        self._show_settings_page()

    def _show_settings_page(self, disable_back: bool = False) -> None:
        """Show the settings page."""
        settings_page = SettingsPage(self.page, self.config, disable_back)
        settings_page.show(on_return=self._on_settings_return)

    def _on_settings_return(self) -> None:
        """Handle return from settings page."""
        self.config = load_config()  # Reload config
        self._update_engine_dropdown()


class SettingsPage:
    """Settings page component."""

    def __init__(self, page: ft.Page, config: dict, disable_back: bool = False):
        self.page = page
        self.config = config
        self.disable_back = disable_back
        self.notification_manager = NotificationManager(page)

    def show(self, on_return: Optional[Callable] = None) -> None:
        """Display the settings page."""
        self.on_return = on_return
        self.page.clean()
        self.page.add(self._create_settings_content())

    def _create_settings_content(self) -> ft.Container:
        """Create settings page content."""
        # API Key fields
        self.openai_key = ft.TextField(
            label="OpenAI API Key",
            value=self.config["openai_key"],
            disabled=True,  # Currently disabled
            width=400,
        )
        self.claude_key = ft.TextField(
            label="Claude API Key",
            value=self.config["claude_key"],
            disabled=True,  # Currently disabled
            width=400,
        )
        self.gemini_key = ft.TextField(
            label="Google Gemini API Key",
            value=self.config["gemini_key"],
            width=400,
        )

        # Buttons
        save_button = ft.ElevatedButton(
            "保存设置",
            on_click=self._save_settings,
            style=UIStyleConfig.button_style(),
        )

        # Build column
        col = [
            ft.Text("API 设置", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            self.openai_key,
            self.claude_key,
            self.gemini_key,
            save_button,
        ]

        # Add back button if not disabled
        if not self.disable_back:
            return_button = ft.IconButton(
                icon=ft.icons.ARROW_BACK,
                tooltip="返回主页",
                on_click=self._return_to_main,
            )
            col.insert(0, ft.Row([return_button], alignment=ft.MainAxisAlignment.START))

        return ft.Container(
            content=ft.Column(col, spacing=UIStyleConfig.SPACING_SMALL),
            **UIStyleConfig.container_style(),
        )

    def _save_settings(self, e) -> None:
        """Save settings and update configuration."""
        set_api_key("openai", self.openai_key.value or "")
        set_api_key("claude", self.claude_key.value or "")
        set_api_key("gemini", self.gemini_key.value or "")

        if not self.disable_back:
            self.notification_manager.show_success("设置已保存")
            if self.on_return:
                self.on_return()
        else:
            self.notification_manager.show_success("重启软件以应用设置")

    def _return_to_main(self, e) -> None:
        """Return to main page."""
        self.page.clean()
        SubtitleTranslatorApp(self.page)


def main(page: ft.Page):
    """Main application entry point."""
    SubtitleTranslatorApp(page)


ft.app(target=main)
