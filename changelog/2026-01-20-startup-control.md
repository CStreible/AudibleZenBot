## 2026-01-20 — Connector startup control (tests/CI)

Summary
-------
- Add `startup_allowed()` helper in `platform_connectors/connector_utils.py`.
- Gate connector background startup (worker threads, websocket threads, webhook servers)
  when the environment variable `AUDIBLEZENBOT_CI=1` is set. This prevents
  connectors from starting long-running network threads during test or CI runs.
- Applied guards to: `twitch_connector.py`, `trovo_connector.py`, `dlive_connector.py`,
  `youtube_connector.py`, `twitter_connector.py`, `kick_connector.py`, and
  `kick_connector_old_pusher.py`.

Why
---
Unit tests and CI should be able to import connector modules without
triggering network activity or threads. This change reduces test flakiness
and allows reliable monkeypatching of websocket/connect functions during tests.

How to opt-in/out
-----------------
- To disable background startup behavior (i.e., run normally), leave
  `AUDIBLEZENBOT_CI` unset or set it to any value other than `1`.
- To enable CI/test-safe mode, set `AUDIBLEZENBOT_CI=1` in your CI environment
  or locally when running tests that should avoid starting threads.

Notes
-----
- Unit tests in this repository were updated to rely on this gating and the
  test suite passes with `AUDIBLEZENBOT_CI` set to `1`.
