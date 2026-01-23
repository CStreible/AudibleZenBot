Platform connectors contract

- Signal contract:
  - `message_received_with_metadata(platform, username, message, metadata)` — preferred
  - `message_received(platform, username, message, metadata)` — legacy supported
  - `message_deleted(platform, message_id)` — when the platform reports deletion

- `metadata` should be a dict and may include keys: `timestamp`, `message_id`, `color`, `badges`, `emotes`, `event_type`.

- Connectors should not start long-running network threads on import. Provide `connect()` and `disconnect()` methods.

- Tests: use `tests/mock_connectors.MockConnector` to simulate platform messages in unit/integration tests.
