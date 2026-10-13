"""Exercise the real Edge SDK/MP3 writer with the WebSocket network replaced."""
import asyncio
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs

import aiohttp
import edge_tts
import pytest

from pet.voice_chime_service import _TTSWorker


def test_original_worker_uses_new_microsoft_websocket_and_writes_audio(monkeypatch, tmp_path):
    calls = []
    sessions = []
    sent = []
    header = b'X-RequestId:synthetic\r\nContent-Type:audio/mpeg\r\nPath:audio'
    payload = (len(header)+2).to_bytes(2, 'big') + header + b'\r\n' + b'synthetic-mp3'

    class WebSocket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def send_str(self, text):
            sent.append(text)

        def __aiter__(self):
            async def frames():
                yield SimpleNamespace(type=aiohttp.WSMsgType.BINARY, data=payload)
                yield SimpleNamespace(type=aiohttp.WSMsgType.TEXT, data='Path:turn.end\r\n\r\n')
            return frames()

    class Session:
        def __init__(self, **kwargs):
            sessions.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        def ws_connect(self, url, **kwargs):
            calls.append((url, kwargs))
            return WebSocket()

    monkeypatch.setattr(edge_tts.communicate.aiohttp, 'ClientSession', Session)
    monkeypatch.setattr(edge_tts.communicate, 'WSS_URL', 'wss://speech.platform.bing.com/old?x=1')
    worker = _TTSWorker('合成测试文字', 'zh-CN-XiaoyiNeural', '+10%', '+2Hz', tmp_path/'speech.mp3', lambda *_: None)
    asyncio.run(worker._synthesize(worker._voice))
    url = urlsplit(calls[0][0])
    assert url.hostname == 'api.msedgeservices.com'
    assert url.path == '/tts/cognitiveservices/websocket/v1'
    assert parse_qs(url.query)['Ocp-Apim-Subscription-Key'] == [edge_tts.constants.TRUSTED_CLIENT_TOKEN]
    assert sessions[0]['trust_env'] is True
    assert calls[0][1]['ssl'] is not False
    assert 'XiaoyiNeural' in sent[-1] and '+10%' in sent[-1] and '+2Hz' in sent[-1]
    assert worker._out_path.read_bytes() == b'synthetic-mp3'


def test_bundle_checker_rejects_missing_endpoint_adapter(monkeypatch, tmp_path):
    from scripts import verify_bundle_tts as verify
    exe = tmp_path/'pet.exe'
    exe.write_bytes(b'not executed; archive boundary replaced')
    present = set(verify.MINIMUM_MODULES) | {'pet.voice_chime_service', 'pet.edge_tts_compat', 'edge_tts.constants'}
    monkeypatch.setattr(verify, 'import_closure', lambda: set())
    monkeypatch.setattr(verify, 'frozen_module_names', lambda _: present)
    assert verify.verify(None, exe)[0] == 0
    present.remove('pet.edge_tts_compat')
    code, result = verify.verify(None, exe)
    assert code == 4 and result['missing'] == ['pet.edge_tts_compat']


def test_official_build_invokes_endpoint_archive_gate():
    from pathlib import Path
    script = (Path(__file__).resolve().parents[1]/'scripts/build_onedir.ps1').read_text(encoding='utf-8-sig')
    assert 'scripts\\verify_bundle_tts.py --app-dir $appDir' in script
    assert 'Bundled Microsoft TTS compatibility check failed' in script
