"""One background job at a time. The worker never calls Tkinter."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Queue
from threading import Event
from typing import Any, Callable


@dataclass(frozen=True, repr=False)
class JobEvent:
    kind: str
    payload: Any


class BackgroundWorker:
    def __init__(self):
        self.events: Queue[JobEvent] = Queue()
        self.cancelled = Event()
        self.busy = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="equipment-processing")

    def start(self, operation: Callable) -> bool:
        if self.busy:
            return False
        self.busy = True
        self.cancelled.clear()

        def run():
            try:
                result = operation(
                    lambda completed, total: self.events.put(JobEvent("progress", (completed, total))),
                    self.cancelled,
                )
                self.events.put(JobEvent("done", result))
            except Exception:
                # A raw exception may expose source values. The view gets a safe category.
                self.events.put(JobEvent("error", "The operation could not finish. Preview again before processing."))

        self.executor.submit(run)
        return True

    def stop(self):
        """Stop between files; never interrupt an active M1 commit."""
        self.cancelled.set()

    def close(self):
        self.stop()
        self.executor.shutdown(wait=False)
