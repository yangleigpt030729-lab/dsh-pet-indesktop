"""Isolated Windows/source acceptance launcher. Default Fake chat; --live is opt-in.

No credentials or user data are copied into the source or distribution directory.
The normal product entry remains python -m pet.
"""
import argparse
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def install_fake_chat():
    import urllib.request
    from pet.chat import providers
    from pet.chat.models import SecretStore
    from pet.chat.service import ChatService
    from pet.companion.proactive_service import ProactiveService
    if getattr(ChatService.__init__, '_acceptance_fake', False):
        return
    class FakeProvider:
        synthetic_acceptance = True
        def stream(self, messages, config, cancel):
            if cancel.is_set():
                return
            text = str(messages)
            if '"interaction": "head"' in text:
                yield '合成测试：被你轻轻摸一下，本鱼的心情亮晶晶。'
            elif '"interaction": "feeding"' in text:
                yield '合成测试：收到这份数字点心啦，原文件好好地留在原地。'
            elif '"topic": "drink"' in text:
                yield '合成测试：本鱼提醒你喝点水。'
            elif '"topic": "break"' in text:
                yield '合成测试：起来活动一下吧，本鱼陪你。'
            else:
                yield '合成测试：今天也慢慢来，本鱼在这里陪你。'
    original = ChatService.__init__
    def initialize(self, provider=None, *args, **kwargs):
        original(self, provider if isinstance(provider, FakeProvider) else FakeProvider(), *args, **kwargs)
    initialize._acceptance_fake = True
    ChatService.__init__ = initialize
    original_proactive = ProactiveService.__init__
    def initialize_proactive(self, *args, provider=None, **kwargs):
        # Explicit injection keeps the service's keyless test contract honest.
        original_proactive(self, *args, provider=FakeProvider(), **kwargs)
    ProactiveService.__init__ = initialize_proactive
    SecretStore.get = lambda *a: ''
    SecretStore.set = lambda *a: False
    providers.test_connection = lambda *a, **k: (True, 'Fake Provider 可用；真实 DeepSeek 联网 NOT TESTED')
    def offline(*a, **k):
        raise OSError('Fake acceptance mode disables urllib network requests')
    urllib.request.urlopen = offline


def configure(data_dir):
    from pet.config import Config, _default_base, APP_DIR_NAME
    root = Path(__file__).resolve().parents[1]
    data_dir = Path(data_dir).resolve()
    if data_dir == root or data_dir.is_relative_to(root) or data_dir/APP_DIR_NAME == (_default_base()/APP_DIR_NAME).resolve():
        raise ValueError('Choose an acceptance directory outside the checkout and original user data directory')
    first = not (data_dir/APP_DIR_NAME/'config.json').exists()
    config = Config(base=data_dir)
    if first:
        settings = config.chat_settings()
        provider = settings.active_config
        provider.provider_id = 'acceptance-'+hashlib.sha256(str(config.dir).encode()).hexdigest()[:12]
        provider.api_key_ref = 'provider/'+provider.provider_id
        settings.providers = {provider.provider_id:provider}
        settings.active_provider = provider.provider_id
        config.set_chat_settings(settings)
    # Settings stay in this test process and use this same isolated Config.
    # Explicit settings children also inherit this base and Fake mode if the
    # isolation switch is later enabled locally.
    config.set('settings_process_isolation', False)
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--live', action='store_true', help='Use real Provider only after manual Windows credential setup')
    parser.add_argument('--auto-close-seconds', type=int, default=0, help='Optional bounded launcher smoke; not acceptance evidence')
    args = parser.parse_args()
    if not args.live:
        install_fake_chat()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from pet.app import AppShell
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    config = configure(args.data_dir)
    if not args.live:
        config.set('proactive_chat', {**config.get('proactive_chat'), 'enabled':True})
    if not config.save():
        raise OSError('Acceptance configuration could not be saved')
    shell = AppShell(app, config)
    shell._companion_acceptance_fake = not args.live
    shell.start()
    if not args.live and shell.companion_service is not None:
        shell.companion_service.delivered.connect(
            lambda _text: print('FAKE: synthetic proactive bubble displayed', flush=True))
        QTimer.singleShot(1500, shell.companion_service.tick)
    if args.auto_close_seconds:
        QTimer.singleShot(max(1, args.auto_close_seconds)*1000, app.quit)
    print('LIVE: real Provider opt-in; enter key only in local settings' if args.live else 'FAKE: synthetic chat, no real API key or DeepSeek network', flush=True)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
