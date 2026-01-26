# Connector flags — AudibleZenBot C#

Scanned: `AudibleZenBot.AutoGen/platform_connectors`

Summary of TODOs / unimplemented markers found:

- `base_connector.cs`
  - multiple `// TODO: implement` entries (constructor and helpers)

- `placeholder_server_8889.cs`
  - `// TODO: implement`

- `trovo_connector.cs` & `trovo_oauth.cs`
  - Many `// TODO: implement` markers including constructors and OAuth helpers. Marked as "not implemented" in places.

- `twitch_connector.cs`
  - Numerous `// TODO: implement` markers spread across the file, including constructor and many method stubs. (Large file — requires careful walkthrough.)

- `youtube_connector.cs`, `youtube_oauth_local.cs`
  - `// TODO: implement` placeholders present.

- `twitter_connector.cs`
  - Appears implemented for basic simulated send (logs), but test file `test_twitter.cs` contains `// TODO: implement` — tests incomplete.

- `kick_connector.cs` and `kick_connector_old_pusher.cs`
  - No explicit TODOs found in quick scan, but `kick_connector.cs` has console logging and may require validation for full feature parity.

- `dlive_connector.cs`
  - No explicit TODOs flagged, basic connect/disconnect logic present.

- `trovo_*`, `youtube_*`, `twitch_connector.cs` require highest attention due to many TODOs.

Recommendations:
1. Prioritize `twitch_connector.cs` and `trovo_connector.cs` for detailed implementation review and unit tests.
2. Move `test_twitter.cs` TODOs into `AudibleZenBot.Tests` and implement tests to validate `twitter_connector.cs` behavior.
3. Create small unit tests for `kick_connector.cs`, `dlive_connector.cs`, and `youtube_connector.cs` to verify basic connect/send flows.
4. Audit `base_connector.cs` — many connectors depend on it; implementing core behaviors there will reduce duplicate work.

(Generated: 2026-01-25)
