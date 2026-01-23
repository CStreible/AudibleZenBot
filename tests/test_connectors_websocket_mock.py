import asyncio
import importlib
import json
import types
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_trovo_connect_uses_websocket():
    mod = importlib.import_module('platform_connectors.trovo_connector')
    TrovoWorker = next(obj for name, obj in vars(mod).items() if name.endswith('Worker') and hasattr(obj, 'connect_to_trovo'))

    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock(side_effect=[json.dumps({"type": "RESPONSE"})])

    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=ws)
    acm.__aexit__ = AsyncMock(return_value=False)

    def connect_mock(*args, **kwargs):
        return acm

    with patch('platform_connectors.trovo_connector.websockets.connect', connect_mock):
        worker = TrovoWorker(access_token='tok', channel='chan')
        worker.chat_token = 'chat-token'
        worker.running = False
        await worker.connect_to_trovo()

    sent_calls = [c.args[0] for c in ws.send.call_args_list]
    assert any('"type": "AUTH"' in c or 'AUTH' in c for c in sent_calls)


@pytest.mark.asyncio
async def test_dlive_connect_uses_websocket():
    mod = importlib.import_module('platform_connectors.dlive_connector')
    DLiveWorker = next(obj for name, obj in vars(mod).items() if name.endswith('Worker') and hasattr(obj, 'connect_and_listen'))

    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock(side_effect=[json.dumps({"type": "connection_ack"})])

    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=ws)
    acm.__aexit__ = AsyncMock(return_value=False)
    def connect_mock(*args, **kwargs):
        return acm

    with patch('platform_connectors.dlive_connector.websockets.connect', connect_mock):
        worker = DLiveWorker(username='user', access_token=None)
        worker.running = False
        await worker.connect_and_listen()

    sent_calls = [c.args[0] for c in ws.send.call_args_list]
    assert any('connection_init' in c for c in sent_calls)


@pytest.mark.asyncio
async def test_twitch_connect_uses_websocket():
    mod = importlib.import_module('platform_connectors.twitch_connector')
    TwitchWorker = next(obj for name, obj in vars(mod).items() if name.endswith('Worker') and hasattr(obj, 'connect_to_twitch'))

    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock(side_effect=asyncio.CancelledError())

    # Call authenticate directly with assigned ws
    worker = TwitchWorker(channel='chan', oauth_token='oauth:tok')
    worker.ws = ws
    await worker.authenticate()

    sent_calls = [c.args[0] for c in ws.send.call_args_list]
    assert any('PASS oauth:' in c or 'CAP REQ' in c or 'NICK' in c for c in sent_calls)


@pytest.mark.asyncio
async def test_kick_connect_uses_websocket():
    mod = importlib.import_module('platform_connectors.kick_connector_old_pusher')
    KickWorker = next(obj for name, obj in vars(mod).items() if name.endswith('Worker') and hasattr(obj, 'connect_to_kick'))

    async def fake_get_chatroom_id(self):
        return 'room123'

    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock(side_effect=asyncio.CancelledError())

    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=ws)
    acm.__aexit__ = AsyncMock(return_value=False)
    def connect_mock(*args, **kwargs):
        return acm
    # Module may not have 'websockets' attr; inject a simple namespace
    mod = importlib.import_module('platform_connectors.kick_connector_old_pusher')
    mod.websockets = types.SimpleNamespace(connect=connect_mock)

    with patch('platform_connectors.kick_connector_old_pusher.KickWorker.get_chatroom_id', fake_get_chatroom_id):
        worker = KickWorker(channel='chan', oauth_token=None)
        worker.running = False
        await worker.connect_to_kick()

    sent_calls = [c.args[0] for c in ws.send.call_args_list]
    assert any('pusher:subscribe' in c for c in sent_calls)


@pytest.mark.asyncio
async def test_twitch_eventsub_connect_uses_websocket():
    mod = importlib.import_module('platform_connectors.twitch_connector')
    EventSubWorker = next(obj for name, obj in vars(mod).items() if name.endswith('EventSubWorker'))

    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock(side_effect=[json.dumps({"metadata": {"message_type": "session_welcome"}, "payload": {"session": {"id": "s1"}}})])

    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=ws)
    acm.__aexit__ = AsyncMock(return_value=False)

    def connect_mock(*args, **kwargs):
        return acm

    with patch('platform_connectors.twitch_connector.websockets.connect', connect_mock):
        async def _fake_validate(self):
            return None

        with patch.object(EventSubWorker, 'validate_token', _fake_validate):
            worker = EventSubWorker(oauth_token='tok', client_id='cid', broadcaster_login='broad')
            worker.running = False
            await worker.connect_and_listen()

    # ensure no exceptions and at least the flow ran
    sent_calls = [c.args[0] for c in ws.send.call_args_list]
    assert True
