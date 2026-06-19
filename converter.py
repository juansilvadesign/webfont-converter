"""Core font-to-webfont conversion functions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fontTools.ttLib import TTFont


SUPPORTED_INPUT_EXTENSIONS = frozenset({".otf", ".ttf", ".woff"})
SUPPORTED_OUTPUT_FORMATS = frozenset({"woff2", "woff"})


@dataclass(frozen=True)
class ConversionResult:
    """The observable result of converting one font file."""

    source: Path
    destination: Path
    input_size: int
    output_size: int


def collect_font_files(inputs: Iterable[str | Path]) -> list[Path]:
    """Collect supported font files from files and recursively from folders."""

    collected: dict[Path, None] = {}

    for raw_input in inputs:
        path = Path(raw_input).expanduser()
        if path.is_dir():
            candidates = (
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and candidate.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS
            )
        elif path.is_file() and path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
            candidates = (path,)
        else:
            candidates = ()

        for candidate in candidates:
            collected[candidate.resolve()] = None

    return sorted(collected, key=lambda candidate: str(candidate).casefold())


def unique_output_path(candidate: Path, source: Path | None = None) -> Path:
    """Return a non-conflicting output path without overwriting the source."""

    candidate = candidate.resolve()
    source = source.resolve() if source is not None else None
    if not candidate.exists() and candidate != source:
        return candidate

    counter = 1
    while True:
        numbered = candidate.with_name(
            f"{candidate.stem} ({counter}){candidate.suffix}"
        )
        if not numbered.exists() and numbered != source:
            return numbered
        counter += 1


def convert_font(
    source: str | Path,
    output_dir: str | Path,
    output_format: str,
) -> ConversionResult:
    """Convert one OTF, TTF, or WOFF file to WOFF2 or WOFF."""

    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Font file not found: {source_path}")
    if source_path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        raise ValueError(f"Unsupported font input: {source_path.name}")

    flavor = output_format.lower()
    if flavor not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"Unsupported output format: {output_format}")

    destination_dir = Path(output_dir).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = unique_output_path(
        destination_dir / f"{source_path.stem}.{flavor}",
        source=source_path,
    )

    font = TTFont(str(source_path))
    try:
        font.flavor = flavor
        font.save(str(destination))
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        font.close()

    return ConversionResult(
        source=source_path,
        destination=destination,
        input_size=source_path.stat().st_size,
        output_size=destination.stat().st_size,
    )

