"""Real Qt bubbles and service queue; only network/media-device boundaries fake."""
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication
import pytest
from pet.speech_bubble import PetSpeechBubble as SpeechBubble
from tests.test_voice_chime_service import _service, _WorkerSpy
from tests.test_companion_chat import wait

@pytest.fixture
def bubble():
    QApplication.instance() or QApplication([])
    b = SpeechBubble()
    yield b
    b.dismiss()
    b.deleteLater()

def ticket(bubble, text='完整回复。', valid=lambda: True):
    from pet.speech_binding import SpeechTicket
    bubble.show_text(text, QRect(100,100,100,100), 500)
    return SpeechTicket(bubble, bubble.text_presentation_id, valid)

def test_wait_and_play_hold_bubble_until_actual_end(bubble):
    t = ticket(bubble)
    assert not bubble._hide_timer.isActive()
    assert t() and t.state == 'waiting'
    t.phase('playing')
    t.progress(60000, 40000)
    assert not bubble._hide_timer.isActive() and bubble.isVisible()
    t.finish('completed')
    assert not bubble.isVisible()

def test_replaced_presentation_cannot_be_closed_by_old_end(bubble):
    old = ticket(bubble)
    bubble.show_text('新回复。', QRect(100,100,100,100),5000)
    receipt = bubble.text_presentation_id
    old.finish('completed')
    assert bubble.isVisible() and bubble.text_presentation_id == receipt
    assert bubble._hide_timer.isActive()

@pytest.mark.parametrize('outcome',['failed','cancelled','muted','timeout'])
def test_failure_restores_normal_hide_without_permanent_hold(bubble,outcome):
    t = ticket(bubble)
    t.finish(outcome)
    assert bubble._hide_timer.isActive()
    assert not t()

def test_long_reply_is_one_task_pages_survive_and_last_is_displayed(bubble):
    t = ticket(bubble, '这是一段完整的长回复，分页不会改变语音任务。'*30)
    assert len(bubble._pages)>2 and bubble._page_timer.isActive()
    receipt = bubble.text_presentation_id
    t.phase('playing')
    t.progress(9000,4000)
    assert bubble.text_presentation_id == receipt and t()
    t.finish('completed')
    assert bubble.isVisible()
    while bubble._page_index < len(bubble._pages)-1:
        bubble._on_page_timeout()
    wait(QApplication.instance(), lambda: bubble.label.text()==bubble._pages[-1])
    assert bubble._hide_timer.isActive()

def test_hide_and_permission_revocation_cancel_wait(bubble):
    allowed=[True]
    t=ticket(bubble,valid=lambda: allowed[0])
    allowed[0]=False
    t.check()
    assert not t() and bubble._hide_timer.isActive()
    t=ticket(bubble)
    bubble.dismiss()
    assert not t()

def test_queue_replacement_releases_other_actor_bubble(tmp_path,monkeypatch):
    service,app,cfg=_service(tmp_path,monkeypatch)
    first,second=SpeechBubble(),SpeechBubble()
    try:
        a=ticket(first,'第一只。')
        b=ticket(second,'第二只。')
        service._player_busy=lambda:True
        service.speak('第一只。',valid=a,config=cfg)
        service.speak('第二只。',valid=b,config=cfg)
        assert a.state=='cancelled' and first._hide_timer.isActive()
        assert b() and not second._hide_timer.isActive()
        service.stop()
        assert not b() and second._hide_timer.isActive()
    finally:
        first.dismiss();second.dismiss()

def test_synthesis_error_releases_ticket_keeps_original_text(tmp_path,monkeypatch,bubble):
    service,app,cfg=_service(tmp_path,monkeypatch)
    t=ticket(bubble)
    service.speak('完整回复。',valid=t,config=cfg)
    assert len(_WorkerSpy.instances)==1
    _WorkerSpy.instances[-1].finish(error='synthetic failure')
    app_events=QApplication.instance()
    wait(app_events,lambda:not service._busy)
    assert t.state=='failed' and bubble._hide_timer.isActive()
    assert bubble._raw_text=='完整回复。'

class Media:
    """Device boundary double; real enum values and service handlers."""
    def __init__(self,service):
        from PySide6.QtMultimedia import QMediaPlayer as M
        self.M=M
        self.service=service
        self.status=M.MediaStatus.LoadedMedia
        self.state=M.PlaybackState.StoppedState
        self.pos=0
        self.length=10000
        self.plays=0
    def mediaStatus(self):return self.status
    def playbackState(self):return self.state
    def duration(self):return self.length
    def position(self):return self.pos
    def setSource(self,source):
        self.source=source
        self.status=self.M.MediaStatus.LoadedMedia
    def play(self):
        self.plays+=1
        self.state=self.M.PlaybackState.PlayingState
        self.service._on_playback_state(self.state)
    def stop(self):
        self.state=self.M.PlaybackState.StoppedState
        self.service._on_playback_state(self.state)
    def end(self):
        self.status=self.M.MediaStatus.EndOfMedia
        self.stop()
        self.service._on_media_status(self.status)

@pytest.mark.parametrize('outcome',['natural','stop','invalid','error','mute','revoke'])
def test_actual_media_boundary_distinguishes_termination(tmp_path,monkeypatch,bubble,outcome):
    service,app,cfg=_service(tmp_path,monkeypatch)
    media=service._player=Media(service)
    service._terminal_statuses=(media.M.MediaStatus.EndOfMedia,media.M.MediaStatus.InvalidMedia)
    allowed=[True]
    t=ticket(bubble,valid=lambda:allowed[0])
    path=tmp_path/'cached.mp3';path.write_bytes(b'synthetic MP3')
    assert service.play_file(str(path),valid=t,config=cfg)
    assert t.state=='playing' and not bubble._hide_timer.isActive()
    media.pos=4000
    service._on_audio_progress()
    if outcome=='natural':media.end()
    elif outcome=='stop':media.stop()
    elif outcome=='invalid':
        media.status=media.M.MediaStatus.InvalidMedia
        service._on_media_status(media.status)
    elif outcome=='error':service._on_player_error()
    elif outcome=='mute':service._hot_volume(80,True)
    else:
        allowed[0]=False
        t.check()
        assert media.state==media.M.PlaybackState.StoppedState
    assert t.state==('completed' if outcome=='natural' else 'cancelled' if outcome in ('stop','revoke') else 'muted' if outcome=='mute' else 'failed')
    assert not bubble.isVisible() if outcome=='natural' else bubble._hide_timer.isActive()


def test_late_old_media_event_does_not_close_new_bubble(tmp_path,monkeypatch,bubble):
    service,app,cfg=_service(tmp_path,monkeypatch)
    media=service._player=Media(service)
    service._terminal_statuses=(media.M.MediaStatus.EndOfMedia,media.M.MediaStatus.InvalidMedia)
    path=tmp_path/'cached.mp3';path.write_bytes(b'synthetic')
    old=ticket(bubble,'旧回复。')
    service.play_file(str(path),valid=old,config=cfg)
    new=ticket(bubble,'新回复。')
    service.play_file(str(path),valid=new,config=cfg)
    service._on_media_status(media.M.MediaStatus.EndOfMedia)  # old queued status, current source still loaded
    assert new() and bubble.isVisible()
    media.end()
    assert not bubble.isVisible()


def test_sticky_consumer_is_never_owned_by_speech(bubble):
    from pet.speech_binding import SpeechTicket
    bubble.show_text('审批',QRect(100,100,100,100),sticky=True)
    t=SpeechTicket(bubble,bubble.text_presentation_id,lambda:True)
    assert t.finished and bubble.isVisible() and not bubble._hide_timer.isActive()


def test_healthy_long_playback_has_no_30_second_deadline(bubble):
    t=ticket(bubble)
    t.phase('playing')
    t.progress(300000,120000)
    assert t() and not t.deadline.isActive() and not bubble._hide_timer.isActive()
    t.finish('completed')


def test_chime_bubble_and_festival_share_binding_without_companion_switch(tmp_path,monkeypatch,bubble):
    from pet.festival_service import FestivalReminderService
    service,app,cfg=_service(tmp_path,monkeypatch)
    app.win._speech_bubble=bubble
    app.win.show_bubble=lambda text,**k:bubble.show_text(text,QRect(100,100,100,100),500)
    app.ensure_audio_channel=lambda:service
    media=service._player=Media(service)
    service._terminal_statuses=(media.M.MediaStatus.EndOfMedia,media.M.MediaStatus.InvalidMedia)
    path=tmp_path/'cached.mp3';path.write_bytes(b'synthetic')
    service._play_and_bubble(str(path),'现在是九点整','现在09:00')
    assert not bubble._hide_timer.isActive()
    media.end()
    assert not bubble.isVisible()
    festival=FestivalReminderService(app)
    festival._cfg['speak']=True
    festival._bubble('合成节日提醒。')
    festival._speak('合成节日提醒。')
    assert not bubble._hide_timer.isActive()
    _WorkerSpy.instances[-1].finish()
    wait(QApplication.instance(),lambda:not service._busy)
    media.end()
    assert not bubble.isVisible()
    cfg.set('voice_chime_show_bubble',False)
    service.apply_config()
    service._play_and_bubble(str(path),'audio only','must not show')
    assert not bubble.isVisible()
