# Conversion Inventory — AudibleZenBot C# (initial)

- Projects discovered:
  - AudibleZenBot.AutoGen
  - AudibleZenBot.Connectors
  - AudibleZenBot.Core
  - AudibleZenBot.Integration
  - AudibleZenBot.Overlay
  - AudibleZenBot.UI
  - AudibleZenBot.WPF
  - AudibleZenBot.Tests

- Key core modules (AudibleZenBot.AutoGen/core):
  - config.cs, oauth_handler.cs, secret_store.cs, chat_manager.cs, http_session.cs, emotes.cs, twitch_emotes.cs, ngrok_manager.cs, overlay_server.cs

- Platform connectors (AudibleZenBot.AutoGen/platform_connectors):
  - twitch_connector.cs, twitter_connector.cs, dlive_connector.cs, kick_connector.cs, trovo_connector.cs, youtube_connector.cs, plus related oauth/local helpers

- Findings from quick scan:
  - WPF views reference Twitch UI, `ConfigModule`, and `core.oauth_handler` (Twitch account + OAuth flows present).
  - `AudibleZenBot.Tests` builds and all tests passed locally (11/11).
  - Several `// TODO: implement` placeholders in `AudibleZenBot.AutoGen` tests and UI automation page.
  - Core contains `secret_store.cs` and `oauth_handler.cs` — sensitive storage and OAuth logic exist in C#.

- Preliminary gap candidates (need deeper review):
  - Review `twitter_connector.cs` and `test_twitter.cs` TODOs — Twitter functionality may be incomplete.
  - Validate `kick_connector_old_pusher.cs` vs `kick_connector.cs` for legacy vs current implementations.
  - Confirm emote handling: `emotes.cs` and `twitch_emotes.cs` cover expected platform APIs.

- Next recommended steps:
  1. Map each connector to its tests and UI points-of-use.
  2. Produce a detailed feature matrix (file-by-file) showing parity with Python spec.
  3. Triage and implement `TODO` items starting with test failures or missing integrations.

(Generated: 2026-01-25)
