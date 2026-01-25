# Twitch & Trovo Prioritized Implementation Checklist

Generated: 2026-01-25

Goal: Identify concrete implementation tasks to bring `twitch_connector.cs` and `trovo_connector.cs` to functional parity and testability.

Top priority (Twitch)
- [ ] Implement `MakeRetrySession`, `New`, `Init` helpers at top-level module.
- [ ] Implement `SetBotUsername` and token refresh helpers (`RefreshAccessToken`, `OnEventsubReauthRequested`, `Disconnect`).
- [ ] Implement chat-related helpers: `DeleteMessage`, `GetCustomReward`, `BanUser`, `SendMessageAsync`, `SendMessage` plumbing and local-echo tracking.
- [ ] Implement EventSub lifecycle: fully flesh out `StartEventSubWebsocketAsync` usage (already present), `OnEventSubStatus`, `SubscribeToRedemptions`/`SubscribeToCommonEvents` cross-checks, and session management.
- [ ] Implement parsing helpers: `ParseClearmsg`, `ParseUsernotice`, `ParsePrivmsg`, `HandleMessage` support is present but parsing helpers needed.
- [ ] Implement worker/instance-level methods on `TwitchConnector`, `TwitchWorker`, and `TwitchEventSubWorker` (constructors, `Run`, `ConnectToTwitch`, `Authenticate`, `HandleMessage`, `HealthCheckLoop`).
- [ ] Add unit tests mirroring `TwitchHelixTests.cs` cases for additional flows (e.g., eventsub notifications, token validation). Verify `ResolveUserIdAsync` and `SendChatMessageAsync` with mocked `HttpClient` responses.

High priority (Trovo)
- [ ] Implement `DeleteMessage`, `BanUser`, `GetChatToken`, `PingLoop`, `Listen`, `HandleMessage`, `RandomNonce`, `HealthCheckLoop`, and `Stop` in `Trovo_connectorModule`.
- [ ] Implement `TrovoConnector` instance methods and `TrovoWorker` worker routines (`Run`, `GetChatToken`, `ConnectToTrovo`, `Listen`, `PingLoop`, `RandomNonce`).
- [ ] Add unit tests to assert token persistence, `SendMessage` behavior (simulated), and `ConnectToPlatform` flow using mocked `ConnectorUtils` and `HttpClient`.

Cross-cutting
- [ ] Audit and implement shared `base_connector.cs` helpers used by multiple connectors.
- [ ] Ensure `core.http_client.HttpClientFactory` supports injecting mocked `HttpClient` instances for tests.
- [ ] Add tests that cover OAuth flows by mocking `core.oauth_handler.OAuthHandler` (Get/Refresh/Authenticate).
- [ ] Remove or implement `// TODO: implement` stubs progressively; prefer implementing core low-level behaviors referenced by many connectors (retry, token refresh, masking, session management).

Risk / Notes
- `twitch_connector.cs` contains many TODOs but already implements key HTTP-backed flows (ResolveUserIdAsync, ValidateToken, EventSub subscription creation). Focus implementation on parsing/IRC/local echo and worker lifecycle to enable chat integration.
- `trovo_connector.cs` is currently a minimal simulated implementation; adding full WS-based chat will be larger effort.

Next step: I can implement a small unit test for `Twitch_connectorModule.ResolveUserIdAsync` using a mocked `HttpClient` to demonstrate testing pattern and create helpers in `HttpClientFactory` if needed. Proceed with that?