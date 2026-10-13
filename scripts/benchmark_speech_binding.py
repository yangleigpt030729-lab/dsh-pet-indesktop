"""Offline real-Qt lifecycle cost; does not synthesize or play audio."""
import json
import statistics
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QRect, QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from pet.speech_bubble import PetSpeechBubble
from pet.speech_binding import SpeechTicket
from pet.voice_chime import normalize_chime_config, pick_quote


def measure(action, count):
    samples = []
    for _ in range(count):
        started = time.perf_counter_ns()
        action()
        samples.append((time.perf_counter_ns()-started)/1000)
    return {'samples': count, 'median_us': round(statistics.median(samples), 3),
            'p95_us': round(sorted(samples)[int(count*.95)-1], 3)}


def main():
    app = QApplication.instance() or QApplication([])
    b = PetSpeechBubble()
    rect = QRect(100,100,100,100)
    for _ in range(10):
        b.show_text('合成性能样本。', rect)
        app.processEvents()
    result = {'plain_show': measure(lambda: b.show_text('合成性能样本。', rect), 200)}
    b.show_text('合成性能样本。', rect)
    def bind():
        task = SpeechTicket(b,b.text_presentation_id,lambda: True)
        task.finish('failed')
    result['bind_release'] = measure(bind,200)
    task = SpeechTicket(b,b.text_presentation_id,lambda: True)
    result['active_guard_check'] = measure(task.check,2000)
    task.finish('failed')
    from pet.config import Config
    from pet.companion.head_speech import speech_identity, permission_stamp
    from pet.voice_volume import effective
    with tempfile.TemporaryDirectory(prefix='speech-perf-') as directory:
        config = Config(base=Path(directory))
        config.save()
        identity, permission = speech_identity(config), permission_stamp(config)
        def actual_policy():
            return (speech_identity(config) == identity and permission_stamp(config) == permission
                    and effective(config) > 0)
        task = SpeechTicket(b,b.text_presentation_id,actual_policy)
        result['disk_policy_guard_check'] = measure(task.check,2000)
        task.finish('failed')
    cfg = normalize_chime_config(None)
    now = datetime(2026,10,14,12)
    result['context_quote'] = measure(lambda: pick_quote(now,cfg),2000)
    for child in b.findChildren(SpeechTicket):
        QCoreApplication.sendPostedEvents(child,QEvent.Type.DeferredDelete)
    app.processEvents()
    result['live_ticket_children'] = len(b.findChildren(SpeechTicket))
    b.dismiss()
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
