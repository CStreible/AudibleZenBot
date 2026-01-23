# Canonical Message Schema

This document describes the minimal canonical message schema ChatManager expects
from platform connectors. Connectors should prefer emitting `message_received_with_metadata`
but may fall back to `message_received` (legacy).

Minimal metadata keys (all optional unless noted):

- `message_id` (string): Platform-provided unique identifier for the message. When
  present it must be a stable string.
- `timestamp` / `tmi-sent-ts` (string|int): Platform-provided timestamp. May be
  integer milliseconds since epoch or an ISO timestamp string.
- `badges` (string|dict): Badge data or string representation for display.
- `emotes` (string|dict): Emote metadata if provided by the platform.
- `color` (string): Username color hex string if provided.

Rules and recommendations:

- Metadata must be a `dict` (empty dict is acceptable).
- `message_id` should be coerced to a string by connectors or by `ChatManager`.
- Connectors should avoid embedding complex IRC tag blobs into the `username` field;
  instead parse tags into `metadata` and supply `username` as the display name.
- If a connector cannot provide `message_id`, ChatManager will fall back to
  deduplication heuristics (recent canonical message cache).

Connector checklist:

- [ ] Emit `message_received_with_metadata(platform, username, message, metadata)` when possible.
- [ ] If only `message_received` is available, ensure callers understand metadata will be empty.
- [ ] Ensure `metadata` is a dict and uses the keys above when available.

If you need help updating a connector to conform to the schema, open an issue or
assign one of the maintainers; we can help with a small patch to parse platform tags.
