# 2026-01-19 — twitch_emotes hardening

- schedule_emote_set_fetch: perform immediate fetch when background throttler is not active so `id_map` is populated synchronously in test/simple runs.
- fetch_emote_sets / fetch_channel_emotes: defensive parsing and string coercion to tolerate unexpected response shapes.
- Improved logging in `_request_with_backoff` and better structured throttler payloads for success/error.
- Minor hardening for image prefetch and id normalization.
