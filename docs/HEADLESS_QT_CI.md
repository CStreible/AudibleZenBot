Headless Qt / QWebEngine test runner (CI and local)
=================================================

This project contains an integration test that exercises `QWebEngineView` (the
Qt WebEngine) and requires a headless X server in CI or when running locally on
Linux. The test is guarded and will skip automatically if `PyQt6.QtWebEngineWidgets`
is not importable.

What the CI workflow does
- Installs system packages required by Qt WebEngine (NSS, X11/Xvfb, fonts, audio
  libraries).
- Installs Python dependencies and `PyQt6` + `PyQt6-QtWebEngine` via pip.
- Starts an Xvfb server and runs `pytest` under that virtual display.

GitHub Actions
---------------
See `.github/workflows/ci.yml` for the workflow used by this repository. It runs
on `ubuntu-latest` and starts an Xvfb display at `:99` before running tests.

Running tests locally (Ubuntu / WSL)
-----------------------------------
1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

2. Install Python requirements and Qt packages:

```bash
pip install -r requirements.txt
pip install PyQt6 PyQt6-QtWebEngine
```

3. Install system packages (Ubuntu):

```bash
sudo apt-get update
sudo apt-get install -y xvfb libnss3 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxrandr2 libxss1 libasound2 libpangocairo-1.0-0 libatk1.0-0 libcups2 libdbus-1-3 fonts-liberation libxkbcommon0 libglu1-mesa
```

4. Start Xvfb and run pytest:

```bash
export DISPLAY=:99
Xvfb :99 -screen 0 1280x1024x24 &
pytest -q
```

Notes & troubleshooting
- On macOS and Windows, running headless Qt WebEngine in CI is more involved;
  consider using a Linux runner for these integration tests.
- If tests continually skip, confirm `PyQt6` and `PyQt6-QtWebEngine` are
  successfully installed in the environment and that `DISPLAY` is set.
- If `QWebEngine` fails with GPU or sandbox errors, try adding
  `--no-sandbox` or environment tweaks specific to your runner.

Selective runs
---------------
To run only the integration test locally:

```bash
pytest -q tests/test_emote_integration_onload.py
```
