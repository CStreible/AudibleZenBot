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
  - `config.cs`, `oauth_handler.cs`, `secret_store.cs`, `chat_manager.cs`, `http_session.cs`, `emotes.cs`, `twitch_emotes.cs`, `ngrok_manager.cs`, `overlay_server.cs`

- Platform connectors (AudibleZenBot.AutoGen/platform_connectors):
  - `twitch_connector.cs`, `twitter_connector.cs`, `dlive_connector.cs`, `kick_connector.cs`, `trovo_connector.cs`, `youtube_connector.cs`, plus related oauth/local helpers

- Findings from quick scan:
  - WPF views reference Twitch UI, `ConfigModule`, and `core.oauth_handler` (Twitch account + OAuth flows present).
  - `AudibleZenBot.Tests` builds and all tests passed locally (11/11).
  - Several `// TODO: implement` placeholders in `AudibleZenBot.AutoGen` tests and UI automation page.
  - Core contains `secret_store.cs` and `oauth_handler.cs` — sensitive storage and OAuth logic exist in C#.

- Preliminary gap candidates (need deeper review):
  - Review `twitter_connector.cs` and `test_twitter.cs` TODOs — Twitter functionality may be incomplete.
  - Validate `kick_connector_old_pusher.cs` vs `kick_connector.cs` for legacy vs current implementations.
  - Confirm emote handling: `emotes.cs` and `twitch_emotes.cs` cover expected platform APIs.

- Connector → UI / Tests mapping (initial):
  - Twitch
    - Connector: `AudibleZenBot.AutoGen/platform_connectors/twitch_connector.cs`
    - UI: `AudibleZenBot.WPF/Views/ConnectionsPage.xaml` and `PlatformConnectionPanel.xaml.cs` (login, category suggestions, save/refresh handlers)
    - Tests: `AudibleZenBot.Tests/TwitchHelixTests.cs` (SendChatMessageAsync, ResolveUserIdAsync)

  - Twitter
    - Connector: `AudibleZenBot.AutoGen/platform_connectors/twitter_connector.cs`
    - UI: no direct WPF UI references found (connector managed via config and oauth flow)
    - Tests: `AudibleZenBot.AutoGen/test_twitter.cs` contains `// TODO: implement` placeholders — test coverage incomplete

  - Kick
    - Connector: `AudibleZenBot.AutoGen/platform_connectors/kick_connector.cs` (also `kick_connector_old_pusher.cs` present)
    - UI: `AudibleZenBot.WPF/Views/ConnectionsPage.xaml` (Kick tab), `AudibleZenBot.UI/MainForm.cs` lists Kick platform
    - Tests: no dedicated test class in `AudibleZenBot.Tests` — AutoGen includes platform test stubs

  - DLive
    - Connector: `AudibleZenBot.AutoGen/platform_connectors/dlive_connector.cs`
    - UI: `ConnectionsPage.xaml` (DLive tab), `ConnectionsPage.xaml.cs` handlers
    - Tests: `AudibleZenBot.AutoGen/test_dlive*.cs` test stubs exist in AutoGen

  - Trovo
    - Connector: `AudibleZenBot.AutoGen/platform_connectors/trovo_connector.cs` and oauth helpers
    - UI: `ConnectionsPage.xaml` (Trovo tab) and UI handlers
    - Tests: no dedicated test in `AudibleZenBot.Tests`; AutoGen contains helper test files

  - YouTube
    - Connector: `AudibleZenBot.AutoGen/platform_connectors/youtube_connector.cs` and `youtube_oauth_local.cs`
    - UI: `ConnectionsPage.xaml` (YouTube tab) and connection handlers
    - Tests: no dedicated test in `AudibleZenBot.Tests`; some OAuth HTTP logs in WPF handlers

- Notes:
  - Many platform connectors exist under `AudibleZenBot.AutoGen/platform_connectors` and are referenced by the WPF connection UI.
  - `AudibleZenBot.Tests` currently contains focused tests for Twitch integration; other platform tests appear as stubs under `AutoGen`.
  - `test_twitter.cs` and `ui/automation_page.cs` include `// TODO: implement` comments that should be triaged.

- Next recommended actions:
  1. Walk each connector file and mark TODOs or unsupported behavior; prioritize connectors with missing tests (Twitter, Kick, Trovo, YouTube, DLive).
  2. Add or enable unit tests in `AudibleZenBot.Tests` for non-Twitch connectors where feasible.
  3. Verify OAuth flows (`oauth_handler.cs`) across platforms and ensure `secret_store.cs` usage is secure and documented.

(Generated: 2026-01-25)
