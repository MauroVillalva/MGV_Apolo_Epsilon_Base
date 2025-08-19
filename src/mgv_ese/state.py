import threading
from datetime import datetime

class State:
    def __init__(self, follow_epsilon: bool):
        self.lock = threading.Lock()
        self.red = "OFF"
        self.yellow = "OFF"
        self.green = "OFF"
        self.last_peso = None
        self.follow_epsilon = follow_epsilon
        self.last_update_source = None
        self.last_update_at = None

    def snapshot(self):
        with self.lock:
            return {
                "red": self.red,
                "yellow": self.yellow,
                "green": self.green,
                "last_peso": self.last_peso,
                "follow_epsilon": self.follow_epsilon,
                "last_update_source": self.last_update_source,
                "last_update_at": self.last_update_at
            }

    def update(self, partial: dict, source: str, apply_func=None):
        changed = {}
        with self.lock:
            for k in ("red", "yellow", "green"):
                if k in partial and partial[k] in ("ON", "OFF"):
                    if getattr(self, k) != partial[k]:
                        setattr(self, k, partial[k])
                        changed[k] = partial[k]
            if "last_peso" in partial:
                self.last_peso = partial["last_peso"]

            self.last_update_source = source
            self.last_update_at = datetime.now().isoformat(timespec="seconds")

        if apply_func and changed:
            for k, v in changed.items():
                apply_func(k, v)
        return changed
