# Font to Webfont Converter

A PyQt5 desktop application for converting OTF, TTF, and WOFF fonts to WOFF2 or WOFF. It keeps the select → configure → convert flow from the Video to Audio Converter UI and replaces the media engine with `fontTools`.

## Features

- Select multiple OTF, TTF, or WOFF files.
- Import every supported font from a folder recursively.
- Convert a batch to WOFF2 or legacy WOFF.
- Choose the output folder.
- Use the bundled Adobe Caslon family throughout the interface.
- Track per-file progress without blocking the interface.
- Continue the batch when one font fails and report the errors at the end.
- Preserve existing files by generating names such as `Font (1).woff2`.

Conversion repackages the full font. It does not subset glyphs.

## Setup

Python 3.9 or newer is recommended.

```bash
cd knowledge/projects/webfont-converter
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows, replace `.venv/bin/` with `.venv\Scripts\`.

## Run

```bash
.venv/bin/python app.py
```

Windows users can also run `run.bat` after creating `.venv`.

## Test

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The test suite builds a minimal TrueType fixture and verifies both WOFF2 and WOFF output.

## Project structure

```text
app.py                 PyQt5 interface and background conversion thread
converter.py           Reusable font collection and conversion engine
fonts/adobe-caslon/     Adobe Caslon Regular, Italic, Semibold, and Bold styles
icons/                 UI icons reused from Video to Audio Converter
tests/test_converter.py
requirements.txt
```

## Origin

- Conversion engine adapted from `workspace/psiativa/projects/webfont-converter`.
- PyQt5 interface adapted from `knowledge/projects/video-to-audio`.

The interface source and reused icons remain subject to the Apache License 2.0 included with this project.
