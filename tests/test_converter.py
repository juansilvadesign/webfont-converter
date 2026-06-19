from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from converter import collect_font_files, convert_font, unique_output_path


def build_test_font(destination: Path) -> None:
    """Build a minimal valid TrueType font for conversion tests."""

    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "A"])
    builder.setupCharacterMap({65: "A"})

    notdef_pen = TTGlyphPen(None)
    a_pen = TTGlyphPen(None)
    a_pen.moveTo((100, 0))
    a_pen.lineTo((300, 700))
    a_pen.lineTo((500, 0))
    a_pen.closePath()

    builder.setupGlyf(
        {
            ".notdef": notdef_pen.glyph(),
            "A": a_pen.glyph(),
        }
    )
    builder.setupHorizontalMetrics({".notdef": (600, 0), "A": (600, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable(
        {
            "familyName": "Converter Test",
            "styleName": "Regular",
            "uniqueFontIdentifier": "Converter Test Regular",
            "fullName": "Converter Test Regular",
            "psName": "ConverterTest-Regular",
        }
    )
    builder.setupOS2(
        sTypoAscender=800,
        sTypoDescender=-200,
        usWinAscent=800,
        usWinDescent=200,
    )
    builder.setupPost()
    builder.setupMaxp()
    builder.save(destination)


class ConverterTests(unittest.TestCase):
    def test_collect_font_files_recursively_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "nested"
            nested.mkdir()
            first = root / "A.TTF"
            second = nested / "B.otf"
            unsupported = root / "notes.txt"
            first.touch()
            second.touch()
            unsupported.touch()

            collected = collect_font_files([root, first])

            self.assertEqual(collected, sorted([first.resolve(), second.resolve()]))

    def test_unique_output_path_uses_numbered_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "Font.woff2"
            output.touch()

            self.assertEqual(
                unique_output_path(output),
                (root / "Font (1).woff2").resolve(),
            )

    def test_converts_ttf_to_both_webfont_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Test.ttf"
            output = root / "output"
            build_test_font(source)

            for output_format in ("woff2", "woff"):
                with self.subTest(output_format=output_format):
                    result = convert_font(source, output, output_format)
                    self.assertTrue(result.destination.is_file())
                    self.assertEqual(result.destination.suffix, f".{output_format}")
                    converted = TTFont(result.destination)
                    try:
                        self.assertEqual(converted.flavor, output_format)
                    finally:
                        converted.close()

    def test_never_overwrites_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Test.ttf"
            output = root / "output"
            build_test_font(source)

            first = convert_font(source, output, "woff2")
            second = convert_font(source, output, "woff2")

            self.assertNotEqual(first.destination, second.destination)
            self.assertEqual(second.destination.name, "Test (1).woff2")


if __name__ == "__main__":
    unittest.main()

