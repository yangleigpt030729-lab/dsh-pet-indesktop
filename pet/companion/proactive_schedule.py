"""Pure scheduler: monotonic activity, explicit UI snapshots, no I/O."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Snapshot:
    visible: bool = True
    suspended: bool = False
    fullscreen: bool = False
    typing: bool = False
    manual_busy: bool = False
    important: bool = False
    paused: bool = False
    quitting: bool = False
    idle_seconds: float | None = 0

    @property
    def allowed(self):
        return self.visible and not any((self.suspended, self.fullscreen, self.typing,
            self.manual_busy, self.important, self.paused, self.quitting)) and self.idle_seconds is not None and self.idle_seconds < 300


@dataclass(frozen=True)
class Candidate:
    event: str
    category: str


class Scheduler:
    def __init__(self):
        self.last_tick = None
        self.activity = 0

    def candidates(self, state, now, mono, config):
        delta = 0 if self.last_tick is None else mono-self.last_tick
        self.last_tick = mono
        if not config['enabled'] or delta < 0 or delta > 120 or not state.allowed:
            self.activity = 0
        elif state.allowed:
            self.activity += delta
        if not config['enabled'] or not state.allowed:
            return []
        quiet = config['quiet_hours']
        if quiet:
            clock = now.strftime('%H:%M')
            start, end = quiet
            if (start <= clock < end if start < end else clock >= start or clock < end):
                return []
        day, slot = now.date().isoformat(), int(now.timestamp()//7200)
        result = []
        if config['break_reminders'] and self.activity >= 3600:
            result.append(Candidate(f'break:{day}:{slot}', 'break'))
        if config['water_reminders'] and self.activity >= 5400:
            result.append(Candidate(f'drink:{day}:{slot}', 'drink'))
        if config['greetings']:
            band = 'morning' if 5 <= now.hour < 12 else 'afternoon' if 12 <= now.hour < 18 else 'evening'
            result.append(Candidate(f'greeting:{day}:{band}', 'greeting'))
        if self.activity >= 7200:
            result.append(Candidate(f'care:{day}:{slot}', 'care'))
        return result
