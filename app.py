"""Font to Webfont Converter desktop application.

The PyQt5 interface is adapted from the Video to Audio Converter project.
The media conversion flow was replaced with fontTools-based webfont conversion.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QFontDatabase, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from converter import ConversionResult, collect_font_files, convert_font


APP_DIR = Path(__file__).resolve().parent
FONT_DIRECTORIES = (
    APP_DIR / "fonts" / "inter",
    APP_DIR / "fonts" / "adobe-caslon",
)
DEFAULT_FONT_FAMILY = "Inter"
FALLBACK_FONT_FAMILIES = ("Adobe Caslon",)
FONT_FILTER = "Font Files (*.otf *.ttf *.woff)"


def load_application_font(app: QApplication) -> str | None:
    """Load bundled fonts and apply the configured family stack globally."""

    loaded_families: dict[str, str] = {}
    for font_directory in FONT_DIRECTORIES:
        for font_path in sorted(font_directory.glob("*.ttf")):
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id < 0:
                continue
            for family in QFontDatabase.applicationFontFamilies(font_id):
                loaded_families.setdefault(family.casefold(), family)

    requested_families = (DEFAULT_FONT_FAMILY, *FALLBACK_FONT_FAMILIES)
    resolved_families = [
        loaded_families[name.casefold()]
        for name in requested_families
        if name.casefold() in loaded_families
    ]
    resolved_families = list(dict.fromkeys(resolved_families))
    if not resolved_families:
        return None

    application_font = app.font()
    application_font.setFamilies(resolved_families)
    # Adobe Caslon reports identical numeric weights in all bundled files.
    # Selecting by style name keeps its Regular face deterministic when used.
    application_font.setStyleName("Regular")
    app.setFont(application_font)
    return resolved_families[0]


@dataclass(frozen=True)
class ConversionSummary:
    """The result returned by the background conversion thread."""

    converted: tuple[ConversionResult, ...]
    errors: tuple[str, ...]
    cancelled: bool = False


class ConvertThread(QThread):
    """Convert selected fonts without blocking the interface."""

    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(object)

    def __init__(
        self,
        font_paths: list[Path],
        output_format: str,
        output_dir: Path,
    ) -> None:
        super().__init__()
        self.font_paths = font_paths
        self.output_format = output_format
        self.output_dir = output_dir
        self.is_running = True

    def run(self) -> None:
        converted: list[ConversionResult] = []
        errors: list[str] = []
        total_files = len(self.font_paths)

        for index, font_path in enumerate(self.font_paths, start=1):
            if not self.is_running:
                self.finished_signal.emit(
                    ConversionSummary(tuple(converted), tuple(errors), cancelled=True)
                )
                return

            self.status_signal.emit(f"Converting {font_path.name}...")
            try:
                converted.append(
                    convert_font(font_path, self.output_dir, self.output_format)
                )
            except Exception as error:  # Continue converting the remaining files.
                errors.append(f"{font_path.name}: {error}")

            self.progress_signal.emit(int(index / total_files * 100))

        self.finished_signal.emit(
            ConversionSummary(tuple(converted), tuple(errors), cancelled=False)
        )

    def stop(self) -> None:
        self.is_running = False


class FontToWebfontApp(QMainWindow):
    """Desktop interface for batch webfont conversion."""

    def __init__(self) -> None:
        super().__init__()
        self.font_paths: list[Path] = []
        self.output_dir: Path | None = None
        self.convert_thread: ConvertThread | None = None

        self.setWindowTitle("Font to Webfont Converter")
        self.setGeometry(300, 200, 500, 400)
        self.setWindowIcon(QIcon(str(APP_DIR / "icons" / "convert.png")))
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout()

        self.font_list = QListWidget(self)
        layout.addWidget(self.font_list)

        select_layout = QHBoxLayout()

        self.select_btn = QPushButton("Select Fonts", self)
        self.select_btn.setIcon(QIcon(str(APP_DIR / "icons" / "add.png")))
        self.select_btn.clicked.connect(self.open_file_dialog)
        select_layout.addWidget(self.select_btn)

        self.folder_btn = QPushButton("Select Font Folder", self)
        self.folder_btn.setIcon(QIcon(str(APP_DIR / "icons" / "folder.png")))
        self.folder_btn.clicked.connect(self.open_folder_dialog)
        select_layout.addWidget(self.folder_btn)

        self.clear_btn = QPushButton("Clear List", self)
        self.clear_btn.setIcon(QIcon(str(APP_DIR / "icons" / "clear.png")))
        self.clear_btn.clicked.connect(self.clear_font_list)
        select_layout.addWidget(self.clear_btn)

        layout.addLayout(select_layout)

        format_layout = QHBoxLayout()
        self.format_label = QLabel("Output Format:", self)
        format_layout.addWidget(self.format_label)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["woff2", "woff"])
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        self.output_btn = QPushButton("Select Output Folder", self)
        self.output_btn.setIcon(QIcon(str(APP_DIR / "icons" / "folder.png")))
        self.output_btn.clicked.connect(self.select_output_folder)
        layout.addWidget(self.output_btn)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Progress: 0%", self)
        layout.addWidget(self.progress_label)

        self.status_label = QLabel("Ready", self)
        layout.addWidget(self.status_label)

        self.convert_btn = QPushButton("Convert", self)
        self.convert_btn.setIcon(QIcon(str(APP_DIR / "icons" / "convert.png")))
        self.convert_btn.clicked.connect(self.start_conversion)
        layout.addWidget(self.convert_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_file_dialog(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Font Files",
            "",
            FONT_FILTER,
        )
        self.add_font_paths(collect_font_files(files))

    def open_folder_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Font Folder")
        if not folder:
            return

        fonts = collect_font_files([folder])
        if not fonts:
            QMessageBox.warning(
                self,
                "No Fonts Found",
                "The selected folder contains no OTF, TTF, or WOFF files.",
            )
            return
        self.add_font_paths(fonts)

    def add_font_paths(self, paths: list[Path]) -> None:
        known_paths = set(self.font_paths)
        for path in paths:
            if path in known_paths:
                continue
            self.font_paths.append(path)
            known_paths.add(path)
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            self.font_list.addItem(item)

        self.status_label.setText(f"{len(self.font_paths)} font(s) selected")

    def clear_font_list(self) -> None:
        self.font_list.clear()
        self.font_paths = []
        self.progress_bar.setValue(0)
        self.progress_label.setText("Progress: 0%")
        self.status_label.setText("Ready")

    def select_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not folder:
            return

        self.output_dir = Path(folder).resolve()
        self.output_btn.setText(f"Output: {self.output_dir.name}")
        self.output_btn.setToolTip(str(self.output_dir))
        QMessageBox.information(
            self,
            "Folder Selected",
            f"Output folder set to: {self.output_dir}",
        )

    def start_conversion(self) -> None:
        if not self.font_paths or self.output_dir is None:
            QMessageBox.warning(
                self,
                "Missing Selection",
                "Please select font files and an output folder.",
            )
            return

        self.progress_bar.setValue(0)
        self.progress_label.setText("Progress: 0%")
        self.set_controls_enabled(False)

        self.convert_thread = ConvertThread(
            self.font_paths.copy(),
            self.format_combo.currentText(),
            self.output_dir,
        )
        self.convert_thread.progress_signal.connect(self.update_progress)
        self.convert_thread.status_signal.connect(self.status_label.setText)
        self.convert_thread.finished_signal.connect(self.handle_conversion_finished)
        self.convert_thread.start()

    def update_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"Progress: {value}%")

    def handle_conversion_finished(self, summary: ConversionSummary) -> None:
        self.set_controls_enabled(True)

        if summary.cancelled:
            self.status_label.setText("Conversion cancelled")
            return

        if summary.errors:
            details = "\n".join(summary.errors[:5])
            remaining = len(summary.errors) - 5
            if remaining > 0:
                details += f"\n...and {remaining} more error(s)."
            QMessageBox.warning(
                self,
                "Conversion Finished With Errors",
                f"Converted {len(summary.converted)} font(s).\n\n{details}",
            )
            self.status_label.setText(
                f"Converted {len(summary.converted)}; failed {len(summary.errors)}"
            )
            return

        QMessageBox.information(
            self,
            "Complete",
            f"Converted {len(summary.converted)} font(s) successfully.",
        )
        self.status_label.setText(
            f"Converted {len(summary.converted)} font(s) successfully"
        )
        self.font_list.clear()
        self.font_paths = []

    def set_controls_enabled(self, enabled: bool) -> None:
        for control in (
            self.select_btn,
            self.folder_btn,
            self.clear_btn,
            self.format_combo,
            self.output_btn,
            self.convert_btn,
        ):
            control.setEnabled(enabled)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API name
        if self.convert_thread is not None and self.convert_thread.isRunning():
            self.convert_thread.stop()
            self.convert_thread.wait()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    load_application_font(app)
    window = FontToWebfontApp()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
