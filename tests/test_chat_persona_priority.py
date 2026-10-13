"""User persona versus real resource manifest; fake only the network boundary."""
import importlib
import json
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
import pytest
from PySide6.QtWidgets import QApplication
from pet.chat.models import ChatSettings
from pet.chat.prompt import PromptBuilder
from pet.chat.service import ChatService
from pet.config import Config
from tests.test_companion_chat import wait
from tests.test_companion_proactive_service import FakeProvider

ROLE = 'shenshen'
PACKAGED = 'PACKAGED-ROLE: 你是角色资源包中的默认大肥鱼。'
CUSTOM = 'CUSTOM-USER: 你是机器人阿蓝，禁止自称女仆；没有文件或记忆授权时不得读取。'
NEW = 'NEW-USER: 你是用户设置的图书管理员小树。'


@pytest.fixture
def manifest_builder(tmp_path, monkeypatch):
    root = tmp_path/'characters'
    folder = root/ROLE
    folder.mkdir(parents=True)
    (folder/'manifest.json').write_text(json.dumps({'chat': {'system_prompt': PACKAGED}}, ensure_ascii=False), encoding='utf-8')
    builder = PromptBuilder(root)
    # Override only the resource location, not the resolver or prompt contents.
    for name in ('pet.companion.proactive_service', 'pet.companion.interaction_service',
                 'pet.chat.widgets', 'pet.chat.legacy_widgets'):
        monkeypatch.setattr(importlib.import_module(name), 'PromptBuilder', lambda _root: builder)
    return builder


def saved_persona(cfg, text):
    settings = cfg.chat_settings()
    settings.default_system_prompt = text
    cfg.set_chat_settings(settings)
    assert cfg.save()


def test_saved_user_prompt_wins_when_real_manifest_also_exists(manifest_builder):
    settings = ChatSettings.defaults()
    settings.default_system_prompt = '  '+CUSTOM+'  '
    assert manifest_builder.effective_system_prompt(settings, ROLE) == CUSTOM
    assert manifest_builder.build_messages(settings, ROLE, [], '你好')[0]['content'] == CUSTOM
    assert manifest_builder.effective_system_prompt(settings, ROLE, 'explicit-call-override') == 'explicit-call-override'


@pytest.mark.parametrize('text', ['', '   ', ChatSettings().default_system_prompt, ' '+ChatSettings().default_system_prompt+' '])
def test_unmodified_or_cleared_prompt_preserves_real_character_default(manifest_builder, text):
    settings = ChatSettings.defaults()
    settings.default_system_prompt = text
    assert manifest_builder.effective_system_prompt(settings, ROLE) == PACKAGED
    assert manifest_builder.effective_system_prompt(settings, 'missing') == ChatSettings().default_system_prompt


def test_existing_ai_editor_save_and_new_process_restart_keep_user_persona(tmp_path, manifest_builder):
    from pet.chat.ai_settings_page import _AiSettingsPage
    QApplication.instance() or QApplication([])
    base = tmp_path/'data'
    cfg = Config(base=base)
    page = _AiSettingsPage(cfg)
    try:
        page.prompt.setPlainText(CUSTOM)
        page.save()
        assert cfg.save()
        restarted = Config(base=base)
        assert manifest_builder.effective_system_prompt(restarted.chat_settings(), ROLE) == CUSTOM
        code = ('import sys; from pet.config import Config; from pet.chat.prompt import PromptBuilder; '
                'print(PromptBuilder(sys.argv[2]).effective_system_prompt(Config(base=sys.argv[1]).chat_settings(),sys.argv[3]))')
        result = subprocess.run([sys.executable, '-c', code, str(base), str(manifest_builder.characters_root), ROLE],
                                capture_output=True, text=True, encoding='utf-8', timeout=60, check=True)
        assert result.stdout.strip() == CUSTOM
    finally:
        page.deleteLater()


def companion(tmp_path, kind, provider):
    from pet.companion.interaction_service import InteractionService
    from tests.test_companion_interactions import Target
    from pet.companion.proactive_service import ProactiveService
    from pet.companion.proactive_schedule import Snapshot
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path/'data')
    cfg.set('character', ROLE)
    cfg.set('dialogue_mode', 'whale_maid')
    cfg.set('proactive_chat', {'enabled': True})
    cfg.set('companion_interaction', {'head_touch_enabled': True, 'feeding_enabled': True})
    cfg.save()
    output = []
    now, mono = [datetime(2099, 5, 7, 10, tzinfo=timezone.utc)], [1000.]
    if kind == 'greeting':
        service = ProactiveService(cfg, lambda: Snapshot(), lambda t: (output.append(t), True)[1],
                                   provider=provider, clock=lambda: now[0], monotonic=lambda: mono[0])
        def submit():
            service.tick()
        def advance():
            now[0] += timedelta(minutes=31)
            mono[0] += 31*60
    else:
        target = Target(cfg)
        output = target.texts
        service = InteractionService(provider=provider)
        def submit():
            assert service.request(kind, target, {'files': 1, 'categories': {'image': 1}, 'path': 'PRIVATE-PATH', 'filename': 'PRIVATE-NAME'})
        def advance():
            service.cooldowns.clear()
    return app, cfg, service, output, submit, advance


@pytest.mark.parametrize('kind', ['greeting', 'head', 'feeding'])
@pytest.mark.parametrize('custom', [False, True])
def test_companion_actual_provider_uses_user_or_pack_default_and_keeps_safety(tmp_path, manifest_builder, kind, custom):
    provider = FakeProvider(['这次也自然地陪着你。'])
    app, cfg, service, output, submit, advance = companion(tmp_path, kind, provider)
    if custom:
        saved_persona(cfg, CUSTOM)
    try:
        submit()
        wait(app, lambda: not service.busy)
        assert len(provider.calls) == len(output) == 1
        messages = provider.calls[0][0]
        assert messages[0]['content'] == (CUSTOM if custom else PACKAGED)
        assert PACKAGED not in str(messages) if custom else True
        assert 'expression_style' in messages[1]['content'] and '不覆盖角色人设' in messages[1]['content']
        assert '不是用户' in messages[-1]['content']
        assert 'PRIVATE-PATH' not in str(messages) and 'PRIVATE-NAME' not in str(messages)
        if kind == 'feeding':
            assert '绝不假装' in messages[-1]['content'] and '"image": 1' in messages[-1]['content']
        assert not (cfg.dir/'companion_memory.sqlite3').exists()
        assert not list(cfg.dir.glob('sessions*'))
    finally:
        service.close()
        wait(app, lambda: not service.chat._workers)


@pytest.mark.parametrize('kind', ['greeting', 'head', 'feeding'])
def test_saved_persona_hot_switch_rejects_old_async_result_then_uses_new(tmp_path, manifest_builder, kind):
    barrier = threading.Event()
    provider = FakeProvider(['旧人设回复不得展示。', '新的人设回复。'], barrier=barrier)
    app, cfg, service, output, submit, advance = companion(tmp_path, kind, provider)
    saved_persona(cfg, CUSTOM)
    try:
        submit()
        wait(app, lambda: bool(provider.calls))
        assert provider.calls[0][0][0]['content'] == CUSTOM
        saved_persona(cfg, NEW)
        if kind == 'greeting':
            service.apply_config()  # Existing application hot-update seam.
        barrier.set()
        wait(app, lambda: not service.busy)
        assert output == []
        advance()
        submit()
        wait(app, lambda: not service.busy)
        assert len(provider.calls) == 2 and provider.calls[1][0][0]['content'] == NEW
        assert output == ['新的人设回复。']
    finally:
        barrier.set()
        service.close()
        wait(app, lambda: not service.chat._workers)


def chat_window(tmp_path, module, provider, monkeypatch):
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path/'data')
    cfg.resolve_api_key = lambda _p: ''
    widgets = importlib.import_module(module)
    monkeypatch.setattr(widgets, 'ChatService', lambda **kwargs: ChatService(provider=provider, **kwargs))
    window = widgets.ChatWindow(cfg, ROLE)
    return app, cfg, window


@pytest.mark.parametrize('module', ['pet.chat.widgets', 'pet.chat.legacy_widgets'])
@pytest.mark.parametrize('custom', [False, True])
def test_ordinary_chat_actual_provider_uses_saved_user_or_manifest_persona(tmp_path, manifest_builder, module, custom, monkeypatch):
    provider = FakeProvider(['普通聊天回复。'])
    app, cfg, window = chat_window(tmp_path, module, provider, monkeypatch)
    try:
        if custom:
            saved_persona(cfg, CUSTOM)
            window.refresh_settings()
        window.input.setPlainText('你好')
        window.send_message()
        wait(app, lambda: len(window.session.messages) == 2)
        assert provider.calls[0][0][0]['content'] == (CUSTOM if custom else PACKAGED)
    finally:
        window.service.shutdown()
        wait(app, lambda: not window.service._workers)
        window.close()


@pytest.mark.parametrize('module', ['pet.chat.widgets', 'pet.chat.legacy_widgets'])
def test_ordinary_chat_persona_refresh_cancels_old_request_and_preserves_history(tmp_path, manifest_builder, module, monkeypatch):
    barrier = threading.Event()
    provider = FakeProvider(['旧人设回复不得入会话。', '新的人设聊天回复。'], barrier=barrier)
    app, cfg, window = chat_window(tmp_path, module, provider, monkeypatch)
    saved_persona(cfg, CUSTOM)
    window.refresh_settings()
    try:
        window.input.setPlainText('第一条')
        window.send_message()
        wait(app, lambda: bool(provider.calls))
        old = window._active_request_id
        saved_persona(cfg, NEW)
        window.refresh_settings()
        assert window._active_request_id is None
        barrier.set()
        wait(app, lambda: not window.service.busy and not window.service._workers)
        # Simulate already queued callbacks after the request is no longer current.
        window._delta(old, '旧文字')
        window._finished(old, '旧人设回复不得入会话。')
        assert [m.role for m in window.session.messages] == ['user']
        window.input.setPlainText('第二条')
        window.send_message()
        wait(app, lambda: len(window.session.messages) == 3)
        assert provider.calls[-1][0][0]['content'] == NEW
        assert window.session.messages[-1].content == '新的人设聊天回复。'
    finally:
        barrier.set()
        window.service.shutdown()
        wait(app, lambda: not window.service._workers)
        window.close()


def test_persona_change_discards_modern_typewriter_queue_after_network_finished(tmp_path, manifest_builder, monkeypatch):
    provider = FakeProvider(['旧缓存输出。'])
    app, cfg, window = chat_window(tmp_path, 'pet.chat.widgets', provider, monkeypatch)
    saved_persona(cfg, CUSTOM)
    window.refresh_settings()
    try:
        window.input.setPlainText('你好')
        window.send_message()
        window._typewriter_timer.setInterval(60000)  # Deliberately hold UI drain, no timing guess.
        wait(app, lambda: window._pending_finish_text is not None and not window.service.busy)
        saved_persona(cfg, NEW)
        window.refresh_settings()
        window._typewriter_timer.timeout.emit()
        assert [m.role for m in window.session.messages] == ['user']
        assert window._pending_finish_text is None and not window._typewriter_timer.isActive()
    finally:
        window.service.shutdown()
        wait(app, lambda: not window.service._workers)
        window.close()


@pytest.mark.parametrize('module', ['pet.chat.widgets', 'pet.chat.legacy_widgets'])
def test_unrelated_settings_refresh_keeps_current_persona_request(tmp_path, manifest_builder, module, monkeypatch):
    barrier = threading.Event()
    provider = FakeProvider(['仍属当前人设的回复。'], barrier=barrier)
    app, cfg, window = chat_window(tmp_path, module, provider, monkeypatch)
    saved_persona(cfg, CUSTOM)
    window.refresh_settings()
    try:
        window.input.setPlainText('你好')
        window.send_message()
        wait(app, lambda: bool(provider.calls))
        rid = window._active_request_id
        cfg.set('dialogue_mode', 'whale_maid')
        assert cfg.save()
        window.refresh_settings()
        assert window._active_request_id == rid and window.service.busy
        barrier.set()
        wait(app, lambda: len(window.session.messages) == 2)
        assert window.session.messages[-1].content == '仍属当前人设的回复。'
    finally:
        barrier.set()
        window.service.shutdown()
        wait(app, lambda: not window.service._workers)
        window.close()


def test_child_saved_persona_does_not_replace_unmodified_parent_persona(tmp_path, manifest_builder):
    base = tmp_path/'data'
    parent = Config(base=base)
    parent.save()
    child = Config(base=base, instance_id='slot-1')
    saved_persona(child, CUSTOM)
    assert manifest_builder.effective_system_prompt(Config(base=base).chat_settings(), ROLE) == PACKAGED
    assert manifest_builder.effective_system_prompt(Config(base=base, instance_id='slot-1').chat_settings(), ROLE) == CUSTOM
