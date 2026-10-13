"""Manual menu path, real Qt actors, fake screenshot/network/media only."""
import threading
import pytest
from PySide6.QtWidgets import QMenu
from pet.context_menus.shared import add_look_screen
from pet.sprite_menu_facade import SpriteMenuFacade
from tests.test_companion_feed_presentation import hosted
from tests.test_companion_head_speech import set_target_config
from tests.test_voice_chime_service import _service, _WorkerSpy
from tests.test_companion_chat import wait

def actions(menu):
    for action in menu.actions():
        yield action
        if action.menu():yield from actions(action.menu())

@pytest.mark.parametrize('topology',['legacy','overlay'])
@pytest.mark.parametrize('child',[False,True])
@pytest.mark.parametrize('active',[False,True])
def test_manual_menu_cue_and_final_follow_active_consent_without_auto_screen(tmp_path,monkeypatch,topology,child,active):
    from pet import vision
    barrier=threading.Event()
    captured=threading.Event()
    def reply(*a,**k):
        captured.set()
        assert barrier.wait(10)
        return '完整的手动识屏合成回复。'
    monkeypatch.setattr(vision,'capture_screen_bytes',lambda:b'synthetic screenshot')
    monkeypatch.setattr(vision,'foreground_app_info',lambda:'synthetic')
    monkeypatch.setattr(vision,'ask_about_screen',reply)
    with hosted(tmp_path,topology,child) as h:
        channel,_,_=_service(tmp_path/'voice',monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service=channel
        set_target_config(h,'proactive_bubble_speak_enabled',active)
        set_target_config(h,'self_talk_speak_enabled',True)
        set_target_config(h,'proactive_screen',{'enabled':False,'whitelist':[]})
        set_target_config(h,'proactive_chat',{'enabled':False})
        synced=[]
        if topology == "overlay":
            h.host._instance.enable_chat = True
            h.host._instance.sync_look_to_chat = lambda *a:synced.append(a)
        else:
            h.host.on_look_synced=lambda *a:synced.append(a)
        menu=QMenu()
        facade=SpriteMenuFacade(h.host,h.target.sprite_ref()) if topology=='overlay' else h.host
        if topology == "legacy":
            h.host.on_look_screen = h.host.look_at_screen
        add_look_screen(menu,facade)
        action=next(a for a in actions(menu) if '看看屏幕' in a.text())
        try:
            action.trigger()
            wait(h.app,lambda:captured.is_set())
            assert h.bubble._raw_text in ('让我看看…','让我看看……')
            assert len(_WorkerSpy.instances)==int(active)
            barrier.set()
            wait(h.app,lambda:not h.host._look_busy)
            assert h.bubble._raw_text=='完整的手动识屏合成回复。'
            assert len(synced)==1
            if active:
                _WorkerSpy.instances[0].finish()
                wait(h.app,lambda:len(_WorkerSpy.instances)==2)
                assert channel._player.plays==0  # stale pre-cue never starts
                assert _WorkerSpy.instances[-1].text==h.bubble._raw_text
                _WorkerSpy.instances[-1].finish()
                wait(h.app,lambda:not channel._busy)
                assert channel._player.plays==1
                assert not h.bubble._hide_timer.isActive()
            if topology=='overlay' and child:
                assert h.host._speech_bubble._raw_text!='完整的手动识屏合成回复。'
        finally:
            barrier.set()
            menu.close()

@pytest.mark.parametrize('topology',['legacy','overlay'])
@pytest.mark.parametrize('cancel',['speech_off','role','hide_show','cancel','failure','preference_volume'])
def test_manual_result_cancellation_and_failure_boundaries(tmp_path,monkeypatch,topology,cancel):
    from pet import vision
    barrier,entered=threading.Event(),threading.Event()
    def reply(*args,**kwargs):
        entered.set()
        assert barrier.wait(10)
        if cancel=='failure':raise RuntimeError('synthetic failure')
        return '这是一段完整的长回复，需要分页展示但只朗读一次。'*25
    monkeypatch.setattr(vision,'capture_screen_bytes',lambda:b'synthetic')
    monkeypatch.setattr(vision,'foreground_app_info',lambda:'synthetic')
    monkeypatch.setattr(vision,'ask_about_screen',reply)
    with hosted(tmp_path,topology,True) as h:
        channel,_,_=_service(tmp_path/'voice',monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service=channel
        set_target_config(h,'proactive_bubble_speak_enabled',True)
        set_target_config(h,'proactive_screen',{'enabled':False,'whitelist':[]})
        try:
            h.host.look_at_screen(h.target.sprite_ref()) if topology=='overlay' else h.host.look_at_screen()
            wait(h.app,entered.is_set)
            old=h.host._manual_screen_request
            if cancel=='speech_off':set_target_config(h,'proactive_bubble_speak_enabled',False)
            elif cancel=='role':set_target_config(h,'character','different-role')
            elif cancel=='hide_show':
                if topology=='overlay':
                    h.host.set_sprite_visible(h.target.sprite_ref(),False)
                    h.host.set_sprite_visible(h.target.sprite_ref(),True)
                else:
                    h.host.hide();h.host.show()
            elif cancel=='cancel':old.cancel()
            elif cancel=='preference_volume':
                from pet.voice_volume import write, menu_config
                cfg = menu_config(SpriteMenuFacade(h.host,h.target.sprite_ref())) if topology == "overlay" else h.target.config()
                assert write(cfg,volume=23)
            barrier.set()
            wait(h.app,lambda:not h.host._look_busy)
            wait(h.app,lambda:old.cancelled or old.stage=='final')
            _WorkerSpy.instances[0].finish()
            wait(h.app,lambda:not channel._busy or len(_WorkerSpy.instances)>1)
            if cancel=='preference_volume':
                assert len(_WorkerSpy.instances)==2 and len(h.bubble._pages)>1
                assert _WorkerSpy.instances[-1].text==h.bubble._raw_text
                _WorkerSpy.instances[-1].finish()
                wait(h.app,lambda:not channel._busy)
                assert channel._player.plays==1 and channel._audio_out.volumes[-1]==.23
            else:
                assert channel._player.plays==0 and len(_WorkerSpy.instances)==1
                assert h.bubble._hide_timer.isActive() or not h.bubble.isVisible()
        finally:
            barrier.set()
