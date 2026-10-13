"""Actual card button -> AppShell signal slot -> actual QuickChatBubble."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from tests.test_companion_feed_presentation import hosted
from tests.test_companion_chat import wait


def cleanup_island(h):
    for quick in (h.shell.instance.quick_chat, getattr(h.shell, 'island_chat', None)):
        if quick is not None:
            quick.close()
            quick.deleteLater()
    if hasattr(h.host, '_close_quick_chat'):
        h.host._close_quick_chat()
    if h.shell.island_collision:
        h.shell.island_collision.stop()
    h.shell.island.hide()
    h.shell.island.deleteLater()
    from pet.chat.service import ChatService
    ChatService.unregister_global_finished(h.shell._on_global_chat_finished)


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
def test_card_chat_button_opens_real_input_bubble(tmp_path, topology):
    with hosted(tmp_path, topology) as h:
        h.cfg.set('dynamic_island', {'enabled': True})
        h.shell._sync_dynamic_island()
        island = h.shell.island
        try:
            island.expand_card()
            island._finish_animations()
            QTest.mouseClick(island._card_chat_btn, Qt.MouseButton.LeftButton)
            quick = lambda: h.host._quick_chat if topology == 'overlay' else h.shell.instance.quick_chat
            wait(h.app, lambda: quick() is not None and quick().isVisible())
            assert quick().input.isVisible()
            island._finish_animations()
            assert island._debug_state()['mode'] != 'expanded'
        finally:
            cleanup_island(h)


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('mode', ['hidden', 'no_chat', 'quit_before_deferred'])
def test_actual_card_preserves_hidden_no_chat_and_exit_routes(tmp_path, topology, mode):
    with hosted(tmp_path, topology) as h:
        h.cfg.set('dynamic_island', {'enabled': True})
        if mode == 'no_chat':
            h.shell.enable_chat = False
        if mode == 'hidden':
            h.host.set_pet_visible(False) if topology == 'overlay' else h.host.hide()
        h.shell._sync_dynamic_island()
        island = h.shell.island
        try:
            island.expand_card()
            island._finish_animations()
            QTest.mouseClick(island._card_chat_btn, Qt.MouseButton.LeftButton)
            if mode == 'quit_before_deferred':
                h.shell._quitting = True
            h.app.processEvents()
            if mode == 'hidden':
                wait(h.app, lambda: h.shell.island_chat is not None and h.shell.island_chat.isVisible())
            else:
                assert h.shell.instance.quick_chat is None
                assert getattr(h.host, '_quick_chat', None) is None
                assert h.shell.island_chat is None
        finally:
            cleanup_island(h)
