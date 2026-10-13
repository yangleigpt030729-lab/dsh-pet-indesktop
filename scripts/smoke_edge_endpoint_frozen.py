"""Offline frozen-module smoke; synthetic audio is not native or online acceptance."""
import asyncio
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

import edge_tts
from pet.voice_chime_service import _TTSWorker


def main():
    if not getattr(sys, 'frozen', False):
        raise RuntimeError('Run the PyInstaller-built diagnostic, not this source script')
    observed = []

    class SyntheticCommunicate:
        def __init__(self, text, voice, **kwargs):
            host = urlsplit(edge_tts.communicate.WSS_URL).hostname
            assert host == 'api.msedgeservices.com', 'frozen worker did not apply the endpoint repair'
            observed.append(host)

        async def save(self, filename):
            Path(filename).write_bytes(b'synthetic audio; not playable acceptance evidence')

    edge_tts.Communicate = SyntheticCommunicate  # network boundary only
    with tempfile.TemporaryDirectory(prefix='edge-frozen-smoke-') as root:
        worker = _TTSWorker('synthetic speech', 'zh-CN-XiaoyiNeural', '+0%', '+0Hz', Path(root)/'speech.mp3', lambda *_: None)
        asyncio.run(worker._synthesize(worker._voice))
        assert worker._out_path.stat().st_size > 0
    print('FROZEN endpoint adapter PASS: '+observed[0]+'; synthetic/offline; real audio NOT TESTED')


if __name__ == '__main__':
    main()
