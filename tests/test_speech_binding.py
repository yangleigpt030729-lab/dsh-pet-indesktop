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
    elif outcome=='stop':
        media.stop()
        wait(QApplication.instance(),lambda:t.finished)
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


def test_queue_wait_and_cache_play_release_only_their_own_actor(tmp_path,monkeypatch):
    service,app,cfg=_service(tmp_path,monkeypatch)
    first,second=SpeechBubble(),SpeechBubble()
    media=service._player=Media(service)
    service._terminal_statuses=(media.M.MediaStatus.EndOfMedia,media.M.MediaStatus.InvalidMedia)
    a=ticket(first,'先播放。')
    b=ticket(second,'排队播放。')
    try:
        path=tmp_path/'local.mp3';path.write_bytes(b'synthetic cached')
        service.play_file(str(path),valid=a,config=cfg)
        service.speak('排队播放。',valid=b,config=cfg)
        assert b.state=='queued' and not second._hide_timer.isActive()
        media.end()
        assert not first.isVisible() and second.isVisible()
        assert len(_WorkerSpy.instances)==1
        worker=_WorkerSpy.instances[-1]
        worker.out_path.write_bytes(b'synthetic cached')
        worker.finish()
        wait(QApplication.instance(),lambda:not service._busy)
        assert b.state=='playing' and media.plays==2
        second._hide_timer.timeout.emit() if second._hide_timer.isActive() else None
        assert second.isVisible()
        media.end()
        assert not second.isVisible()
        # Re-display the same full reply and use exactly the existing cache key.
        c=ticket(second,'排队播放。')
        service.speak('排队播放。',valid=c,config=cfg)
        assert len(_WorkerSpy.instances)==1 and media.plays==3
        media.end()
        assert c.state=='completed'
    finally:
        service.stop();first.dismiss();second.dismiss()


def test_unexpected_late_synthesis_cannot_consume_new_guard(tmp_path,monkeypatch,bubble):
    service,app,cfg=_service(tmp_path,monkeypatch)
    old=ticket(bubble,'旧任务。')
    service.speak('旧任务。',valid=old,config=cfg)
    first=_WorkerSpy.instances[-1]
    service._busy_since=-1000000
    service._release_stale_busy()
    new=ticket(bubble,'新任务。')
    service.speak('新任务。',valid=new,config=cfg)
    second=_WorkerSpy.instances[-1]
    first.finish()
    QApplication.instance().processEvents()
    assert service._busy and service._speech_guard is new
    assert channel_plays(service)==0 and new()
    second.finish(error='synthetic failure')
    wait(QApplication.instance(),lambda:not service._busy)
    assert new.state=='failed'


def channel_plays(service):
    return service._player.plays


def test_destroyed_bubble_releases_playing_task(tmp_path,monkeypatch):
    from PySide6.QtCore import QCoreApplication,QEvent
    service,app,cfg=_service(tmp_path,monkeypatch)
    b=SpeechBubble()
    media=service._player=Media(service)
    t=ticket(b)
    path=tmp_path/'cached.mp3';path.write_bytes(b'synthetic')
    service.play_file(str(path),valid=t,config=cfg)
    b.deleteLater()
    QCoreApplication.sendPostedEvents(b,QEvent.Type.DeferredDelete)
    assert t.finished and media.state==media.M.PlaybackState.StoppedState


def test_permission_revoked_at_end_is_cancellation_not_normal_close(bubble):
    allowed=[True]
    t=ticket(bubble,valid=lambda:allowed[0])
    t.phase('playing')
    allowed[0]=False
    t.finish('completed')
    assert t.state=='cancelled' and bubble.isVisible() and bubble._hide_timer.isActive()


def test_stopped_then_end_status_in_same_media_transition_is_natural(tmp_path,monkeypatch,bubble):
    service,app,cfg=_service(tmp_path,monkeypatch)
    media=service._player=Media(service)
    service._terminal_statuses=(media.M.MediaStatus.EndOfMedia,media.M.MediaStatus.InvalidMedia)
    t=ticket(bubble)
    path=tmp_path/'cached.mp3';path.write_bytes(b'synthetic')
    service.play_file(str(path),valid=t,config=cfg)
    media.stop()  # some backends emit state before their terminal status
    media.status=media.M.MediaStatus.EndOfMedia
    service._on_media_status(media.status)
    QApplication.instance().processEvents()
    assert t.state=='completed' and not bubble.isVisible()


def test_disabled_chime_bubble_does_not_bind_old_same_text_or_silence_audio(tmp_path,monkeypatch,bubble):
    service,app,cfg=_service(tmp_path,monkeypatch)
    app.win._speech_bubble=bubble
    bubble.show_text('现在09:00',QRect(100,100,100,100),5000)
    service._cfg['show_bubble']=False
    media=service._player=Media(service)
    path=tmp_path/'cached.mp3';path.write_bytes(b'synthetic')
    service._play_and_bubble(str(path),'现在是九点整','现在09:00')
    assert media.plays==1 and bubble._speech_hold is None
    assert bubble._hide_timer.isActive()


def test_suppressed_festival_does_not_claim_previous_same_text(tmp_path,monkeypatch,bubble):
    from pet.festival_service import FestivalReminderService
    service,app,cfg=_service(tmp_path,monkeypatch)
    app.win._speech_bubble=bubble
    app.ensure_audio_channel=lambda:service
    bubble.show_text('合成节日提醒。',QRect(100,100,100,100),5000)
    monkeypatch.setattr('pet.window_alerts.sprite_in_flight',lambda host:True)
    festival=FestivalReminderService(app)
    festival._cfg['speak']=True
    festival._bubble('合成节日提醒。')
    festival._speak('合成节日提醒。')
    assert bubble._speech_hold is None and bubble._hide_timer.isActive()
    assert len(_WorkerSpy.instances)==1  # independent voice behavior preserved
    service.stop()


def test_native_player_destroyed_releases_owned_waiting_bubble(tmp_path,monkeypatch,bubble):
    from PySide6.QtCore import QCoreApplication,QEvent
    from pet.voice_chime_service import VoiceChimeService
    service,app,cfg=_service(tmp_path,monkeypatch)
    service._player=None
    assert VoiceChimeService._ensure_player(service)
    player=service._player
    t=ticket(bubble)
    service._playing_guard=t
    service._playing_started=True
    t.phase('playing')
    try:
        player.deleteLater()
        QCoreApplication.sendPostedEvents(player,QEvent.Type.DeferredDelete)
        assert t.state=='failed' and bubble._hide_timer.isActive()
        assert service._player is None
    finally:
        service._player=None  # fixture must not try to stop an already deleted native handle
        service.stop()


def test_old_playing_or_error_signal_cannot_settle_a_new_loading_task(tmp_path,monkeypatch,bubble):
    service,app,cfg=_service(tmp_path,monkeypatch)
    media=service._player=Media(service)
    media.play=lambda:None  # the new source has not started yet
    media.error=lambda:media.M.Error.NoError
    t=ticket(bubble)
    path=tmp_path/'cached.mp3';path.write_bytes(b'synthetic')
    service.play_file(str(path),valid=t,config=cfg)
    assert t.state=='loading'
    service._on_playback_state(media.M.PlaybackState.PlayingState)
    service._on_player_error(media.M.Error.ResourceError,'old source')
    assert t.state=='loading' and t.deadline.isActive() and not t.finished
    service.stop()
