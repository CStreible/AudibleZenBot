# Contributing

Thanks for your interest in contributing to AudibleZenBot! A few quick guidelines to get you started.

- Fork the repo and open a pull request against `main` with a clear title and description.
- Run tests locally before opening a PR:

```powershell
# Use the workspace venv if present
.\scripts\run_tests.ps1
```

- Keep changes small and focused. Add unit tests for new behavior and update documentation when applicable.
- Use the existing code style and run linters if configured.
- For new platform connectors, follow `docs/message_schema.md` and ensure the connector emits `message_received_with_metadata(platform, username, message, metadata)` when possible.

If you're unsure where to start, open an issue describing your idea and we'll help you get started.

Thanks — we appreciate contributions of all sizes.