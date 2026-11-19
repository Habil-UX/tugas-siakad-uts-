from abc import ABC, abstractmethod
from typing import List

class Observer(ABC):
    @abstractmethod
    def update(self, event_type: str, data: dict):
        pass

class ScheduleSubject:
    def __init__(self):
        self._observers: List[Observer] = []

    def attach(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer):
        self._observers.remove(observer)

    def notify(self, event_type: str, data: dict):
        for observer in self._observers:
            try:
                observer.update(event_type, data)
            except Exception as e:
                print(f"Failed to notify observer {observer.__class__.__name__}: {e}")