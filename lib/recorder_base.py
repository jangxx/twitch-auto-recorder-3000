from abc import abstractmethod
from threading import Thread
from typing import Self

from lib.stream_metadata import StreamMetadata

class RecorderBase(Thread):
    def __init__(self):
        super().__init__()

        self._is_initialized = False
        self._recording = False
        self._encountered_error = None
        self._is_finished = False
        self._stop_time = 0

    def isRecording(self) -> bool:
        return self._recording

    def isInitialized(self) -> bool:
        return self._is_initialized

    def encounteredError(self):
        return self._encountered_error is not None

    def getStopTime(self):
        return self._stop_time

    def isFinished(self):
        return self._is_finished

    @abstractmethod
    def getFreshClone(self) -> Self:
        pass

    @abstractmethod
    def startRecording(self, metadata: StreamMetadata):
        pass

    @abstractmethod
    def stopRecording(self):
        pass

    @abstractmethod
    def finish(self):
        pass