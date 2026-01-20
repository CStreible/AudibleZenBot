Adds a guarded PyQt6 WebEngine integration test for the ChatPage click/delete flow,
plus smoke import tests for core, UI, and platform connector modules.

CI workflow (.github/workflows/integration-webengine.yml) is added to run the
WebEngine test on Ubuntu 22.04 with required system libraries. The
integration test is gated behind the `AZB_ENABLE_WEBENGINE_TESTS` env var.

Files of interest:
- tests/integration/test_chatpage_click.py
- tests/unit/test_smoke_core_ui.py
- tests/unit/test_smoke_connectors.py
- .github/workflows/integration-webengine.yml

This PR aims to make headless WebEngine tests reliable in CI and add
baseline smoke coverage to catch import-time regressions.
