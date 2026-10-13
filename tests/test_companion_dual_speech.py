"""Displayed accompaniment uses two independent opt-ins and one guarded channel."""
import json
import threading
import pytest
from PySide6.QtWidgets import QApplication
from pet.config import Config
from pet.companion.interaction_service import InteractionService
from tests.test_companion_chat import wait
from tests.test_companion_interactions import setup
from tests.test_companion_proactive_service import FakeProvider
from tests.test_companion_head_speech import set_target_config
from tests.test_companion_acceptance_launcher import installed_fake as _launcher_fake_fixture


@pytest.fixture
def installed_fake(monkeypatch):
    return _launcher_fake_fixture.__wrapped__(monkeypatch)


@pytest.mark.parametrize('kind', ['head', 'feeding'])
def test_success_allows_immediate_next_request_without_advancing_clock(tmp_path, kind):
    provider = FakeProvider(['第一份回应已经收到。', '现在是完全不同的新回复。'])
    app, cfg, target, service = setup(tmp_path, provider)
    service.clock = lambda: 10000.
    try:
        assert service.request(kind, target)
        wait(app, lambda: not service.busy)
        assert service.request(kind, target)
        wait(app, lambda: not service.busy)
        assert len(provider.calls) == len(target.texts) == 2
    finally:
        service.close()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
@pytest.mark.parametrize('passive,active', [(False, False), (True, False), (False, True), (True, True)])
def test_real_receipts_independent_switches_head_feed_and_proactive(tmp_path, installed_fake, topology, child, passive, active):
    from tests.test_companion_feed_presentation import hosted
    from pet.companion import proactive_runtime
    with hosted(tmp_path, topology, child) as h:
        set_target_config(h, 'self_talk_speak_enabled', passive)
        set_target_config(h, 'proactive_bubble_speak_enabled', active)
        service = h.shell.companion_interactions = InteractionService()
        for kind in ('head', 'feeding'):
            assert service.request(kind, h.target, {'files': 1})
            wait(h.app, lambda: not service.busy)
            channel = h.shell.voice_chime_service
            assert (channel._acceptance_speech[-1] == h.bubble._raw_text) if passive else channel is None
        # Runtime selects the actual primary/legacy host, not a child voice accidentally.
        if child and topology == 'overlay':
            return
        h.shell.instance.win = h.host
        h.host._bubble_busy_until = 0
        text = '这是已经展示的主动合成问候。'
        assert proactive_runtime.present(h.shell, text)
        proactive_runtime.speak_delivered(h.shell, text)
        channel = h.shell.voice_chime_service
        count = len(channel._acceptance_speech) if channel else 0
        assert count == int(passive)*2+int(active)
        assert not list(h.cfg.dir.glob('*memory*')) and not list(h.cfg.dir.glob('*sessions*'))


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
def test_periodic_text_uses_passive_speech_once(tmp_path, installed_fake, topology, child):
    from tests.test_companion_feed_presentation import hosted
    from pet import window_alerts
    with hosted(tmp_path, topology, child) as h:
        set_target_config(h, 'self_talk_speak_enabled', True)
        host = h.host._self_talk_hosts[h.target.sprite_ref()] if topology == 'overlay' and child else h.host
        host._self_talk_enabled = True
        host._self_talk_texts = ['周期文字只有这一句。']
        host._self_talk_images = []
        h.host._bubble_busy_until = 0
        window_alerts.on_self_talk_timeout(host)
        assert h.bubble._raw_text == '周期文字只有这一句。'
        assert h.shell.voice_chime_service._acceptance_speech == [h.bubble._raw_text]
        host._self_talk_timer.stop()


def test_two_unique_immediate_settings_and_old_preference_survive_reload(tmp_path):
    from pet.modern_settings_dialog import ModernSettingsDialog, SettingRow
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('self_talk_speak_enabled', True)
    cfg.save()
    dialog = ModernSettingsDialog(cfg, include_ai=True)
    try:
        assert dialog.click_self_talk_speak_check.isChecked()
        assert not cfg.get('proactive_bubble_speak_enabled', False)
        row = dialog.findChild(SettingRow, 'settingRow_click_self_talk_speak')
        assert row.label.text() == '被动互动朗读'
        active = dialog.findChild(SettingRow, 'settingRow_proactive_chat_speak')
        assert active is not None and '语音合成服务' in active.hint_label.text()
        control = active.control
        control.setChecked(True)
        assert Config(base=tmp_path).get('proactive_bubble_speak_enabled') is True
        dialog.click_self_talk_speak_check.setChecked(False)
        assert Config(base=tmp_path).get('self_talk_speak_enabled') is False
        assert not row.isHidden() and control.isEnabled()
        assert dialog.select_page('主动陪伴朗读')
    finally:
        dialog.deleteLater()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
@pytest.mark.parametrize('failure', [False, True])
def test_actual_feed_statistics_silent_then_fun_reply_once_private_files_unchanged(tmp_path, monkeypatch, topology, child, failure):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_voice_chime_service import _service, _WorkerSpy
    with hosted(tmp_path, topology, child) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        provider = FakeProvider([RuntimeError('offline') if failure else '安全元数据变成了美味零食。'])
        service = h.shell.companion_interactions = InteractionService(provider=provider)
        now = [10000.]
        service.clock = lambda: now[0]
        paths = [tmp_path/'PRIVATE.png', tmp_path/'PRIVATE.zip', tmp_path/'PRIVATE-folder']
        paths[0].write_bytes(b'PRIVATE-BYTES')
        paths[1].write_bytes(b'PRIVATE-ZIP')
        paths[2].mkdir()
        (paths[2]/'PRIVATE.txt').write_text('PRIVATE-CONTENT', encoding='utf-8')
        h.drop(list(map(str, paths)))
        wait(h.app, lambda: not h.worker.feed_busy)
        assert '吃掉' in h.bubble._raw_text and '读不了' not in h.bubble._raw_text
        assert not _WorkerSpy.instances and not provider.calls
        receipt = h.bubble.text_presentation_id
        now[0] += 2.01  # Presentation coordination, not successful-request cooldown.
        service._flush_feeding()
        wait(h.app, lambda: not service.busy)
        assert len(provider.calls) == len(_WorkerSpy.instances) == 1
        assert h.bubble.text_presentation_id > receipt
        assert _WorkerSpy.instances[0].text == h.bubble._raw_text
        from pet.companion.head_speech import speak_target
        speak_target(h.target, h.bubble._raw_text, lambda: True)
        assert len(_WorkerSpy.instances) == 1  # Duplicate receipt cannot speak twice.
        payload = json.dumps(provider.calls[0][0], ensure_ascii=False)
        assert all(private not in payload for private in ('PRIVATE', str(tmp_path), '.png', '.zip'))
        assert paths[0].read_bytes() == b'PRIVATE-BYTES'
        assert paths[1].read_bytes() == b'PRIVATE-ZIP'
        assert not list(h.cfg.dir.glob('*memory*')) and not list(h.cfg.dir.glob('*sessions*'))
        if failure:
            assert service.backoff == now[0]+120
            calls = len(provider.calls)
            assert service.request('feeding', h.target, {'files': 1})
            wait(h.app, lambda: not service.busy)
            assert len(provider.calls) == calls  # Backoff avoids another paid model call.


@pytest.mark.parametrize('first_kind', ['head', 'feeding'])
def test_busy_burst_has_one_request_and_bounded_merged_followup(tmp_path, first_kind):
    barrier = threading.Event()
    provider = FakeProvider(['旧投喂结果应静默丢弃。', '合并后的新投喂结果。'], barrier=barrier)
    app, cfg, target, service = setup(tmp_path, provider)
    now = [10000.]
    service.clock = lambda: now[0]
    try:
        assert service.request(first_kind, target, {'files': 1})
        wait(app, lambda: bool(provider.calls))
        for _ in range(1000):
            assert not service.request('head', target)
            service.offer_feeding(target, {'files': 1, 'categories': {'image': 1}})
        assert len(service.pending_feeds) == len(provider.calls) == 1
        assert service.pending_feeds[target.key]['metadata']['files'] == 1000
        barrier.set()
        wait(app, lambda: not service.active and not service.chat.busy)
        assert not target.texts  # No old reply overwriting the new statistics.
        now[0] += 2.01
        service._flush_feeding()
        wait(app, lambda: not service.busy)
        assert len(provider.calls) == 2 and target.texts == ['合并后的新投喂结果。']
        assert '"files": 1000' in '\n'.join(m['content'] for m in provider.calls[1][0])
    finally:
        barrier.set()
        service.close()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('image_valid', [False, True])
@pytest.mark.parametrize('trigger', ['click', 'periodic'])
def test_actual_self_talk_image_silent_and_failed_image_falls_back_to_spoken_text(tmp_path, installed_fake, topology, image_valid, trigger):
    from tests.test_companion_feed_presentation import hosted
    from pet import window_alerts
    from PySide6.QtGui import QImage, QColor
    with hosted(tmp_path, topology, child=True) as h:
        set_target_config(h, 'self_talk_speak_enabled', True)
        set_target_config(h, 'self_talk_image_chance', 100)
        host = h.host._self_talk_hosts[h.target.sprite_ref()] if topology == 'overlay' else h.host
        host._self_talk_enabled = True
        host._self_talk_texts = ['加载失败后实际展示的文字。']
        image = tmp_path/'test.png'
        pix = QImage(20, 20, QImage.Format.Format_ARGB32)
        pix.fill(QColor('red'))
        pix.save(str(image))
        if not image_valid:
            image.write_bytes(b'invalid image')
        host._self_talk_images = [image]
        if topology == 'overlay':
            h.host._self_talk_image_cache = {str(image): pix if image_valid else QImage()}
        if trigger == 'click':
            assert window_alerts.show_click_self_talk(host, 'idle1')
        else:
            window_alerts.on_self_talk_timeout(host)
        if image_valid:
            assert h.bubble._content_kind == 'image' and h.shell.voice_chime_service is None
        else:
            assert h.bubble._raw_text == host._self_talk_texts[0]
            assert h.shell.voice_chime_service._acceptance_speech == [h.bubble._raw_text]
        host._self_talk_timer.stop()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('revoke', ['switch', 'off-on', 'role', 'hide', 'replace', 'quit', 'memory', 'voice'])
def test_passive_and_active_pending_voices_revoke_before_play(tmp_path, monkeypatch, topology, revoke):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.companion.head_speech import speak_target
    from pet.companion.proactive_policy import set_enabled
    from pet.companion.memory_context import MemoryContext
    with hosted(tmp_path, topology, child=True) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        assert h.target.present('已经成功展示的被动文字。')
        speak_target(h.target, h.bubble._raw_text, lambda: True)
        assert len(_WorkerSpy.instances) == 1
        assert h.target.present('已经成功展示的主动文字。')
        speak_target(h.target, h.bubble._raw_text, lambda: True, active=True)
        assert channel._pending_speech == h.bubble._raw_text  # Same bounded channel.
        if revoke == 'switch':
            set_target_config(h, 'proactive_bubble_speak_enabled', False)
        elif revoke == 'off-on':
            path = h.target.config().path
            set_enabled(path, False, feature='proactive_bubble_speak_enabled')
            set_enabled(path, True, feature='proactive_bubble_speak_enabled')
        elif revoke == 'role':
            set_target_config(h, 'character', 'another-role')
        elif revoke == 'hide':
            h.host.hide() if topology == 'legacy' else h.host.overlay.hide()
        elif revoke == 'replace':
            h.target.present('新的无声内容替换了旧消息。')
        elif revoke == 'quit':
            h.shell._quitting = True
        elif revoke == 'memory':
            MemoryContext.set_runtime_policy(h.target.config().path, False)
        else:
            set_target_config(h, 'voice_chime_voice', 'zh-CN-XiaoyiNeural')
        _WorkerSpy.instances[0].finish()
        wait(h.app, lambda: not channel._busy)
        channel._terminal_statuses = ('END',)
        channel._on_media_status('END')
        assert channel._player.plays == 0 and len(_WorkerSpy.instances) == 1
        assert not channel._pending_speech


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('active', [False, True])
@pytest.mark.parametrize('delivery', ['bubble', 'notification', 'failed', 'deleted'])
def test_due_todo_speech_exact_once_after_original_records(tmp_path, installed_fake, topology, active, delivery):
    from datetime import datetime
    from tests.test_companion_feed_presentation import hosted
    from pet.todo_reminder import TodoReminderService, new_todo_item
    with hosted(tmp_path, topology) as h:
        set_target_config(h, 'proactive_bubble_speak_enabled', active)
        h.shell.instance.win = h.host
        notifications = []
        h.shell.system_notify = lambda *a, **k: notifications.append(a) or True
        service = TodoReminderService(h.shell)
        item = new_todo_item('合成到期提醒', 'once', '10:00', '2026-10-13')
        service.set_items([item])
        h.cfg.set('todo_reminder_lead_minutes', 0)
        h.cfg.set('system_notifications_enabled', delivery == 'notification')
        service.apply_config()
        try:
            if delivery == 'notification':
                h.host.hide() if topology == 'legacy' else h.host.overlay.hide()
            elif delivery == 'failed':
                h.host._bubble_suppressed = True
            elif delivery == 'deleted':
                service.set_items([])
            now = datetime(2026, 10, 13, 10, 0)
            service.request_tick(now)
            wait(h.app, lambda: not service.busy)
            channel = h.shell.voice_chime_service
            expected = ['⏰ 待办提醒：合成到期提醒（10:00）'] if active and delivery == 'bubble' else []
            assert (channel._acceptance_speech if channel else []) == expected
            if delivery == 'bubble':
                assert service._store.load()[0]['fired_due_slot'] == '2026-10-13T10:00#due'
            service.request_tick(now)
            wait(h.app, lambda: not service.busy)
            assert (channel._acceptance_speech if channel else []) == expected
            assert len(notifications) == int(delivery == 'notification')
        finally:
            service.stop()


@pytest.mark.parametrize('revoke', ['delete', 'edit', 'disable', 'stop', 'restart', 'switch', 'off-on'])
def test_delivered_todo_pending_synthesis_revoked_without_touching_delivery(tmp_path, monkeypatch, revoke):
    from datetime import datetime
    from tests.test_companion_feed_presentation import hosted
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.todo_reminder import TodoReminderService, new_todo_item
    from pet.companion.proactive_policy import set_enabled
    with hosted(tmp_path, 'overlay') as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        service = TodoReminderService(h.shell)
        assert service._store.save([new_todo_item('合成到期文字', 'once', '10:00', '2026-10-13')])  # Loaded before startup, as after a restart.
        h.cfg.set('todo_reminder_lead_minutes', 0)
        service.apply_config()
        try:
            service.request_tick(datetime(2026, 10, 13, 10, 0))
            wait(h.app, lambda: not service.busy and len(_WorkerSpy.instances) == 1)
            assert service._store.load()[0]['fired_due_slot']
            if revoke in ('delete', 'edit', 'disable'):
                items = service.items()
                if revoke == 'delete':
                    items = []
                elif revoke == 'edit':
                    items[0]['title'] = '改后的标题'
                else:
                    items[0]['enabled'] = False
                service.set_items(items)
            elif revoke == 'stop':
                service.stop()
            elif revoke == 'restart':
                class FixedClock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return datetime(2026, 10, 13, 10, 0, tzinfo=tz)
                monkeypatch.setattr('pet.todo_reminder.datetime', FixedClock)
                service.stop()
                service.start()
                wait(h.app, lambda: not service.busy)
            elif revoke == 'switch':
                set_target_config(h, 'proactive_bubble_speak_enabled', False)
            else:
                set_enabled(h.cfg.path, False, feature='proactive_bubble_speak_enabled')
                set_enabled(h.cfg.path, True, feature='proactive_bubble_speak_enabled')
            _WorkerSpy.instances[0].finish()
            wait(h.app, lambda: not channel._busy)
            assert channel._player.plays == 0
        finally:
            service.stop()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('category', ['greeting', 'drink', 'break', 'care'])
@pytest.mark.parametrize('active', [False, True])
def test_real_proactive_worker_delivered_signal_reads_same_bubble_offline(tmp_path, monkeypatch, installed_fake, topology, category, active):
    from datetime import datetime
    from pet.companion import proactive_runtime
    from pet.chat.models import SecretStore
    from pet.voice_chime_service import _TTSWorker
    from pet import vision
    from PySide6.QtMultimedia import QCamera, QAudioSource
    import urllib.request
    from tests.test_companion_feed_presentation import hosted
    def forbidden(*args, **kwargs):
        pytest.fail('Fake accessed credentials, network, real audio or capture')
    for owner, name in [(SecretStore, 'get'), (urllib.request, 'urlopen'), (_TTSWorker, 'run'),
                        (vision, 'capture_screen_bytes'), (QCamera, 'start'), (QAudioSource, 'start')]:
        monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setattr(vision, 'get_system_idle_seconds', lambda: 0)
    with hosted(tmp_path, topology) as h:
        set_target_config(h, 'proactive_bubble_speak_enabled', active)
        h.cfg.set('proactive_chat', {'enabled': True})
        h.cfg.save()
        proactive_runtime.sync(h.shell)
        service = h.shell.companion_service
        service.timer.stop()
        requests = []
        stream = service.chat.provider.stream
        def record(messages, config, cancel):
            requests.append(messages)
            yield from stream(messages, config, cancel)
        service.chat.provider.stream = record
        service.clock = lambda: datetime(2026, 10, 13, 10, 0).astimezone()
        service.monotonic = lambda: 10000.
        service.scheduler.last_tick = 10000.
        service.scheduler.activity = 7200.
        receipts = []
        service.delivered.connect(receipts.append)
        try:
            service.tick(category=category)
            wait(h.app, lambda: not service.busy)
            assert receipts == [h.bubble._raw_text]
            assert len(requests) == 1
            channel = h.shell.voice_chime_service
            assert (channel._acceptance_speech if channel else []) == (receipts if active else [])
            stats = service.state.stats('2026-10-13')
            assert stats['successes'] == 1
            service.tick(category=category)
            wait(h.app, lambda: not service.busy)
            assert len(receipts) == len(requests) == 1  # 30-minute gate remains intact.
            assert not list(h.cfg.dir.glob('*sessions*')) and not (h.cfg.dir/'companion_memory.sqlite3').exists()
        finally:
            service.close()


@pytest.mark.parametrize('passive,active', [(False, False), (True, False), (False, True), (True, True)])
def test_shared_audio_channel_lifecycle_and_independent_chime_consumers(tmp_path, passive, active):
    from pet.app import AppShell
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('self_talk_speak_enabled', passive)
    cfg.set('self_talk_enabled', True)  # Ordinary click and AI can stay off.
    cfg.set('proactive_bubble_speak_enabled', active)
    shell = AppShell(app, cfg)
    try:
        shell._sync_chime_service()
        assert (shell.voice_chime_service is not None) == (passive or active)
        if passive or active:
            channel = shell.voice_chime_service
            assert shell.ensure_audio_channel() is channel
        cfg.set('self_talk_speak_enabled', False)
        cfg.set('proactive_bubble_speak_enabled', False)
        shell._sync_chime_service()
        assert shell.voice_chime_service is None
        cfg.set('festival_reminder_enabled', True)
        cfg.set('festival_reminder_speak', True)
        shell._sync_chime_service()
        assert shell.voice_chime_service is not None
        cfg.set('festival_reminder_speak', False)
        cfg.set('voice_chime_enabled', True)
        shell._sync_chime_service()
        assert shell.voice_chime_service is not None
    finally:
        if shell.voice_chime_service:
            shell.voice_chime_service.stop()
        shell._teardown_config_watcher()


def test_new_process_retains_two_switches_with_old_key_only_migration(tmp_path):
    import subprocess
    import sys
    cfg = Config(base=tmp_path)
    cfg.set('self_talk_speak_enabled', True)
    cfg.data.pop('proactive_bubble_speak_enabled')
    cfg.save()
    reloaded = Config(base=tmp_path)
    assert reloaded.get('self_talk_speak_enabled') and not reloaded.get('proactive_bubble_speak_enabled')
    reloaded.set('proactive_bubble_speak_enabled', True)
    reloaded.save()
    code = ('from pet.config import Config; import sys; c=Config(base=sys.argv[1]); '
            'assert c.get("self_talk_speak_enabled"); assert c.get("proactive_bubble_speak_enabled"); print("persisted")')
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path)], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == 'persisted'


def test_proactive_tts_error_preserves_text_and_title_never_enters_extra_logs(tmp_path, monkeypatch, caplog):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.companion.head_speech import speak_target
    with hosted(tmp_path, 'legacy') as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        text = '⏰ 待办提醒：SYNTHETIC-PRIVATE-TITLE（10:00）'
        assert h.target.present(text)
        speak_target(h.target, text, lambda: True, active=True)
        assert len(_WorkerSpy.instances) == 1
        _WorkerSpy.instances[0].finish(error='offline')
        wait(h.app, lambda: not channel._busy)
        assert h.bubble.isVisible() and h.bubble._raw_text == text
        assert channel._player.plays == 0
        assert 'SYNTHETIC-PRIVATE-TITLE' not in caplog.text


def test_successful_feed_offer_keeps_two_second_coordination_without_twenty_second_cooldown(tmp_path):
    provider = FakeProvider(['第一份数字点心收好啦。', '下一份完全不同的投喂回复。'])
    app, cfg, target, service = setup(tmp_path, provider)
    now = [10000.]
    service.clock = lambda: now[0]
    try:
        for count in (1, 2):
            service.offer_feeding(target, {'files': 1})
            service._flush_feeding()
            assert len(provider.calls) == count-1
            now[0] += 2.01
            service._flush_feeding()
            wait(app, lambda: not service.busy)
            assert len(provider.calls) == len(target.texts) == count
        assert now[0] < 10005.
    finally:
        service.close()


def test_next_real_interaction_revokes_previous_unplayed_voice_before_new_reply(tmp_path, monkeypatch):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_voice_chime_service import _service, _WorkerSpy
    with hosted(tmp_path, 'legacy') as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        provider = FakeProvider(['上一条已经展示的文字。', '新互动生成中的文字。'])
        service = h.shell.companion_interactions = InteractionService(provider=provider)
        barrier = threading.Event()
        try:
            assert service.request('head', h.target)
            wait(h.app, lambda: not service.busy)
            old = h.bubble._raw_text
            provider.barrier = barrier
            assert service.request('head', h.target)
            wait(h.app, lambda: len(provider.calls) == 2)
            assert h.bubble._raw_text == old
            _WorkerSpy.instances[0].finish()
            wait(h.app, lambda: not channel._busy)
            assert channel._player.plays == 0
        finally:
            service.cancel()
            barrier.set()
            wait(h.app, lambda: not service.chat._workers)


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('active', [False, True])
def test_both_channels_use_child_voice_rate_pitch_volume_and_original_cache(tmp_path, monkeypatch, topology, active):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.companion.head_speech import speak_target
    observed = []
    class Worker(_WorkerSpy):
        def __init__(self, text, voice, rate, pitch, out_path, on_done):
            observed.append((voice, rate, pitch))
            super().__init__(text, voice, rate, pitch, out_path, on_done)
    with hosted(tmp_path, topology, child=True) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        monkeypatch.setattr('pet.voice_chime_service._TTSWorker', Worker)
        for key, value in {'self_talk_speak_enabled': not active, 'proactive_bubble_speak_enabled': active,
                           'voice_chime_voice': 'zh-CN-XiaoyiNeural', 'voice_chime_rate': 15,
                           'voice_chime_pitch': 5, 'voice_chime_volume': 23}.items():
            set_target_config(h, key, value)
        assert h.target.present('子宠实际展示的同一句文字。')
        speak_target(h.target, h.bubble._raw_text, lambda: True, active=active)
        assert observed == [('zh-CN-XiaoyiNeural', '+15%', '+5Hz')]
        worker = _WorkerSpy.instances[0]
        worker.out_path.write_bytes(b'synthetic cache')
        worker.finish()
        wait(h.app, lambda: not channel._busy)
        assert channel._player.plays == 1 and channel._audio_out.volumes[-1] == .23
        assert h.target.present('子宠实际展示的同一句文字。')
        speak_target(h.target, h.bubble._raw_text, lambda: True, active=active)
        assert len(observed) == 1 and channel._player.plays == 2


def test_old_child_missing_active_consent_never_inherits_new_parent_opt_in(tmp_path):
    from tests.test_companion_feed_presentation import hosted
    with hosted(tmp_path, 'overlay', child=True) as h:
        h.cfg.set('proactive_bubble_speak_enabled', True)
        h.cfg.save()
        path = h.target.config().path
        data = json.loads(path.read_text(encoding='utf-8'))
        data.pop('proactive_bubble_speak_enabled', None)
        data['self_talk_speak_enabled'] = True  # Existing explicitly saved passive preference.
        path.write_text(json.dumps(data), encoding='utf-8')
        h.host._invalidate_sprite_configs()
        assert h.target.config().get('self_talk_speak_enabled') is True
        assert h.target.config().get('proactive_bubble_speak_enabled', False) is False
        assert h.cfg.get('proactive_bubble_speak_enabled') is True


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('active', [False, True])
def test_persisted_opt_out_overrides_older_runtime_opt_in_after_config_refresh(tmp_path, installed_fake, topology, active):
    from tests.test_companion_feed_presentation import hosted
    from pet.companion.head_speech import speak_target
    from pet.companion.proactive_policy import set_enabled
    with hosted(tmp_path, topology) as h:
        field = 'proactive_bubble_speak_enabled' if active else 'self_talk_speak_enabled'
        set_target_config(h, field, True)
        set_enabled(h.target.config().path, True, feature=field)
        # Simulate the existing external/settings-child refresh boundary.
        set_target_config(h, field, False)
        assert h.target.present('用户撤销后显示但不朗读的文字。')
        speak_target(h.target, h.bubble._raw_text, lambda: True, active=active)
        assert h.shell.voice_chime_service is None
