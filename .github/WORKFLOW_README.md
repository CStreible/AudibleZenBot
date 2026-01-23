# CI Workflow: Python tests

This repository uses the `Python tests` GitHub Actions workflow (.github/workflows/python-tests.yml).

What it does
- Runs unit tests on multiple Python versions.
- Optionally runs UI integration tests under Xvfb.

Automatic triggers
- The integration job runs automatically on pushes to the `main` branch and on pull requests targeting `main`.

Manual trigger (Run workflow)
1. In GitHub, go to the repository > `Actions` tab.
2. Select the `Python tests` workflow from the left-hand list.
3. Click the `Run workflow` dropdown.
4. Set the `run_integration` input to `true` and choose the branch to run on.
5. Click the `Run workflow` button.

Notes
- Integration runs use `xvfb-run` and install headless Qt/system deps; they are slower than unit-only runs.
- If you'd like to run just unit tests locally, use:

```powershell
.\scripts\run_tests.ps1
```

Or directly:

```bash
python -m unittest discover -v
```

If you want the integration job to run for other branches (e.g., `develop`), I can update the workflow to include them.