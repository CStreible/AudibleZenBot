Summary:
- Harden EventSub subscription lifecycle in `AudibleZenBot.AutoGen/platform_connectors/twitch_connector.cs`
- Add per-(type,session) throttling to avoid rapid repeated creates
- Treat 409 as idempotent success and log/handle 401 with reauth callback
- Use `core.http_retry` helpers for retries/backoff
- Tests fixed/updated: `AudibleZenBot.Tests` JSON literals and EventSub dispatch; all tests pass locally

Files changed (high level):
- AudibleZenBot.AutoGen/platform_connectors/twitch_connector.cs (throttling, POST error handling)

Why: prevents duplicate subscriptions, reduces race/429 issues, and prepares for replacing IRC flows with EventSub-first handling.

Next steps (future work):
- Add persistent subscription registry to survive restarts
- Replace remaining IRC call-sites with EventSub mapping
- Add CI gating for live Helix actions

Testing: `dotnet test AudibleZenBot.Tests` -> all tests pass locally (19/19).
