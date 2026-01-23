import pytest
import asyncio
from contextlib import asynccontextmanager

from platform_connectors.connector_utils import connect_with_retry


class FakeConnectFactory:
    def __init__(self, succeed_on=3):
        self.attempts = 0
        self.succeed_on = succeed_on

    def __call__(self, uri, *args, **kwargs):
        self.attempts += 1
        succeed = self.attempts >= self.succeed_on

        @asynccontextmanager
        async def cm():
            if not succeed:
                raise ConnectionError(f"failed to connect (attempt {self.attempts})")
            class DummyWS:
                async def send(self, *a, **k):
                    pass

            yield DummyWS()

        return cm()


@pytest.mark.asyncio
async def test_connect_with_retry_succeeds_after_retries(caplog):
    caplog.clear()
    factory = FakeConnectFactory(succeed_on=3)

    async with connect_with_retry(factory, "wss://example.test", retries=5, backoff_factor=0.001, logger=None) as ws:
        assert ws is not None

    # Factory should have been called at least 3 times (2 failures, 1 success)
    assert factory.attempts == 3
    # There should be at least one warning logged for retry attempts
    assert any('websockets connect failed attempt' in r.message for r in caplog.records if r.levelname in ('WARNING', 'ERROR'))


@pytest.mark.asyncio
async def test_connect_with_retry_fails_after_max_attempts(caplog):
    caplog.clear()
    # Always fail
    factory = FakeConnectFactory(succeed_on=999)

    with pytest.raises(Exception):
        async with connect_with_retry(factory, "wss://example.test", retries=3, backoff_factor=0.001, logger=None):
            pass

    assert factory.attempts == 3
    # Expect an error logged after exhausting retries
    assert any('websockets connect failed after' in r.message for r in caplog.records if r.levelname == 'ERROR')
